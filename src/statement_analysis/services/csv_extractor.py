import csv
import io


class CSVExtractor:
    _DELIMITERS = [",", ";", "\t", "|"]

    def extract_and_format(self, csv_bytes: bytes) -> str:
        text = self._decode(csv_bytes)
        delimiter = self._detect_delimiter(text)
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = [row for row in reader if any(cell.strip() for cell in row)]

        if not rows:
            return "=== CSV CONTENT ===\n(empty file)"

        lines = ["=== CSV TABLE ==="]
        for row in rows:
            lines.append(" | ".join(cell.strip() for cell in row))

        return "\n".join(lines)

    def _decode(self, data: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("latin-1", errors="replace")

    def _detect_delimiter(self, text: str) -> str:
        sample = "\n".join(text.splitlines()[:10])
        counts = {d: sample.count(d) for d in self._DELIMITERS}
        return max(counts, key=lambda d: counts[d])
