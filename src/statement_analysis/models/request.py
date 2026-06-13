from datetime import date
from typing import Literal

from pydantic import Base64Bytes, BaseModel, field_validator


class CategoryInput(BaseModel):
    id: int
    type: Literal["income", "expense"]
    name: str


class Base64FileRequest(BaseModel):
    pdf_data: Base64Bytes
    file_type: Literal["pdf", "csv"] = "pdf"
    filename: str | None = None
    bank_name: str | None = None
    start_date: date
    end_date: date
    categories: list[CategoryInput]

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: date, info) -> date:
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date must be on or after start_date")
        return v
