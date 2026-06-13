import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation

import anthropic

from ..models.request import CategoryInput
from ..models.response import StatementAnalysisResponse, Transaction

SYSTEM_PROMPT = (
    "You are an expert financial data extraction system specializing in bank statements. "
    "You extract transaction data from bank statements regardless of format, language, or structure. "
    "You always output valid JSON. You never fabricate transactions — only extract what is clearly present."
)

EXTRACTION_PROMPT = """\
Analyze this bank statement from {bank_name}.

Extract ONLY transactions that occurred between {start_date} and {end_date} (inclusive). Skip all others.

Assign each transaction to the most appropriate category from this list (use the exact numeric ID):
{categories_list}

RULES:
1. Extract ONLY transactions dated between {start_date} and {end_date}. Skip any outside this range.
2. Amount must ALWAYS be a positive number (absolute value).
3. Dates → ISO YYYY-MM-DD. If year is ambiguous use the most recent plausible year.
4. For category_id, use ONLY the IDs from the list above. Pick the most fitting one.
5. Statement may be in any language — keep original description text as-is in "description".
6. Do not skip transactions out of uncertainty — make your best inference.
7. clean_description: a short human-readable label for the transaction (e.g. "Netflix Subscription",
   "Amazon Purchase", "Salary Deposit"). Max 30 characters. No codes, no reference numbers.

OUTPUT — strict JSON, no markdown fences:
{{
  "transactions": [
    {{
      "date": "YYYY-MM-DD",
      "amount": 123.45,
      "description": "Original raw text from statement",
      "clean_description": "Human readable label",
      "category_id": 8
    }}
  ],
  "currency": "USD/EUR/GBP/BRL/etc — detect from symbols or text, default USD",
  "confidence": 0.95
}}

STATEMENT CONTENT:
{content}"""


class LLMParser:
    def __init__(
        self,
        client: anthropic.Anthropic,
        model: str = "claude-haiku-4-5-20251001",
        max_tokens: int = 4096,
        max_content_chars: int = 12000,
    ) -> None:
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.max_content_chars = max_content_chars

    def parse(
        self,
        formatted_content: str,
        bank_name: str | None,
        start_date: date,
        end_date: date,
        categories: list[CategoryInput],
    ) -> StatementAnalysisResponse:
        categories_map: dict[int, CategoryInput] = {c.id: c for c in categories}
        categories_list = "\n".join(
            f"  - ID {c.id}: [{c.type}] {c.name}" for c in categories
        )

        chunks = self._chunk_content(formatted_content)
        all_transactions: list[dict] = []
        confidence_scores: list[float] = []
        currency: str = "USD"
        warnings: list[str] = []
        seen: set[tuple] = set()

        for i, chunk in enumerate(chunks):
            try:
                result = self._call_claude(
                    chunk,
                    bank_name=bank_name or "the bank",
                    start_date=start_date,
                    end_date=end_date,
                    categories_list=categories_list,
                )
            except (json.JSONDecodeError, anthropic.APIError) as exc:
                warnings.append(f"Chunk {i + 1} failed: {exc}")
                continue

            for tx in result.get("transactions", []):
                key = (tx.get("date"), str(tx.get("amount")), tx.get("description", "")[:80])
                if key not in seen:
                    seen.add(key)
                    all_transactions.append(tx)

            if result.get("currency"):
                currency = result["currency"]
            confidence_scores.append(float(result.get("confidence", 0.8)))

        expenses: list[Transaction] = []
        income: list[Transaction] = []

        for tx_dict in all_transactions:
            tx = self._to_transaction(tx_dict, categories_map, start_date, end_date, warnings)
            if tx is None:
                continue
            if tx.type == "expense":
                expenses.append(tx)
            else:
                income.append(tx)

        total_expenses = sum((t.amount for t in expenses), Decimal("0"))
        total_income = sum((t.amount for t in income), Decimal("0"))
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        statement_period = f"{start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}"

        return StatementAnalysisResponse(
            expenses=expenses,
            income=income,
            total_expenses=total_expenses,
            total_income=total_income,
            currency=currency,
            bank_name=bank_name,
            statement_period=statement_period,
            transaction_count=len(expenses) + len(income),
            parsing_confidence=round(avg_confidence, 4),
            warnings=warnings,
        )

    def _call_claude(
        self,
        content_chunk: str,
        bank_name: str,
        start_date: date,
        end_date: date,
        categories_list: str,
    ) -> dict:
        prompt = EXTRACTION_PROMPT.format(
            bank_name=bank_name,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            categories_list=categories_list,
            content=content_chunk,
        )
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
        return json.loads(raw.strip())

    def _chunk_content(self, content: str) -> list[str]:
        if len(content) <= self.max_content_chars:
            return [content]

        pages = content.split("--- PAGE BREAK ---")
        chunks: list[str] = []
        current = ""

        for page in pages:
            if len(page) > self.max_content_chars:
                if current.strip():
                    chunks.append(current.strip())
                    current = ""
                for i in range(0, len(page), self.max_content_chars):
                    chunks.append(page[i : i + self.max_content_chars])
            elif len(current) + len(page) > self.max_content_chars:
                if current.strip():
                    chunks.append(current.strip())
                current = page
            else:
                current += "\n" + page

        if current.strip():
            chunks.append(current.strip())

        return chunks or [content[: self.max_content_chars]]

    def _to_transaction(
        self,
        tx_dict: dict,
        categories_map: dict[int, CategoryInput],
        start_date: date,
        end_date: date,
        warnings: list[str],
    ) -> Transaction | None:
        try:
            parsed_date = date.fromisoformat(tx_dict.get("date", ""))

            # Server-side date filter as a safety net (LLM already filters, but verify)
            if not (start_date <= parsed_date <= end_date):
                return None

            raw_amount = tx_dict.get("amount", 0)
            amount = abs(Decimal(str(raw_amount)))
            if amount == 0:
                return None

            description = str(tx_dict.get("description", "")).strip() or "Unknown"
            clean_description = str(tx_dict.get("clean_description", "")).strip()
            if not clean_description:
                clean_description = description[:30]
            clean_description = clean_description[:30]

            category_id = int(tx_dict.get("category_id", -1))
            cat = categories_map.get(category_id)
            if cat is None:
                warnings.append(
                    f"Unknown category_id {category_id} for '{description}' — skipped"
                )
                return None

            return Transaction(
                amount=amount,
                description=description,
                clean_description=clean_description,
                category_id=cat.id,
                category_name=cat.name,
                date=parsed_date,
                type=cat.type,
            )
        except (ValueError, InvalidOperation, KeyError) as exc:
            warnings.append(f"Skipped malformed transaction: {exc} — {tx_dict}")
            return None
