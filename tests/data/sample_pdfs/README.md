# Sample PDFs

Place real bank statement PDFs here for live integration testing. Files are gitignored.

Suggested filenames:
- `bank_tabular.pdf` — statement with debit/credit columns (e.g. Chase, BofA)
- `bank_narrative.pdf` — plain text narrative format
- `bank_multipage.pdf` — multi-page statement
- `bank_portuguese.pdf` — non-English statement (Portuguese/Brazilian banks)
- `bank_scanned.pdf` — scanned image PDF (tests OCR fallback path)

These files are never committed. Add them manually to run:

    pytest tests/integration/ -v -k "live" --live

(Live tests are skipped by default when no PDFs are present.)
