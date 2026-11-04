import os
import tempfile
from datetime import date
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.services.import_service import ImportService

def test_auto_detect_column_mapping():
    cols = ["Transaction Date", "Description / Payee", "Amount ($)", "Category Name"]
    mapping = ImportService.auto_detect_column_mapping(cols)

    assert mapping["date"] == "Transaction Date"
    assert mapping["description"] == "Description / Payee"
    assert mapping["amount"] == "Amount ($)"
    assert mapping["category"] == "Category Name"

def test_import_with_duplicate_detection(app):
    with app.app_context():
        food = Category.query.filter_by(name="Food & Dining").first()
        today = date.today()

        # Seed 1 existing transaction
        existing_tx = Transaction(
            amount=50.0,
            transaction_type="expense",
            date=today,
            description="Existing Dinner",
            category_id=food.id
        )
        db.session.add(existing_tx)
        db.session.commit()

        # Create temporary CSV statement with 1 duplicate and 1 unique row
        with tempfile.NamedTemporaryFile("w+", suffix=".csv", delete=False) as f:
            f.write("Date,Description,Amount,Category\n")
            f.write(f"{today.isoformat()},Existing Dinner,50.00,Food & Dining\n")
            f.write(f"{today.isoformat()},Unique New Grocery,85.50,Food & Dining\n")
            f_path = f.name

        try:
            preview = ImportService.preview_with_duplicates(
                filepath=f_path,
                date_col="Date",
                desc_col="Description",
                amount_col="Amount",
                cat_col="Category"
            )

            assert len(preview) == 2
            # First row should be flagged duplicate
            assert preview[0]["is_duplicate"] is True
            # Second row should be unique
            assert preview[1]["is_duplicate"] is False

            # Commit import with skip_duplicates=True
            batch = ImportService.commit_import(
                filepath=f_path,
                original_filename="test_statement.csv",
                date_col="Date",
                desc_col="Description",
                amount_col="Amount",
                cat_col="Category",
                skip_duplicates=True
            )

            assert batch.imported_rows == 1
            assert batch.skipped_duplicates == 1

            # Check database: should have 2 transactions total (1 seeded + 1 imported)
            total_txs = Transaction.query.count()
            assert total_txs == 2
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)

