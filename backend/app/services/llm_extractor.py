import base64
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.config import settings
from app.models import ExtractedField, ExtractedTrade


class LLMExtractor:
    def __init__(self):
        self.client = None
        if settings.openai_api_key:
            self.client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url if settings.openai_base_url else None,
            )
        self.schema = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        configured_path = Path(settings.trs_schema_path)

        candidates = [configured_path]
        if not configured_path.is_absolute():
            backend_dir = Path(__file__).resolve().parents[2]
            candidates.append(backend_dir / configured_path)
            candidates.append(backend_dir / "app" / "schema_configs" / configured_path.name)

        for candidate in candidates:
            if candidate.exists():
                with open(candidate, "r") as schema_file:
                    return json.load(schema_file)

        raise FileNotFoundError(
            f"TRS schema file not found. Checked: {', '.join(str(p) for p in candidates)}"
        )

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _get_image_media_type(self, image_path: str) -> str:
        ext = os.path.splitext(image_path)[1].lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        return media_types.get(ext, "image/jpeg")

    async def detect_trade_type(self, content: str, image_path: Optional[str] = None) -> str:
        _ = content
        _ = image_path
        # Current scope is TRS only.
        return "TRS"

    async def extract_trade_data(
        self,
        content: str,
        image_path: Optional[str] = None,
        trade_type: Optional[str] = None,
    ) -> ExtractedTrade:
        _ = trade_type

        if not self.client:
            return self._mock_extraction(content)

        prompt = self._build_extraction_prompt()
        messages = [{"role": "user", "content": []}]

        if image_path and os.path.exists(image_path):
            base64_image = self._encode_image(image_path)
            media_type = self._get_image_media_type(image_path)
            messages[0]["content"].append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{base64_image}"},
                }
            )

        messages[0]["content"].append(
            {
                "type": "text",
                "text": f"{prompt}\n\nEvidence content:\n{content}",
            }
        )

        try:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                max_tokens=1800,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content
            parsed = json.loads(result_text)
            normalized_fields = self._normalize_fields(parsed.get("fields", {}))

            return ExtractedTrade(
                trade_type="TRS",
                schema_version=str(parsed.get("schema_version") or self.schema.get("version", "v1")),
                fields=normalized_fields,
                raw_text=content,
            )
        except Exception as exc:
            print(f"LLM extraction failed: {exc}")
            return self._mock_extraction(content)

    def _build_extraction_prompt(self) -> str:
        field_lines: List[str] = []
        for field in self.schema.get("fields", []):
            allowed_values = field.get("allowed_values")
            allowed = f" Allowed values: {allowed_values}." if allowed_values else ""
            required = "required" if field.get("required") else "optional"
            field_lines.append(
                f"- {field['name']} ({field.get('type', 'string')}, {required}).{allowed}"
            )

        return (
            "You are a trade confirmation extraction engine for Total Return Swap (TRS) trades.\n"
            "Extract only fields from the provided schema.\n"
            "Use YYYY-MM-DD for dates.\n"
            "Use numeric values for numeric fields with no separators or currency signs.\n"
            "Use PartyA/PartyB exactly for payer/receiver fields.\n"
            "If a field is missing, set value to null and confidence to 0.0.\n"
            "Infer provenance source_type as one of email_body, attachment, ocr, unknown.\n"
            "Return only valid JSON in this shape:\n"
            "{\n"
            "  \"trade_type\": \"TRS\",\n"
            f"  \"schema_version\": \"{self.schema.get('version', 'v1')}\",\n"
            "  \"fields\": {\n"
            "    \"field_name\": {\n"
            "      \"value\": <value or null>,\n"
            "      \"confidence\": <0.0-1.0>,\n"
            "      \"provenance\": {\n"
            "        \"source_type\": \"email_body|attachment|ocr|unknown\",\n"
            "        \"source_name\": \"optional attachment name\",\n"
            "        \"page\": <page number or null>\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "}\n\n"
            "Schema fields:\n"
            + "\n".join(field_lines)
        )

    def _normalize_fields(self, fields: Dict[str, Any]) -> Dict[str, ExtractedField]:
        normalized: Dict[str, ExtractedField] = {}
        for field in self.schema.get("fields", []):
            field_name = field["name"]
            value_block = fields.get(field_name, {}) or {}
            normalized[field_name] = ExtractedField(
                value=value_block.get("value"),
                confidence=float(value_block.get("confidence", 0.0) or 0.0),
                provenance=value_block.get("provenance"),
            )
        return normalized

    def _mock_extraction(self, content: str) -> ExtractedTrade:
        field_map = {
            "trade_id": self._extract_pattern(content, [r"trade\s*id", r"trade\s*ref", r"reference"]),
            "party_a": self._extract_pattern(content, [r"party\s*a", r"our\s*bank", r"return\s*swap\s*receiver\s*party\s*a"]),
            "party_b": self._extract_pattern(content, [r"party\s*b", r"counterparty"]),
            "trade_date": self._extract_date_for_label(content, [r"trade\s*date"]),
            "effective_date": self._extract_date_for_label(content, [r"effective\s*date", r"start\s*date"]),
            "scheduled_termination_date": self._extract_date_for_label(content, [r"scheduled\s*termination\s*date", r"termination\s*date", r"maturity\s*date"]),
            "bond_return_payer": self._normalize_party_flag(self._extract_pattern(content, [r"bond\s*return\s*payer"])),
            "bond_return_receiver": self._normalize_party_flag(self._extract_pattern(content, [r"bond\s*return\s*receiver"])),
            "local_currency": self._extract_currency(content, [r"local\s*currency", r"currency"]),
            "notional_amount": self._extract_number_for_label(content, [r"notional\s*amount", r"local\s*notional"]),
            "usd_notional_amount": self._extract_number_for_label(content, [r"usd\s*notional\s*amount", r"usd\s*notional"]),
            "initial_spot_rate": self._extract_number_for_label(content, [r"initial\s*spot\s*rate", r"spot\s*rate"]),
            "current_market_price": self._extract_number_for_label(content, [r"current\s*market\s*price", r"market\s*price"]),
            "underlier": self._extract_pattern(content, [r"underlier", r"reference\s*bond", r"reference\s*asset"]),
            "isin": self._extract_pattern(content, [r"isin"]),
        }

        output: Dict[str, ExtractedField] = {}
        for field in self.schema.get("fields", []):
            name = field["name"]
            value = field_map.get(name)

            output[name] = ExtractedField(
                value=value,
                confidence=0.75 if value not in (None, "") else 0.0,
                provenance={"source_type": "unknown", "source_name": None, "page": None},
            )

        return ExtractedTrade(
            trade_type="TRS",
            schema_version=str(self.schema.get("version", "v1")),
            fields=output,
            raw_text=content,
        )

    def _extract_pattern(self, content: str, labels: List[str]) -> Optional[str]:
        lines = content.split("\n")
        for line in lines:
            for label in labels:
                pattern = rf"\b{label}\b\s*[:\-]\s*(.+)$"
                match = re.search(pattern, line, flags=re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        return None

    def _extract_number_for_label(self, content: str, labels: List[str]) -> Optional[float]:
        lines = content.split("\n")
        for line in lines:
            for label in labels:
                if re.search(rf"\b{label}\b", line, flags=re.IGNORECASE):
                    number_match = re.search(r"([-+]?\d[\d,]*\.?\d*)", line)
                    if number_match:
                        try:
                            return float(number_match.group(1).replace(",", ""))
                        except ValueError:
                            return None
        return None

    def _extract_currency(self, content: str, labels: List[str]) -> Optional[str]:
        maybe_value = self._extract_pattern(content, labels)
        if maybe_value:
            match = re.search(r"\b([A-Z]{3})\b", maybe_value.upper())
            if match:
                return match.group(1)

        match = re.search(r"\b(USD|EUR|GBP|JPY|CHF|AUD|CAD|INR|SGD|HKD)\b", content.upper())
        if match:
            return match.group(1)
        return None

    def _extract_date_for_label(self, content: str, labels: List[str]) -> Optional[str]:
        lines = content.split("\n")

        for line in lines:
            for label in labels:
                if re.search(rf"\b{label}\b", line, flags=re.IGNORECASE):
                    parsed = self._parse_date(line)
                    if parsed:
                        return parsed

        parsed_any = self._parse_date(content)
        return parsed_any

    def _parse_date(self, text: str) -> Optional[str]:
        patterns = [
            r"(\d{4}-\d{2}-\d{2})",
            r"(\d{2}/\d{2}/\d{4})",
            r"(\d{2}-\d{2}-\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if not match:
                continue

            raw = match.group(1)
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y"):
                try:
                    return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue

        return None

    def _normalize_party_flag(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None

        text = value.strip().lower().replace(" ", "")
        if text in {"partya", "a", "ourbank", "bank", "party_a"}:
            return "PartyA"
        if text in {"partyb", "b", "counterparty", "party_b"}:
            return "PartyB"

        if "party a" in value.lower():
            return "PartyA"
        if "party b" in value.lower():
            return "PartyB"

        return None


extractor = LLMExtractor()
