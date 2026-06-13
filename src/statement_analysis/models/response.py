from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Always positive, regardless of type")
    description: str = Field(..., min_length=1)
    category_id: int
    category_name: str
    date: date
    type: Literal["expense", "income"]


class StatementAnalysisResponse(BaseModel):
    expenses: list[Transaction] = Field(default_factory=list)
    income: list[Transaction] = Field(default_factory=list)
    total_expenses: Decimal = Decimal("0")
    total_income: Decimal = Decimal("0")
    currency: str = "USD"
    bank_name: str | None = None
    statement_period: str | None = None
    transaction_count: int = 0
    parsing_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
