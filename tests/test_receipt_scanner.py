from datetime import date
from app.services.receipt_service import ReceiptScannerService

def test_parse_entities_standard_receipt():
    sample_text = """
    TRADER JOE'S #142
    SAN FRANCISCO, CA
    DATE: 2026-10-15  14:32
    ORGANIC MILK        $4.99
    SOURDOUGH BREAD     $3.50
    HONEYCRISP APPLES   $6.25
    SUBTOTAL           $14.74
    TAX                 $1.18
    TOTAL              $15.92
    THANK YOU FOR SHOPPING!
    """

    parsed = ReceiptScannerService.parse_entities(sample_text)

    assert "Trader" in parsed["merchant"] or "Joe" in parsed["merchant"]
    assert parsed["date"] == date(2026, 10, 15)
    assert parsed["amount"] == 15.92
    assert parsed["confidence_score"] >= 0.7

def test_parse_entities_alternate_date_format():
    sample_text = """
    WALMART SUPERCENTER
    10/24/2026
    ITEMS: 3
    BALANCE DUE: $48.75
    """

    parsed = ReceiptScannerService.parse_entities(sample_text)

    assert "Walmart" in parsed["merchant"]
    assert parsed["date"] == date(2026, 10, 24)
    assert parsed["amount"] == 48.75
    assert parsed["confidence_score"] >= 0.7

def test_parse_entities_incomplete_ocr_fallback():
    # Incomplete or blurred text
    sample_text = "WELCOME STORE\nSOME RANDOM UNREADABLE NOISE"
    parsed = ReceiptScannerService.parse_entities(sample_text)

    # Should gracefully provide fallback without crashing
    assert parsed["merchant"] is not None
    assert parsed["amount"] == 0.0
    assert parsed["date"] == date.today()
    assert parsed["confidence_score"] <= 0.5

