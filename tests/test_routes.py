import json
from datetime import date
from app.models.category import Category
from app.models.transaction import Transaction

def test_dashboard_route(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Financial Overview" in res.data

def test_transactions_route(client):
    res = client.get("/transactions")
    assert res.status_code == 200
    assert b"Transactions" in res.data

def test_add_transaction_route(client, app):
    with app.app_context():
        food = Category.query.filter_by(name="Food & Dining").first()
        res = client.post("/transactions/new", data={
            "description": "Chipotle Lunch",
            "amount": "14.50",
            "date": date.today().isoformat(),
            "category_id": food.id,
            "transaction_type": "expense",
        }, follow_redirects=True)

        assert res.status_code == 200
        assert b"Transaction recorded" in res.data

        tx = Transaction.query.filter_by(description="Chipotle Lunch").first()
        assert tx is not None
        assert tx.amount == 14.50

def test_api_categorize_route(client):
    res = client.get("/api/categorize?description=Starbucks")
    assert res.status_code == 200
    data = res.get_json()
    assert data["category_name"] == "Food & Dining"
    assert data["method"] == "RULE_BASED"

def test_insights_routes(client):
    res1 = client.get("/insights/")
    assert res1.status_code == 200
    assert b"AI Financial Insights" in res1.data

    res2 = client.get("/insights/api/chart-data")
    assert res2.status_code == 200
    data = res2.get_json()
    assert "history" in data
    assert "category_breakdown" in data

def test_receipts_route(client):
    res = client.get("/receipts/")
    assert res.status_code == 200
    assert b"Receipt Scanner" in res.data

def test_recurring_routes(client, app):
    with app.app_context():
        util = Category.query.filter_by(name="Utilities").first()
        res1 = client.get("/recurring/")
        assert res1.status_code == 200

        res2 = client.post("/recurring/new", data={
            "description": "Monthly Gas Bill",
            "amount": "55.00",
            "frequency": "monthly",
            "interval": "1",
            "start_date": date.today().isoformat(),
            "category_id": util.id,
            "transaction_type": "expense",
        }, follow_redirects=True)

        assert res2.status_code == 200
        assert b"Monthly Gas Bill" in res2.data

def test_goals_routes(client, app):
    with app.app_context():
        res1 = client.get("/goals/")
        assert res1.status_code == 200

        res2 = client.post("/goals/new", data={
            "title": "Home Renovation",
            "target_amount": "5000.00",
            "current_amount": "1000.00",
            "target_date": "2027-01-01",
        }, follow_redirects=True)

        assert res2.status_code == 200
        assert b"Home Renovation" in res2.data

def test_import_route(client):
    res = client.get("/import/")
    assert res.status_code == 200
    assert b"Bank Statement Import" in res.data

