import pytest
from datetime import date, timedelta
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.recurring import RecurringRule
from app.models.user import User
from app.services.copilot_service import CopilotService

def test_copilot_affordability_safe(app):
    with app.app_context():
        cat = Category.query.first()
        today = date.today()

        inc = Transaction(
            amount=5000.0,
            transaction_type="income",
            category_id=cat.id,
            date=today - timedelta(days=2),
            description="Salary deposit",
            currency="USD",
            exchange_rate=1.0,
            original_amount=5000.0
        )
        db.session.add(inc)
        db.session.commit()

        res = CopilotService.process_query("Can I afford a $100 jacket?", reference_date=today)
        assert res["intent"] == "AFFORDABILITY_CHECK"
        assert res["status"] in ["APPROVED", "CAUTION"]
        assert res["data"]["amount"] == 100.0
        assert "verdict" in res
        assert "Safe" in res["verdict"] or "Caution" in res["verdict"]

def test_copilot_affordability_insufficient_funds(app):
    with app.app_context():
        today = date.today()
        res = CopilotService.process_query("Can I buy a luxury boat for $999999?", reference_date=today)
        assert res["intent"] == "AFFORDABILITY_CHECK"
        assert res["status"] == "NOT_RECOMMENDED"
        assert "High Risk" in res["verdict"]
        assert res["data"]["amount"] == 999999.0

def test_copilot_recurring_audit(app):
    with app.app_context():
        cat = Category.query.first()
        today = date.today()

        rule = RecurringRule(
            description="Gym Membership",
            amount=65.0,
            category_id=cat.id,
            frequency="monthly",
            interval=1,
            start_date=today - timedelta(days=30),
            next_due_date=today + timedelta(days=5),
            is_active=True
        )
        db.session.add(rule)
        db.session.commit()

        res = CopilotService.process_query("What are my recurring subscriptions?", reference_date=today)
        assert res["intent"] == "RECURRING_AUDIT"
        assert res["data"]["active_count"] >= 1
        assert "Gym Membership" in res["reply"]

def test_copilot_category_spending(app):
    with app.app_context():
        today = date.today()
        food_cat = Category.query.filter(Category.name.ilike("%Food%")).first()
        if not food_cat:
            food_cat = Category.query.first()

        tx = Transaction(
            amount=42.50,
            transaction_type="expense",
            category_id=food_cat.id,
            date=today - timedelta(days=3),
            description="Dinner at Italian Bistro",
            currency="USD",
            exchange_rate=1.0,
            original_amount=42.50
        )
        db.session.add(tx)
        db.session.commit()

        query_text = f"How much did I spend on {food_cat.name}?"
        res = CopilotService.process_query(query_text, reference_date=today)
        assert res["intent"] == "SPENDING_BY_CATEGORY"
        assert res["data"]["category_name"] == food_cat.name
        assert res["data"]["total_spent"] >= 42.50

def test_copilot_api_endpoint(client, app):
    # Unauthenticated should redirect to login
    resp = client.post("/api/copilot/chat", json={"query": "Can I afford $50?"})
    assert resp.status_code == 302

    # Register/login user
    with app.app_context():
        user = User(username="copilot_user", email="copilot@example.com")
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.commit()

    client.post("/auth/login", data={
        "identifier": "copilot_user",
        "password": "SecurePass123!"
    })

    # Authenticated request
    resp2 = client.post("/api/copilot/chat", json={"query": "Can I afford $50?"})
    assert resp2.status_code == 200
    data = resp2.get_json()
    assert data["success"] is True
    assert data["intent"] == "AFFORDABILITY_CHECK"
    assert "reply" in data
