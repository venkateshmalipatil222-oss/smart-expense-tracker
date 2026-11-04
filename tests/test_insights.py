from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.services.insight_service import InsightService

def test_spending_overview(app):
    with app.app_context():
        food = Category.query.filter_by(name="Food & Dining").first()
        income_cat = Category.query.filter_by(name="Income").first()
        today = date.today()

        t1 = Transaction(amount=3000.0, transaction_type="income", date=today, description="Salary", category_id=income_cat.id)
        t2 = Transaction(amount=120.0, transaction_type="expense", date=today, description="Groceries", category_id=food.id)
        t3 = Transaction(amount=45.0, transaction_type="expense", date=today, description="Dinner", category_id=food.id)
        db.session.add_all([t1, t2, t3])
        db.session.commit()

        overview = InsightService.get_spending_overview(today)

        assert overview["total_income"] == 3000.0
        assert overview["total_expense"] == 165.0
        assert overview["net_savings"] == 2835.0
        assert overview["highest_category"]["category_name"] == "Food & Dining"
        assert overview["highest_category"]["total"] == 165.0

def test_month_over_month_comparison(app):
    with app.app_context():
        food = Category.query.filter_by(name="Food & Dining").first()
        today = date.today()
        prev_month = today - relativedelta(months=1)

        # Prev month expense: $100
        prev_tx = Transaction(amount=100.0, transaction_type="expense", date=prev_month.replace(day=5), description="Past Groceries", category_id=food.id)
        # Current month expense: $250
        curr_tx = Transaction(amount=250.0, transaction_type="expense", date=today.replace(day=5), description="Current Groceries", category_id=food.id)
        db.session.add_all([prev_tx, curr_tx])
        db.session.commit()

        mom = InsightService.compare_month_over_month(today)

        assert mom["current_total"] == 250.0
        assert mom["previous_total"] == 100.0
        assert mom["difference"] == 150.0
        assert mom["percent_change"] == 150.0
        assert mom["direction"] == "increased"

def test_personalized_recommendations_provenance(app):
    with app.app_context():
        food = Category.query.filter_by(name="Food & Dining").first()
        income_cat = Category.query.filter_by(name="Income").first()
        today = date.today()
        prev_month = today - relativedelta(months=1)

        # Baseline previous month: $80
        db.session.add(Transaction(amount=80.0, transaction_type="expense", date=prev_month.replace(day=3), description="Groceries", category_id=food.id))
        # Current month surge: $350
        db.session.add(Transaction(amount=350.0, transaction_type="expense", date=today.replace(day=3), description="Dining Out", category_id=food.id))
        # Income
        db.session.add(Transaction(amount=2000.0, transaction_type="income", date=today.replace(day=1), description="Salary", category_id=income_cat.id))
        db.session.commit()

        recs = InsightService.generate_recommendations(today)
        assert len(recs) > 0

        # Verify presence of provenance tags
        types = {r["type"] for r in recs}
        assert "RULE_BASED" in types or "STATISTICAL_ML" in types

        # Check rationale field is populated
        for r in recs:
            assert "rationale" in r
            assert len(r["rationale"]) > 10
            assert "suggestion" in r

