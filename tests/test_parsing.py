from src.extract import parse_text

SAMPLE = """EXPENSE REIMBURSEMENT REQUEST
Claim ID: RC-2026-0001
Employee Name: Jane Doe
Employee ID: E12345
Department: Finance
Date: 2026-09-01
Category: Travel
Amount (USD): 123.45
Description: Taxi to airport.
"""


def test_parse_complete_form():
    r = parse_text(SAMPLE)
    assert r["employee_name"] == "Jane Doe"
    assert r["employee_id"] == "E12345"
    assert r["amount"] == 123.45


def test_empty_field_becomes_none():
    r = parse_text(SAMPLE.replace("Employee ID: E12345", "Employee ID: "))
    assert r["employee_id"] is None


def test_invalid_amount_becomes_none():
    r = parse_text(SAMPLE.replace("123.45", "abc"))
    assert r["amount"] is None
