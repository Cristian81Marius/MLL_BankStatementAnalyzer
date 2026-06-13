import pytest
from statement_analysis.services.pdf_extractor import PDFExtractor


@pytest.fixture
def extractor() -> PDFExtractor:
    return PDFExtractor()


def test_extract_returns_extracted_content(extractor, minimal_pdf):
    result = extractor.extract(minimal_pdf)
    assert result.page_count >= 1
    assert isinstance(result.pages_text, list)
    assert isinstance(result.tables, list)
    assert isinstance(result.full_text, str)


def test_format_for_llm_includes_raw_text_section(extractor, minimal_pdf):
    content = extractor.extract(minimal_pdf)
    formatted = extractor.format_for_llm(content)
    assert "=== RAW TEXT ===" in formatted


def test_format_for_llm_includes_tables_section_when_tables_present(extractor):
    from unittest.mock import MagicMock, patch
    from io import BytesIO

    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Some text"
    mock_page.extract_tables.return_value = [[["Date", "Amount"], ["2024-01-01", "100.00"]]]

    with patch("pdfplumber.open") as mock_open:
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_open.return_value.__enter__.return_value = mock_pdf

        content = extractor.extract(b"%PDF-1.4 fake")
        formatted = extractor.format_for_llm(content)

    assert "=== EXTRACTED TABLES ===" in formatted
    assert "Date | Amount" in formatted


def test_multipage_pdf_has_page_break_markers(extractor):
    from unittest.mock import MagicMock, patch

    page1 = MagicMock()
    page1.extract_text.return_value = "Page one content"
    page1.extract_tables.return_value = []

    page2 = MagicMock()
    page2.extract_text.return_value = "Page two content"
    page2.extract_tables.return_value = []

    with patch("pdfplumber.open") as mock_open:
        mock_pdf = MagicMock()
        mock_pdf.pages = [page1, page2]
        mock_open.return_value.__enter__.return_value = mock_pdf

        content = extractor.extract(b"%PDF-1.4 fake")

    assert "--- PAGE BREAK ---" in content.full_text
    assert content.page_count == 2
