import base64
from unittest.mock import patch

from tests.conftest import SAMPLE_CATEGORIES, TEST_API_KEY

AUTH = {"X-API-Key": TEST_API_KEY}


def test_base64_pdf_returns_200(client, minimal_pdf, mock_llm_response):
    encoded = base64.b64encode(minimal_pdf).decode()
    with patch(
        "statement_analysis.services.llm_parser.LLMParser._call_claude",
        return_value=mock_llm_response,
    ):
        resp = client.post(
            "/api/v1/analyze/base64",
            json={
                "pdf_data": encoded,
                "file_type": "pdf",
                "bank_name": "Test Bank",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "categories": SAMPLE_CATEGORIES,
            },
            headers=AUTH,
        )
    assert resp.status_code == 200
    assert resp.json()["transaction_count"] == 3


def test_missing_api_key_returns_401(client, minimal_pdf):
    encoded = base64.b64encode(minimal_pdf).decode()
    resp = client.post(
        "/api/v1/analyze/base64",
        json={
            "pdf_data": encoded,
            "file_type": "pdf",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "categories": SAMPLE_CATEGORIES,
        },
    )
    assert resp.status_code == 401


def test_base64_csv_returns_200(client, mock_llm_response):
    csv_bytes = b"Date,Description,Amount,Type\n2024-01-15,AMAZON,52.30,expense"
    encoded = base64.b64encode(csv_bytes).decode()
    with patch(
        "statement_analysis.services.llm_parser.LLMParser._call_claude",
        return_value=mock_llm_response,
    ):
        resp = client.post(
            "/api/v1/analyze/base64",
            json={
                "pdf_data": encoded,
                "file_type": "csv",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "categories": SAMPLE_CATEGORIES,
            },
            headers=AUTH,
        )
    assert resp.status_code == 200


def test_base64_pdf_rejects_non_pdf_bytes(client):
    not_pdf = base64.b64encode(b"not a pdf").decode()
    resp = client.post(
        "/api/v1/analyze/base64",
        json={
            "pdf_data": not_pdf,
            "file_type": "pdf",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "categories": SAMPLE_CATEGORIES,
        },
        headers=AUTH,
    )
    assert resp.status_code == 400


def test_base64_invalid_base64_returns_422(client):
    resp = client.post(
        "/api/v1/analyze/base64",
        json={
            "pdf_data": "!!!not-valid-base64!!!",
            "file_type": "pdf",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "categories": SAMPLE_CATEGORIES,
        },
        headers=AUTH,
    )
    assert resp.status_code == 422


def test_end_date_before_start_date_returns_422(client, minimal_pdf):
    encoded = base64.b64encode(minimal_pdf).decode()
    resp = client.post(
        "/api/v1/analyze/base64",
        json={
            "pdf_data": encoded,
            "file_type": "pdf",
            "start_date": "2024-01-31",
            "end_date": "2024-01-01",
            "categories": SAMPLE_CATEGORIES,
        },
        headers=AUTH,
    )
    assert resp.status_code == 422
