from datetime import date
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.services.anomaly_service import AnomalyDetectionService

def test_anomaly_detection_with_outlier(app):
    with app.app_context():
        food = Category.query.filter_by(name="Food & Dining").first()
        today = date.today()

        # Seed 10 normal dining transactions ($20 - $45)
        for amt in [22.0, 25.5, 30.0, 28.0, 35.0, 24.0, 32.0, 40.0, 26.0, 31.0]:
            db.session.add(Transaction(
                amount=amt,
                transaction_type="expense",
                date=today,
                description="Normal Lunch",
                category_id=food.id
            ))
        db.session.commit()

        # Normal transaction: $33
        is_anom, score, reason, method = AnomalyDetectionService.evaluate_transaction(
            amount=33.0,
            category_id=food.id,
            trans_date=today,
            transaction_type="expense"
        )
        assert is_anom is False

        # Outlier transaction: $380 (12x normal median)
        is_anom, score, reason, method = AnomalyDetectionService.evaluate_transaction(
            amount=380.0,
            category_id=food.id,
            trans_date=today,
            transaction_type="expense"
        )
        assert is_anom is True
        assert score > 0.5
        assert reason is not None
        assert "Food & Dining" in reason

        # Ethical guideline check: Never label as fraud
        assert "fraud" not in reason.lower()
        assert "scam" not in reason.lower()

