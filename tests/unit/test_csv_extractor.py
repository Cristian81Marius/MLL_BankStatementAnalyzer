import pytest
from statement_analysis.services.csv_extractor import CSVExtractor


@pytest.fixture
def extractor() -> CSVExtractor:
    return CSVExtractor()


def test_comma_delimited_csv(extractor):
    data = b"Date,Description,Amount\n2024-01-15,AMAZON,52.30\n2024-01-16,SALARY,3500.00"
    result = extractor.extract_and_format(data)
    assert "Date | Description | Amount" in result
    assert "AMAZON" in result
    assert "3500.00" in result


def test_semicolon_delimited_csv(extractor):
    data = "Date;Description;Amount\n2024-01-15;CARREFOUR;45.00".encode("utf-8")
    result = extractor.extract_and_format(data)
    assert "CARREFOUR" in result


def test_tab_delimited_csv(extractor):
    data = "Date\tDescription\tAmount\n2024-01-15\tNETFLIX\t12.99".encode("utf-8")
    result = extractor.extract_and_format(data)
    assert "NETFLIX" in result


def test_utf8_bom_handled(extractor):
    # Explicit BOM bytes as produced by Excel CSV exports on Windows
    data = b"\xef\xbb\xbfDate,Description,Amount\n2024-01-15,SHOP,20.00"
    result = extractor.extract_and_format(data)
    assert "Date" in result
    assert "﻿" not in result  # BOM character must be stripped


def test_latin1_encoding(extractor):
    data = "Date,Description,Amount\n2024-01-15,Café,8.50".encode("latin-1")
    result = extractor.extract_and_format(data)
    assert "8.50" in result


def test_empty_rows_are_skipped(extractor):
    data = b"Date,Description,Amount\n\n2024-01-15,SHOP,20.00\n\n"
    result = extractor.extract_and_format(data)
    lines = [l for l in result.splitlines() if "|" in l]
    assert len(lines) == 2  # header + 1 data row


def test_output_starts_with_csv_table_header(extractor):
    data = b"Date,Amount\n2024-01-01,10.00"
    result = extractor.extract_and_format(data)
    assert result.startswith("=== CSV TABLE ===")


def test_empty_file_returns_empty_message(extractor):
    result = extractor.extract_and_format(b"")
    assert "empty" in result.lower()
