from datetime import date, timedelta

from src.validate_load import validate


def good() -> dict:
    return {
        "employee_name": "Jane Doe",
        "employee_id": "E12345",
        "date": "2026-09-01",
        "amount": 100.0,
    }


def test_valid_record():
    status, issues, claim_date = validate(good())
    assert status == "valid"
    assert issues == []
    assert claim_date == date(2026, 9, 1)


def test_missing_field_is_rejected():
    rec = good()
    rec["amount"] = None
    status, issues, _ = validate(rec)
    assert status == "rejected"
    assert "missing_field:amount" in issues


def test_negative_amount_is_rejected():
    rec = good()
    rec["amount"] = -5.0
    status, issues, _ = validate(rec)
    assert status == "rejected"
    assert "invalid_amount" in issues


def test_future_date_is_rejected():
    rec = good()
    rec["date"] = (date.today() + timedelta(days=1)).isoformat()
    status, issues, _ = validate(rec)
    assert status == "rejected"
    assert "future_date" in issues


def test_malformed_date_is_rejected():
    rec = good()
    rec["date"] = "2026-13-45"
    status, issues, _ = validate(rec)
    assert status == "rejected"
    assert "invalid_date" in issues
