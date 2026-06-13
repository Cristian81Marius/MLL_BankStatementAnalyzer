from functools import lru_cache

import anthropic
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from ..core.config import get_settings
from ..services.csv_extractor import CSVExtractor
from ..services.pdf_extractor import PDFExtractor
from ..services.llm_parser import LLMParser

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(key: str | None = Security(_api_key_header)) -> None:
    if not key or key != get_settings().api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@lru_cache
def get_anthropic_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=get_settings().anthropic_api_key)


def get_pdf_extractor() -> PDFExtractor:
    return PDFExtractor()


def get_csv_extractor() -> CSVExtractor:
    return CSVExtractor()


def get_llm_parser() -> LLMParser:
    settings = get_settings()
    return LLMParser(
        client=get_anthropic_client(),
        model=settings.claude_model,
        max_tokens=settings.llm_max_tokens,
        max_content_chars=settings.llm_max_content_chars,
    )
