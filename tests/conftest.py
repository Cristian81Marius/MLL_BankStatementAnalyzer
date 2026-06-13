import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

SAMPLE_DIR = Path(__file__).parent / "data" / "sample_pdfs"

SAMPLE_CATEGORIES = [
    {"id": 1, "type": "income", "name": "Salary"},
    {"id": 8, "type": "expense", "name": "Food & Drink"},
    {"id": 3, "type": "expense", "name": "Entertainment"},
    {"id": 5, "type": "expense", "name": "Shopping"},
    {"id": 9, "type": "expense", "name": "Transport"},
]

SAMPLE_CATEGORIES_JSON = json.dumps(SAMPLE_CATEGORIES)


@pytest.fixture(scope="session")
def mock_llm_response() -> dict:
    return {
        "transactions": [
            {
                "date": "2024-01-15",
                "amount": 52.30,
                "description": "WHOLE FOODS MARKET",
                "category_id": 8,
            },
            {
                "date": "2024-01-16",
                "amount": 3500.00,
                "description": "PAYROLL DIRECT DEPOSIT",
                "category_id": 1,
            },
            {
                "date": "2024-01-18",
                "amount": 12.99,
                "description": "NETFLIX",
                "category_id": 3,
            },
        ],
        "currency": "USD",
        "confidence": 0.95,
    }


@pytest.fixture
def mock_anthropic_client(mock_llm_response) -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=json.dumps(mock_llm_response))]
    )
    return client


@pytest.fixture(scope="session")
def minimal_pdf() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n"
        b"2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n"
        b"3 0 obj\n<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]>>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n"
        b"trailer\n<</Size 4 /Root 1 0 R>>\nstartxref\n9\n%%EOF"
    )


TEST_API_KEY = "test-api-key-for-testing"


@pytest.fixture(scope="session")
def app():
    import os
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
    os.environ.setdefault("API_KEY", TEST_API_KEY)
    from statement_analysis.main import create_app
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as c:
        yield c
