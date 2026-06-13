import json
from datetime import date
from typing import Literal

import anthropic
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..core.config import get_settings
from ..models.request import Base64FileRequest, CategoryInput
from ..models.response import StatementAnalysisResponse
from ..services.content_validator import validate_statement_content
from ..services.csv_extractor import CSVExtractor
from ..services.llm_parser import LLMParser
from ..services.pdf_extractor import PDFExtractor
from .dependencies import get_csv_extractor, get_llm_parser, get_pdf_extractor, verify_api_key

router = APIRouter()

_PDF_TYPES = {"application/pdf"}
_CSV_TYPES = {"text/csv", "application/csv"}
_AMBIGUOUS_TYPES = {"application/octet-stream", "binary/octet-stream", "text/plain"}
_ALL_ALLOWED = _PDF_TYPES | _CSV_TYPES | _AMBIGUOUS_TYPES

PDF_MAGIC = b"%PDF"


def _detect_file_type(
    content_type: str,
    filename: str | None,
    data: bytes,
) -> Literal["pdf", "csv"]:
    if content_type in _PDF_TYPES:
        return "pdf"
    if content_type in _CSV_TYPES:
        return "csv"
    # Ambiguous MIME — try filename extension, then magic bytes
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return "csv"
    if name.endswith(".pdf"):
        return "pdf"
    return "pdf" if data.startswith(PDF_MAGIC) else "csv"


def _validate_file(data: bytes, file_type: Literal["pdf", "csv"]) -> None:
    settings = get_settings()
    if len(data) < 4:
        raise HTTPException(status_code=400, detail="File appears empty or corrupt")
    if len(data) > settings.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB size limit")
    if file_type == "pdf" and not data.startswith(PDF_MAGIC):
        raise HTTPException(status_code=400, detail="File is not a valid PDF (missing %PDF header)")


def _parse_categories(raw: str) -> list[CategoryInput]:
    try:
        return [CategoryInput.model_validate(item) for item in json.loads(raw)]
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid categories JSON: {exc}")


def _run_analysis(
    file_bytes: bytes,
    file_type: Literal["pdf", "csv"],
    pdf_extractor: PDFExtractor,
    csv_extractor: CSVExtractor,
    parser: LLMParser,
    bank_name: str | None,
    start_date: date,
    end_date: date,
    categories: list[CategoryInput],
) -> StatementAnalysisResponse:
    if not categories:
        raise HTTPException(status_code=422, detail="At least one category is required")
    if end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    try:
        if file_type == "csv":
            formatted = csv_extractor.extract_and_format(file_bytes)
        else:
            extracted = pdf_extractor.extract(file_bytes)
            formatted = pdf_extractor.format_for_llm(extracted)

        valid, reason = validate_statement_content(formatted)
        if not valid:
            raise HTTPException(status_code=422, detail=f"Invalid statement: {reason}")

        return parser.parse(formatted, bank_name, start_date, end_date, categories)
    except HTTPException:
        raise
    except anthropic.APIError as exc:
        raise HTTPException(status_code=502, detail=f"LLM API error: {exc}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"LLM returned malformed JSON: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")


@router.post("/analyze", response_model=StatementAnalysisResponse, dependencies=[Depends(verify_api_key)])
async def analyze_file_upload(
    file: UploadFile = File(...),
    bank_name: str | None = Form(None),
    start_date: date = Form(...),
    end_date: date = Form(...),
    categories: str = Form(..., description='JSON array e.g. [{"id":1,"type":"income","name":"Salary"}]'),
    pdf_extractor: PDFExtractor = Depends(get_pdf_extractor),
    csv_extractor: CSVExtractor = Depends(get_csv_extractor),
    parser: LLMParser = Depends(get_llm_parser),
) -> StatementAnalysisResponse:
    if file.content_type not in _ALL_ALLOWED:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type '{file.content_type}'. Accepted: PDF, CSV.",
        )
    data = await file.read()
    file_type = _detect_file_type(file.content_type, file.filename, data)
    _validate_file(data, file_type)
    parsed_categories = _parse_categories(categories)
    return _run_analysis(
        data, file_type, pdf_extractor, csv_extractor,
        parser, bank_name, start_date, end_date, parsed_categories,
    )


@router.post("/analyze/base64", response_model=StatementAnalysisResponse, dependencies=[Depends(verify_api_key)])
async def analyze_file_base64(
    request: Base64FileRequest,
    pdf_extractor: PDFExtractor = Depends(get_pdf_extractor),
    csv_extractor: CSVExtractor = Depends(get_csv_extractor),
    parser: LLMParser = Depends(get_llm_parser),
) -> StatementAnalysisResponse:
    data = bytes(request.pdf_data)
    _validate_file(data, request.file_type)
    return _run_analysis(
        data, request.file_type, pdf_extractor, csv_extractor,
        parser, request.bank_name, request.start_date, request.end_date, request.categories,
    )


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {"status": "healthy", "model": settings.claude_model}
