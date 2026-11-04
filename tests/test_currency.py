import pytest
from datetime import date
from app.database import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.services.currency_service import CurrencyService

def test_currency_service_supported_currencies():
    currencies = CurrencyService.get_supported_currencies()
    codes = [c["code"] for c in currencies]
    assert "USD" in codes
    assert "EUR" in codes
    assert "GBP" in codes
    assert "INR" in codes
    assert "JPY" in codes

def test_currency_conversion_rates():
    # USD to USD
    amt, rate = CurrencyService.convert_to_base(100.0, "USD", "USD")
    assert amt == 100.0
    assert rate == 1.0

    # EUR to USD
    eur_amt, eur_rate = CurrencyService.convert_to_base(100.0, "EUR", "USD")
    assert eur_amt == 108.50
    assert eur_rate == 1.085

    # INR to USD
    inr_amt, inr_rate = CurrencyService.convert_to_base(1000.0, "INR", "USD")
    assert inr_amt == 12.00
    assert inr_rate == 0.012

def test_currency_formatting():
    assert CurrencyService.format_amount(1250.50, "USD") == "$1,250.50"
    assert CurrencyService.format_amount(45.00, "EUR") == "€45.00"
    assert CurrencyService.format_amount(5000, "JPY") == "¥5,000"

def test_add_transaction_with_foreign_currency(client, app):
    with app.app_context():
        cat = Category.query.first()
        res = client.post("/transactions/new", data={
            "description": "Tokyo Ramen Shop",
            "amount": "2000",
            "currency": "JPY",
            "date": date.today().isoformat(),
            "category_id": cat.id,
            "transaction_type": "expense",
        }, follow_redirects=True)

        assert res.status_code == 200
        tx = Transaction.query.filter_by(description="Tokyo Ramen Shop").first()
        assert tx is not None
        assert tx.currency == "JPY"
        assert tx.original_amount == 2000.0
        # 2000 * 0.0065 = 13.0 USD
        assert tx.amount == 13.0
        assert tx.exchange_rate == 0.0065

def test_api_currency_convert_endpoint(client):
    res = client.get("/api/currency/convert?amount=100&from=EUR&to=USD")
    assert res.status_code == 200
    data = res.get_json()
    assert data["converted_amount"] == 108.50
    assert data["exchange_rate"] == 1.085
    assert "$108.50" in data["formatted_converted"]
