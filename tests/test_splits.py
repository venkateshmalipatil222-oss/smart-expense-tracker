import pytest
from datetime import date, timedelta
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.split import TransactionSplit, ExpenseShare
from app.services.split_service import SplitService

def test_itemized_splits_success(app):
    with app.app_context():
        cats = Category.query.all()
        cat1 = cats[0]
        cat2 = cats[1]

        tx = Transaction(
            amount=100.0,
            transaction_type="expense",
            category_id=cat1.id,
            date=date.today(),
            description="Department store shopping"
        )
        db.session.add(tx)
        db.session.commit()

        splits_data = [
            {"category_id": cat1.id, "amount": 60.0, "description": "Groceries"},
            {"category_id": cat2.id, "amount": 40.0, "description": "Household goods"},
        ]

        res = SplitService.apply_itemized_splits(tx.id, splits_data)
        assert res["success"] is True
        assert res["total_splits"] == 2

        refreshed_tx = db.session.get(Transaction, tx.id)
        assert refreshed_tx.is_split is True
        assert len(refreshed_tx.splits) == 2
        assert sum(s.amount for s in refreshed_tx.splits) == 100.0

def test_itemized_splits_sum_mismatch(app):
    with app.app_context():
        cat = Category.query.first()
        tx = Transaction(
            amount=100.0,
            transaction_type="expense",
            category_id=cat.id,
            date=date.today(),
            description="Lunch"
        )
        db.session.add(tx)
        db.session.commit()

        # Split items totaling only 80.0
        splits_data = [
            {"category_id": cat.id, "amount": 50.0, "description": "Part 1"},
            {"category_id": cat.id, "amount": 30.0, "description": "Part 2"},
        ]

        with pytest.raises(ValueError) as excinfo:
            SplitService.apply_itemized_splits(tx.id, splits_data)
        assert "does not match transaction total" in str(excinfo.value)

def test_expense_shares_creation_and_exceed_limit(app):
    with app.app_context():
        cat = Category.query.first()
        tx = Transaction(
            amount=120.0,
            transaction_type="expense",
            category_id=cat.id,
            date=date.today(),
            description="Group Dinner"
        )
        db.session.add(tx)
        db.session.commit()

        shares_data = [
            {"person_name": "Alice", "amount": 40.0, "notes": "Main dish"},
            {"person_name": "Bob", "amount": 40.0, "notes": "Appetizers"},
        ]

        res = SplitService.apply_expense_shares(tx.id, shares_data)
        assert res["success"] is True
        assert res["total_shares"] == 2

        refreshed_tx = db.session.get(Transaction, tx.id)
        assert refreshed_tx.is_shared is True
        assert refreshed_tx.unsettled_shares_total == 80.0

        # Attempt to allocate more than transaction total
        excessive_shares = [
            {"person_name": "Charlie", "amount": 150.0, "notes": "Too much"}
        ]
        with pytest.raises(ValueError) as excinfo:
            SplitService.apply_expense_shares(tx.id, excessive_shares)
        assert "cannot exceed transaction amount" in str(excinfo.value)

def test_settle_and_unsettle_share(app):
    with app.app_context():
        cat = Category.query.first()
        tx = Transaction(
            amount=90.0,
            transaction_type="expense",
            category_id=cat.id,
            date=date.today(),
            description="Concert Tickets"
        )
        db.session.add(tx)
        db.session.commit()

        SplitService.apply_expense_shares(tx.id, [
            {"person_name": "David", "amount": 45.0, "notes": "Ticket"}
        ])

        summary1 = SplitService.get_sharing_summary()
        assert summary1["total_unsettled_amount"] >= 45.0
        assert summary1["unsettled_count"] >= 1

        share = ExpenseShare.query.filter_by(person_name="David").first()
        assert share.is_settled is False

        # Settle
        res_settle = SplitService.settle_share(share.id)
        assert res_settle["success"] is True

        refreshed = db.session.get(ExpenseShare, share.id)
        assert refreshed.is_settled is True
        assert refreshed.settled_at is not None

        summary2 = SplitService.get_sharing_summary()
        assert summary2["total_settled_amount"] >= 45.0

        # Unsettle
        res_unsettle = SplitService.unsettle_share(share.id)
        assert res_unsettle["success"] is True
        refreshed2 = db.session.get(ExpenseShare, share.id)
        assert refreshed2.is_settled is False

def test_splits_routes_and_api(client, app):
    with app.app_context():
        cat = Category.query.first()
        tx = Transaction(
            amount=60.0,
            transaction_type="expense",
            category_id=cat.id,
            date=date.today(),
            description="Taxi ride"
        )
        db.session.add(tx)
        db.session.commit()
        tx_id = tx.id

    # 1. GET /splits/
    res = client.get("/splits/")
    assert res.status_code == 200
    assert b"Group Sharing" in res.data

    # 2. POST shares via API
    res_shares = client.post(f"/splits/api/transaction/{tx_id}/shares", json={
        "shares": [
            {"person_name": "Emma", "amount": 30.0, "notes": "Half fare"}
        ]
    })
    assert res_shares.status_code == 200
    data = res_shares.get_json()
    assert data["success"] is True

    # 3. GET /splits/api/summary
    res_sum = client.get("/splits/api/summary")
    assert res_sum.status_code == 200
    sum_data = res_sum.get_json()
    assert sum_data["total_unsettled_amount"] >= 30.0

    # 4. Settle share
    with app.app_context():
        share = ExpenseShare.query.filter_by(person_name="Emma").first()
        share_id = share.id

    res_settle = client.post(f"/splits/settle/{share_id}", follow_redirects=True)
    assert res_settle.status_code == 200
    assert b"successfully settled" in res_settle.data

