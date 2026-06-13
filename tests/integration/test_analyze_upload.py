from unittest.mock import patch

from tests.conftest import SAMPLE_CATEGORIES_JSON, TEST_API_KEY

FORM_BASE = {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "categories": SAMPLE_CATEGORIES_JSON,
}
AUTH = {"X-API-Key": TEST_API_KEY}


def test_health_endpoint_returns_200_without_key(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_missing_api_key_returns_401(client, minimal_pdf):
    resp = client.post(
        "/api/v1/analyze",
        files={"file": ("statement.pdf", minimal_pdf, "application/pdf")},
        data=FORM_BASE,
    )
    assert resp.status_code == 401


def test_wrong_api_key_returns_401(client, minimal_pdf):
    resp = client.post(
        "/api/v1/analyze",
        files={"file": ("statement.pdf", minimal_pdf, "application/pdf")},
        data=FORM_BASE,
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_valid_pdf_upload_returns_200(client, minimal_pdf, mock_llm_response):
    with patch(
        "statement_analysis.services.llm_parser.LLMParser._call_claude",
        return_value=mock_llm_response,
    ):
        resp = client.post(
            "/api/v1/analyze",
            files={"file": ("statement.pdf", minimal_pdf, "application/pdf")},
            data={**FORM_BASE, "bank_name": "Test Bank"},
            headers=AUTH,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["transaction_count"] == 3
    assert body["bank_name"] == "Test Bank"
    assert body["statement_period"] == "01 Jan 2024 – 31 Jan 2024"


def test_valid_csv_upload_returns_200(client, mock_llm_response):
    csv_bytes = b"Date,Description,Amount\n2024-01-15,AMAZON,52.30\n2024-01-16,SALARY,3500.00"
    with patch(
        "statement_analysis.services.llm_parser.LLMParser._call_claude",
        return_value=mock_llm_response,
    ):
        resp = client.post(
            "/api/v1/analyze",
            files={"file": ("statement.csv", csv_bytes, "text/csv")},
            data=FORM_BASE,
            headers=AUTH,
        )
    assert resp.status_code == 200
    assert resp.json()["transaction_count"] == 3


def test_csv_detected_by_filename_when_mime_is_octet_stream(client, mock_llm_response):
    csv_bytes = b"Date,Description,Amount\n2024-01-15,SHOP,20.00"
    with patch(
        "statement_analysis.services.llm_parser.LLMParser._call_claude",
        return_value=mock_llm_response,
    ):
        resp = client.post(
            "/api/v1/analyze",
            files={"file": ("export.csv", csv_bytes, "application/octet-stream")},
            data=FORM_BASE,
            headers=AUTH,
        )
    assert resp.status_code == 200


def test_response_transactions_have_category_id_and_name(client, minimal_pdf, mock_llm_response):
    with patch(
        "statement_analysis.services.llm_parser.LLMParser._call_claude",
        return_value=mock_llm_response,
    ):
        resp = client.post(
            "/api/v1/analyze",
            files={"file": ("statement.pdf", minimal_pdf, "application/pdf")},
            data=FORM_BASE,
            headers=AUTH,
        )
    for tx in resp.json()["expenses"] + resp.json()["income"]:
        assert "category_id" in tx
        assert "category_name" in tx


def test_wrong_mime_type_returns_415(client, minimal_pdf):
    resp = client.post(
        "/api/v1/analyze",
        files={"file": ("note.html", b"<html/>", "text/html")},
        data=FORM_BASE,
        headers=AUTH,
    )
    assert resp.status_code == 415


def test_non_pdf_bytes_with_pdf_extension_returns_400(client):
    resp = client.post(
        "/api/v1/analyze",
        files={"file": ("fake.pdf", b"This is not a PDF at all", "application/pdf")},
        data=FORM_BASE,
        headers=AUTH,
    )
    assert resp.status_code == 400


def test_oversized_file_returns_413(client):
    big = b"%PDF" + b"x" * (51 * 1024 * 1024)
    resp = client.post(
        "/api/v1/analyze",
        files={"file": ("big.pdf", big, "application/pdf")},
        data=FORM_BASE,
        headers=AUTH,
    )
    assert resp.status_code == 413


def test_missing_required_fields_returns_422(client, minimal_pdf):
    resp = client.post(
        "/api/v1/analyze",
        files={"file": ("statement.pdf", minimal_pdf, "application/pdf")},
        headers=AUTH,
    )
    assert resp.status_code == 422


def test_invalid_categories_json_returns_422(client, minimal_pdf, mock_llm_response):
    with patch(
        "statement_analysis.services.llm_parser.LLMParser._call_claude",
        return_value=mock_llm_response,
    ):
        resp = client.post(
            "/api/v1/analyze",
            files={"file": ("statement.pdf", minimal_pdf, "application/pdf")},
            data={**FORM_BASE, "categories": "not-json"},
            headers=AUTH,
        )
    assert resp.status_code == 422
