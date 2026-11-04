from typing import Tuple, Optional
import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy import func
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction

class AnomalyDetectionService:
    """
    Statistical and Machine Learning Anomaly Detection Service.
    Evaluates transaction amounts and category patterns against historical baselines.
    Flags unusual expenditures with plain-English, understandable explanations.
    Strictly avoids alarmist fraud terminology (labels as 'Unusual Expense' / 'High Outlier').
    """

    @classmethod
    def evaluate_transaction(
        cls,
        amount: float,
        category_id: int,
        trans_date,
        transaction_type: str = "expense",
        exclude_tx_id: Optional[int] = None
    ) -> Tuple[bool, float, Optional[str], str]:
        """
        Evaluates a candidate transaction against category and global spending baselines.
        Returns:
            - is_anomaly (bool)
            - anomaly_score (float, 0.0 to 1.0)
            - explanation (str or None)
            - detection_method ("STATISTICAL_IQR", "MACHINE_LEARNING", "NONE")
        """
        # Income is not flagged by expense anomaly detector
        if transaction_type != "expense" or amount <= 0:
            return False, 0.0, None, "NONE"

        # Fetch category details
        category = db.session.get(Category, category_id)
        cat_name = category.name if category else "Uncategorized"

        # Query historical transactions in the same category
        query = Transaction.query.filter(
            Transaction.category_id == category_id,
            Transaction.transaction_type == "expense"
        )
        if exclude_tx_id:
            query = query.filter(Transaction.id != exclude_tx_id)
        historical_txs = query.all()

        amounts = [t.amount for t in historical_txs]

        # Method 1: Category Statistical Baseline (IQR & Z-Score)
        if len(amounts) >= 3:
            q25, q50, q75 = np.percentile(amounts, [25, 50, 75])
            iqr = q75 - q25
            median = float(q50)
            mean = float(np.mean(amounts))
            std = float(np.std(amounts))

            # Upper boundary check
            upper_iqr_bound = q75 + (2.5 * iqr) if iqr > 0 else median * 3.0
            z_score = ((amount - mean) / std) if std > 0 else 0.0

            if amount > upper_iqr_bound or z_score >= 2.5:
                ratio = round(amount / median, 1) if median > 0 else round(amount / max(mean, 1.0), 1)
                severity = "significantly higher" if ratio >= 3.0 else "unusually higher"
                explanation = (
                    f"This purchase of ${amount:,.2f} is {severity} ({ratio}x) "
                    f"than your typical {cat_name} expense (typical median: ${median:,.2f})."
                )
                score = round(min(0.5 + (ratio * 0.1), 0.99), 2)
                return True, score, explanation, "STATISTICAL_IQR"

        # Method 2: Global spending baseline when category has very few samples
        all_expenses = Transaction.query.filter(
            Transaction.transaction_type == "expense"
        ).all()
        all_amounts = [t.amount for t in all_expenses]

        if len(all_amounts) >= 15:
            # Fit Isolation Forest across [amount, day_of_week]
            try:
                features = []
                for t in all_expenses:
                    dow = t.date.weekday() if hasattr(t.date, "weekday") else 0
                    features.append([t.amount, dow])
                
                iso = IsolationForest(contamination=0.04, random_state=42)
                iso.fit(features)
                
                cur_dow = trans_date.weekday() if hasattr(trans_date, "weekday") else 0
                pred = iso.predict([[amount, cur_dow]])[0]
                decision = float(iso.decision_function([[amount, cur_dow]])[0])

                if pred == -1 and amount > float(np.median(all_amounts)) * 2.0:
                    explanation = (
                        f"Atypical spending pattern: ${amount:,.2f} is substantially outside "
                        f"your overall historical transaction distribution."
                    )
                    score = round(min(0.70 + abs(decision), 0.95), 2)
                    return True, score, explanation, "MACHINE_LEARNING"
            except Exception:
                pass

        # Not anomalous
        return False, 0.0, None, "NONE"

    @classmethod
    def reevaluate_all_transactions(cls) -> int:
        """
        Scans all existing transactions in the database and updates their anomaly status.
        Useful after bulk imports or initial seeding.
        """
        transactions = Transaction.query.filter_by(transaction_type="expense").all()
        flagged_count = 0

        for tx in transactions:
            is_anom, score, reason, method = cls.evaluate_transaction(
                amount=tx.amount,
                category_id=tx.category_id,
                trans_date=tx.date,
                transaction_type=tx.transaction_type,
                exclude_tx_id=tx.id
            )
            tx.is_anomaly = is_anom
            tx.anomaly_score = score
            tx.anomaly_reason = reason
            if is_anom:
                flagged_count += 1

        db.session.commit()
        return flagged_count
