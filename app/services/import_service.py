import os
import uuid
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Any, Tuple
from sqlalchemy import func
from werkzeug.utils import secure_filename
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.import_batch import ImportBatch
from app.services.categorizer_service import CategorizerService
from app.services.anomaly_service import AnomalyDetectionService

class ImportService:
    """
    Bank Statement Import Service supporting CSV and Excel (.xlsx, .xls).
    Handles file security validation, dynamic column header auto-detection,
    interactive preview generation, duplicate record identification,
    and bulk transaction ingestion.
    """

    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}

    @classmethod
    def is_allowed_file(cls, filename: str) -> bool:
        if "." not in filename:
            return False
        return filename.rsplit(".", 1)[1].lower() in cls.ALLOWED_EXTENSIONS

    @classmethod
    def parse_uploaded_file(cls, file_storage, upload_folder: str) -> tuple[str, str, List[str], List[Dict[str, Any]]]:
        """
        Validates, saves, and reads a CSV or Excel statement.
        Returns:
            - saved_filepath
            - original_filename
            - detected_columns (list of string headers)
            - sample_rows (top 50 rows as dicts for preview/mapping)
        """
        original_name = secure_filename(file_storage.filename or "statement.csv")
        ext = original_name.rsplit(".", 1)[1].lower()
        unique_name = f"import_{uuid.uuid4().hex[:12]}.{ext}"
        os.makedirs(upload_folder, exist_ok=True)
        abs_path = os.path.join(upload_folder, unique_name)
        file_storage.save(abs_path)

        # Read into pandas dataframe
        if ext == "csv":
            # Attempt UTF-8, then fall back to latin1
            try:
                df = pd.read_csv(abs_path, dtype=str).fillna("")
            except UnicodeDecodeError:
                df = pd.read_csv(abs_path, encoding="latin1", dtype=str).fillna("")
        else:
            df = pd.read_excel(abs_path, dtype=str).fillna("")

        # Sanitize column names
        columns = [str(col).strip() for col in df.columns]
        df.columns = columns

        # Convert top 100 rows to list of dicts for preview
        records = df.head(100).to_dict(orient="records")

        return abs_path, original_name, columns, records

    @classmethod
    def auto_detect_column_mapping(cls, columns: List[str]) -> Dict[str, str]:
        """
        Intelligently guesses which table attribute matches each file column.
        """
        mapping = {
            "date": "",
            "description": "",
            "amount": "",
            "category": "",
        }

        col_lower = {col.lower().replace("_", " ").replace("-", " "): col for col in columns}

        # Date detection
        for term in ["date", "transaction date", "trans date", "posting date", "posted date"]:
            for key, orig in col_lower.items():
                if term in key:
                    mapping["date"] = orig
                    break
            if mapping["date"]:
                break

        # Description detection
        for term in ["description", "narration", "details", "memo", "payee", "merchant", "name", "title"]:
            for key, orig in col_lower.items():
                if term in key:
                    mapping["description"] = orig
                    break
            if mapping["description"]:
                break

        # Amount detection
        for term in ["amount", "transaction amount", "debit", "total", "net", "value"]:
            for key, orig in col_lower.items():
                if term in key:
                    mapping["amount"] = orig
                    break
            if mapping["amount"]:
                break

        # Category detection
        for term in ["category", "type", "expense type", "tag"]:
            for key, orig in col_lower.items():
                if term in key:
                    mapping["category"] = orig
                    break
            if mapping["category"]:
                break

        return mapping

    @classmethod
    def preview_with_duplicates(
        cls,
        filepath: str,
        date_col: str,
        desc_col: str,
        amount_col: str,
        cat_col: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Processes rows with current column mapping and flags potential duplicate records.
        """
        ext = filepath.rsplit(".", 1)[1].lower()
        if ext == "csv":
            try:
                df = pd.read_csv(filepath, dtype=str).fillna("")
            except UnicodeDecodeError:
                df = pd.read_csv(filepath, encoding="latin1", dtype=str).fillna("")
        else:
            df = pd.read_excel(filepath, dtype=str).fillna("")

        preview_rows = []

        for idx, row in df.iterrows():
            raw_date = str(row.get(date_col, "")).strip()
            raw_desc = str(row.get(desc_col, "")).strip()
            raw_amount = str(row.get(amount_col, "")).strip()
            raw_cat = str(row.get(cat_col, "")).strip() if cat_col else ""

            # Clean and parse amount
            clean_amt_str = raw_amount.replace("$", "").replace(",", "").replace("€", "").replace("£", "").strip()
            try:
                amount_val = abs(float(clean_amt_str))
            except ValueError:
                continue  # skip invalid header/empty rows

            # Clean and parse date
            parsed_date = None
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y", "%Y/%m/%d", "%d %b %Y", "%B %d, %Y"):
                try:
                    parsed_date = datetime.strptime(raw_date.split("T")[0].split()[0], fmt).date()
                    break
                except Exception:
                    continue

            if not parsed_date:
                parsed_date = date.today()

            # DUPLICATE DETECTION CHECK
            existing_match = Transaction.query.filter(
                Transaction.date == parsed_date,
                Transaction.amount == amount_val,
                Transaction.description == raw_desc
            ).first()

            is_duplicate = existing_match is not None
            dup_reason = f"Matches existing transaction #{existing_match.id} on {parsed_date}" if is_duplicate else None

            # Category suggestion
            if raw_cat:
                cat_match = Category.query.filter(func.lower(Category.name) == raw_cat.lower()).first()
                cat_name = cat_match.name if cat_match else raw_cat
            else:
                sug = CategorizerService.suggest_category(raw_desc, amount_val)
                cat_name = sug["category_name"]

            preview_rows.append({
                "row_index": idx,
                "date": parsed_date.isoformat(),
                "description": raw_desc,
                "amount": amount_val,
                "category": cat_name,
                "is_duplicate": is_duplicate,
                "duplicate_reason": dup_reason,
            })

        return preview_rows

    @classmethod
    def commit_import(
        cls,
        filepath: str,
        original_filename: str,
        date_col: str,
        desc_col: str,
        amount_col: str,
        cat_col: str = "",
        skip_duplicates: bool = True
    ) -> ImportBatch:
        """
        Executes the import batch, commits transactions into the database,
        and logs summary telemetry.
        """
        preview_data = cls.preview_with_duplicates(
            filepath=filepath,
            date_col=date_col,
            desc_col=desc_col,
            amount_col=amount_col,
            cat_col=cat_col
        )

        batch = ImportBatch(
            filename=original_filename,
            total_rows=len(preview_data),
            imported_rows=0,
            skipped_duplicates=0,
            status="completed"
        )
        db.session.add(batch)
        db.session.flush()

        # Cache categories map
        all_cats = {c.name.lower(): c.id for c in Category.query.all()}
        default_cat_id = all_cats.get("shopping", list(all_cats.values())[0] if all_cats else 1)

        imported_count = 0
        skipped_count = 0

        for item in preview_data:
            if item["is_duplicate"] and skip_duplicates:
                skipped_count += 1
                continue

            # Resolve category id
            cat_name = item["category"]
            category_id = all_cats.get(cat_name.lower())
            if not category_id:
                # Create category if missing
                new_cat = Category(name=cat_name.title(), icon="tag", color="#6B7280")
                db.session.add(new_cat)
                db.session.flush()
                all_cats[cat_name.lower()] = new_cat.id
                category_id = new_cat.id

            t_date = datetime.strptime(item["date"], "%Y-%m-%d").date()
            t_amt = item["amount"]
            t_desc = item["description"]

            # Anomaly check
            is_anom, score, reason, _ = AnomalyDetectionService.evaluate_transaction(
                amount=t_amt,
                category_id=category_id,
                trans_date=t_date,
                transaction_type="expense"
            )

            tx = Transaction(
                amount=t_amt,
                transaction_type="expense",
                date=t_date,
                description=t_desc,
                category_id=category_id,
                import_batch_id=batch.id,
                is_anomaly=is_anom,
                anomaly_score=score,
                anomaly_reason=reason,
                notes=f"Imported from {original_filename}",
            )
            db.session.add(tx)
            imported_count += 1

        batch.imported_rows = imported_count
        batch.skipped_duplicates = skipped_count
        db.session.commit()

        # Clean up temporary upload file
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass

        return batch
