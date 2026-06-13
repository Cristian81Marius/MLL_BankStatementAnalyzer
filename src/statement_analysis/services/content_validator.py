import re

# Matches: 1,234.56 / 1.234,56 / 1234.56 / 1234,56 / $ 50.00 / € 9.99
_AMOUNT_RE = re.compile(
    r"(?:[$€£R\$¥]\s?)?\d{1,3}(?:[.,\s]\d{3})*[.,]\d{2}\b"
    r"|\b\d+[.,]\d{2}\b"
)

# Matches: 01/15/2024 · 2024-01-15 · 15.01.2024 · 15 Jan 2024 · Jan 15 2024
_DATE_RE = re.compile(
    r"\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b"
    r"|\b\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}\b"
    r"|\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{2,4}\b"
    r"|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4}\b",
    re.IGNORECASE,
)

MIN_AMOUNTS = 2
MIN_CHARS = 80


def validate_statement_content(content: str) -> tuple[bool, str]:
    """
    Returns (True, "") if content looks like a bank statement,
    or (False, reason) if it clearly does not.
    """
    stripped = content.strip()

    if len(stripped) < MIN_CHARS:
        return False, "File contains too little text to be a bank statement"

    amounts = _AMOUNT_RE.findall(stripped)
    if len(amounts) < MIN_AMOUNTS:
        return False, (
            f"Only {len(amounts)} amount-like value(s) found — "
            "file does not appear to contain transactions"
        )

    if not _DATE_RE.search(stripped):
        return False, "No transaction dates detected in the file"

    return True, ""
