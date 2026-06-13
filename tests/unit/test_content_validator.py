import pytest
from statement_analysis.services.content_validator import validate_statement_content


def test_valid_statement_passes():
    content = """
    Date        Description          Amount
    2024-01-15  AMAZON PURCHASE      52.30
    2024-01-16  PAYROLL DEPOSIT    3500.00
    2024-01-18  NETFLIX              12.99
    """
    valid, reason = validate_statement_content(content)
    assert valid is True
    assert reason == ""


def test_empty_content_fails():
    valid, reason = validate_statement_content("")
    assert valid is False
    assert "too little text" in reason


def test_no_amounts_fails():
    content = "This is just a regular document with some text and no financial data at all here."
    valid, reason = validate_statement_content(content)
    assert valid is False
    assert "amount" in reason.lower()


def test_no_dates_fails():
    content = "Purchase 52.30 shopping 18.99 groceries 34.50 transport 12.00 dining 9.99 coffee"
    valid, reason = validate_statement_content(content)
    assert valid is False
    assert "date" in reason.lower()


def test_single_amount_fails():
    content = "2024-01-15 Only one transaction here 52.30 nothing else"
    valid, reason = validate_statement_content(content)
    assert valid is False


def test_european_date_format_passes():
    content = """
    15.01.2024  LIDL SUPERMARKET     34.50
    16.01.2024  SALARY PAYMENT     2800.00
    18.01.2024  NETFLIX              12.99
    """
    valid, reason = validate_statement_content(content)
    assert valid is True


def test_currency_symbols_counted_as_amounts():
    content = """
    2024-01-01  SHOP A ONLINE STORE    $52.30
    2024-01-02  SHOP B SUPERMARKET     $18.99
    """
    valid, reason = validate_statement_content(content)
    assert valid is True


def test_month_name_date_format_passes():
    content = """
    15 Jan 2024   AMAZON        45.00
    16 Jan 2024   SALARY      3500.00
    18 Jan 2024   NETFLIX       12.99
    """
    valid, reason = validate_statement_content(content)
    assert valid is True
