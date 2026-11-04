import pytest
from datetime import date, timedelta
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.services.report_service import ReportService

def test_report_service_pdf_generation_empty(app):
    with app.app_context():
        today = date.today()
        start_date = today - timedelta(days=30)
        pdf_bytes = ReportService.generate_pdf_statement(start_date, today, user_name="Test User")
        
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b"%PDF")

def test_report_service_with_transactions(app):
    with app.app_context():
        today = date.today()
        health_cat = Category.query.filter(Category.name.ilike("%Health%")).first()
        food_cat = Category.query.filter(Category.name.ilike("%Food%")).first()
        inc_cat = Category.query.filter_by(is_income=True).first()

        t1 = Transaction(
            amount=3200.0,
            transaction_type="income",
            category_id=inc_cat.id,
            date=today - timedelta(days=10),
            description="Monthly Paycheck"
        )
        t2 = Transaction(
            amount=145.0,
            transaction_type="expense",
            category_id=food_cat.id,
            date=today - timedelta(days=5),
            description="Grocery supermarket"
        )
        t3 = Transaction(
            amount=85.0,
            transaction_type="expense",
            category_id=health_cat.id,
            date=today - timedelta(days=2),
            description="Prescription medications pharmacy"
        )
        db.session.add_all([t1, t2, t3])
        db.session.commit()

        pdf_bytes = ReportService.generate_pdf_statement(today - timedelta(days=15), today, user_name="Alice Smith")
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF")

def test_export_pdf_route_month(client):
    res = client.get("/insights/export/pdf?period=month")
    assert res.status_code == 200
    assert res.content_type == "application/pdf"
    assert res.data.startswith(b"%PDF")
    assert "attachment;" in res.headers.get("Content-Disposition", "")
    assert "SmartExpense_Statement_month_" in res.headers.get("Content-Disposition", "")

def test_export_pdf_route_ytd(client):
    res = client.get("/insights/export/pdf?period=ytd")
    assert res.status_code == 200
    assert res.content_type == "application/pdf"
    assert res.data.startswith(b"%PDF")
    assert "SmartExpense_Statement_ytd_" in res.headers.get("Content-Disposition", "")

def test_export_pdf_route_custom(client):
    res = client.get("/insights/export/pdf?period=custom&start_date=2026-01-01&end_date=2026-06-01")
    assert res.status_code == 200
    assert res.content_type == "application/pdf"
    assert res.data.startswith(b"%PDF")

