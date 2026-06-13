from dataclasses import dataclass, field
from io import BytesIO

import pdfplumber


@dataclass
class ExtractedContent:
    pages_text: list[str]
    tables: list[list[list[str | None]]]
    full_text: str
    has_tables: bool
    page_count: int


class PDFExtractor:
    def extract(self, pdf_bytes: bytes) -> ExtractedContent:
        pages_text: list[str] = []
        all_tables: list[list[list[str | None]]] = []

        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)
                tables = page.extract_tables() or []
                all_tables.extend(tables)

        full_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text)
        return ExtractedContent(
            pages_text=pages_text,
            tables=all_tables,
            full_text=full_text,
            has_tables=bool(all_tables),
            page_count=len(pages_text),
        )

    def format_for_llm(self, content: ExtractedContent) -> str:
        parts: list[str] = []

        if content.has_tables:
            parts.append("=== EXTRACTED TABLES ===")
            for i, table in enumerate(content.tables):
                parts.append(f"\n[Table {i + 1}]")
                for row in table:
                    cleaned = [cell or "" for cell in row]
                    parts.append(" | ".join(cleaned))

        parts.append("\n=== RAW TEXT ===")
        parts.append(content.full_text)
        return "\n".join(parts)
