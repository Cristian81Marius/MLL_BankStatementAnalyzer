import json
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from statement_analysis.models.request import CategoryInput
from statement_analysis.services.llm_parser import LLMParser

CATEGORIES = [
    CategoryInput(id=1, type="income", name="Salary"),
    CategoryInput(id=8, type="expense", name="Food & Drink"),
    CategoryInput(id=3, type="expense", name="Entertainment"),
]

START = date(2024, 1, 1)
END = date(2024, 1, 31)


@pytest.fixture
def parser(mock_anthropic_client) -> LLMParser:
    return LLMParser(client=mock_anthropic_client, model="claude-haiku-4-5-20251001")


def test_parse_splits_expenses_and_income(parser):
    result = parser.parse("some bank statement content", None, START, END, CATEGORIES)
    assert len(result.expenses) == 2  # Food & Drink + Entertainment
    assert len(result.income) == 1    # Salary


def test_parse_totals_are_correct(parser):
    result = parser.parse("some content", None, START, END, CATEGORIES)
    assert result.total_expenses == Decimal("52.30") + Decimal("12.99")
    assert result.total_income == Decimal("3500.00")


def test_parse_metadata_is_populated(parser):
    result = parser.parse("some content", "Test Bank", START, END, CATEGORIES)
    assert result.bank_name == "Test Bank"
    assert result.statement_period == "01 Jan 2024 – 31 Jan 2024"
    assert result.currency == "USD"
    assert result.transaction_count == 3


def test_type_derived_from_category_not_llm(parser):
    result = parser.parse("some content", None, START, END, CATEGORIES)
    salary_tx = next(t for t in result.income if "PAYROLL" in t.description)
    assert salary_tx.type == "income"
    assert salary_tx.category_id == 1
    assert salary_tx.category_name == "Salary"


def test_category_name_and_id_in_response(parser):
    result = parser.parse("some content", None, START, END, CATEGORIES)
    food_tx = next(t for t in result.expenses if "WHOLE FOODS" in t.description)
    assert food_tx.category_id == 8
    assert food_tx.category_name == "Food & Drink"


def test_unknown_category_id_is_skipped_with_warning(mock_anthropic_client, mock_llm_response):
    bad = {**mock_llm_response, "transactions": [
        {"date": "2024-01-10", "amount": 20.0, "description": "UNKNOWN CAT", "category_id": 999},
        {"date": "2024-01-10", "amount": 10.0, "description": "FOOD", "category_id": 8},
    ]}
    mock_anthropic_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=json.dumps(bad))]
    )
    p = LLMParser(client=mock_anthropic_client, model="test")
    result = p.parse("content", None, START, END, CATEGORIES)
    assert result.transaction_count == 1
    assert any("999" in w for w in result.warnings)


def test_transaction_outside_date_range_is_filtered(mock_anthropic_client, mock_llm_response):
    outside = {**mock_llm_response, "transactions": [
        {"date": "2023-12-31", "amount": 50.0, "description": "OLD TX", "category_id": 8},
        {"date": "2024-01-15", "amount": 30.0, "description": "IN RANGE", "category_id": 8},
        {"date": "2024-02-01", "amount": 20.0, "description": "FUTURE TX", "category_id": 8},
    ]}
    mock_anthropic_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=json.dumps(outside))]
    )
    p = LLMParser(client=mock_anthropic_client, model="test")
    result = p.parse("content", None, START, END, CATEGORIES)
    assert result.transaction_count == 1
    assert result.expenses[0].description == "IN RANGE"


def test_markdown_fences_are_stripped(mock_anthropic_client, mock_llm_response):
    fenced = f"```json\n{json.dumps(mock_llm_response)}\n```"
    mock_anthropic_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=fenced)]
    )
    p = LLMParser(client=mock_anthropic_client, model="test")
    result = p.parse("content", None, START, END, CATEGORIES)
    assert result.transaction_count == 3


def test_chunk_content_does_not_exceed_max(mock_anthropic_client):
    p = LLMParser(client=mock_anthropic_client, model="test", max_content_chars=500)
    big = "A" * 3000
    chunks = p._chunk_content(big)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 500


def test_zero_amount_transaction_is_skipped(mock_anthropic_client):
    resp = {"transactions": [
        {"date": "2024-01-01", "amount": 0, "description": "ZERO", "category_id": 8},
        {"date": "2024-01-02", "amount": 10.0, "description": "VALID", "category_id": 8},
    ], "currency": "USD", "confidence": 0.9}
    mock_anthropic_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=json.dumps(resp))]
    )
    p = LLMParser(client=mock_anthropic_client, model="test")
    result = p.parse("content", None, START, END, CATEGORIES)
    assert result.transaction_count == 1


def test_duplicate_transactions_are_deduplicated(mock_anthropic_client):
    resp = {"transactions": [
        {"date": "2024-01-01", "amount": 50.0, "description": "SHOP", "category_id": 8},
        {"date": "2024-01-01", "amount": 50.0, "description": "SHOP", "category_id": 8},
    ], "currency": "USD", "confidence": 0.9}
    mock_anthropic_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text=json.dumps(resp))]
    )
    p = LLMParser(client=mock_anthropic_client, model="test")
    result = p.parse("content", None, START, END, CATEGORIES)
    assert result.transaction_count == 1
