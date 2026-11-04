import pytest
from datetime import date, timedelta
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.recurring import RecurringRule
from app.services.forecast_service import ForecastService

def test_forecast_calculation_and_confidence_bounds(app):
    with app.app_context():
        today = date.today()
        cat_inc = Category.query.filter_by(is_income=True).first()
        cat_exp = Category.query.filter_by(is_income=False).first()

        # Add initial income and some historical expenses
        db.session.add(Transaction(
            amount=5000.0,
            transaction_type="income",
            date=today - timedelta(days=20),
            description="Monthly Paycheck",
            category_id=cat_inc.id
        ))

        db.session.add(Transaction(
            amount=50.0,
            transaction_type="expense",
            date=today - timedelta(days=10),
            description="Grocery run",
            category_id=cat_exp.id
        ))

        db.session.add(Transaction(
            amount=40.0,
            transaction_type="expense",
            date=today - timedelta(days=5),
            description="Gas fillup",
            category_id=cat_exp.id
        ))

        # Add a scheduled recurring rule due in 10 days
        db.session.add(RecurringRule(
            description="Broadband Internet",
            amount=75.0,
            category_id=cat_exp.id,
            frequency="monthly",
            interval=1,
            start_date=today,
            next_due_date=today + timedelta(days=10),
            is_active=True
        ))
        db.session.commit()

        forecast = ForecastService.generate_30d_forecast(today)

        assert "current_balance" in forecast
        assert forecast["current_balance"] == round(5000.0 - 50.0 - 40.0, 2)
        assert "projected_30d_balance" in forecast
        assert len(forecast["forecast_points"]) == 30
        assert forecast["liquidity_risk"] in ["LOW", "MODERATE", "HIGH"]
        assert forecast["total_upcoming_bills_30d"] >= 75.0

        # Verify confidence intervals monotonicity
        for pt in forecast["forecast_points"]:
            assert pt["upper_bound"] >= pt["expected_balance"]
            assert pt["expected_balance"] >= pt["lower_bound"]
            assert "scheduled_bills" in pt

def test_api_forecast_endpoint(client):
    res = client.get("/insights/api/forecast")
    assert res.status_code == 200
    data = res.get_json()
    assert "current_balance" in data
    assert "forecast_points" in data
    assert len(data["forecast_points"]) == 30
