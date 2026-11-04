from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.recurring import RecurringRule
from app.services.recurring_service import RecurringService

def test_due_date_advancement():
    base = date(2026, 5, 1)

    assert RecurringService.calculate_next_due_date(base, "daily", 1) == date(2026, 5, 2)
    assert RecurringService.calculate_next_due_date(base, "weekly", 1) == date(2026, 5, 8)
    assert RecurringService.calculate_next_due_date(base, "monthly", 1) == date(2026, 6, 1)
    assert RecurringService.calculate_next_due_date(base, "yearly", 1) == date(2027, 5, 1)

def test_recurring_execution_and_duplicate_prevention(app):
    with app.app_context():
        util = Category.query.filter_by(name="Utilities").first()
        today = date.today()

        # Create monthly utility recurring rule due today
        rule = RecurringService.create_rule(
            description="Internet Bill",
            amount=65.0,
            category_id=util.id,
            frequency="monthly",
            start_date=today,
        )

        assert rule.next_due_date == today

        # First run: should process and generate 1 transaction
        created_1 = RecurringService.process_due_transactions(as_of_date=today)
        assert len(created_1) == 1
        assert created_1[0].amount == 65.0
        assert created_1[0].recurring_rule_id == rule.id

        # Rule should be advanced to next month
        refreshed_rule = RecurringRule.query.get(rule.id)
        assert refreshed_rule.next_due_date > today

        # Second run immediately on same day: DUPLICATE PREVENTION CHECK
        created_2 = RecurringService.process_due_transactions(as_of_date=today)
        assert len(created_2) == 0

        # Verify only 1 transaction exists in database
        tx_count = Transaction.query.filter_by(recurring_rule_id=rule.id).count()
        assert tx_count == 1

def test_upcoming_payments_projection(app):
    with app.app_context():
        ent = Category.query.filter_by(name="Entertainment").first()
        today = date.today()

        rule = RecurringService.create_rule(
            description="Streaming Service",
            amount=15.0,
            category_id=ent.id,
            frequency="monthly",
            start_date=today + timedelta(days=5),
        )

        upcoming = RecurringService.get_upcoming_payments(days_ahead=30)
        assert upcoming["upcoming_count"] >= 1
        assert upcoming["total_projected_expense"] >= 15.0

