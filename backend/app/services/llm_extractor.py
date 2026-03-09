import base64
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from openai import OpenAI

from app.config import settings
from app.models import ExtractedField, ExtractedTrade

logger = logging.getLogger(__name__)


class LLMExtractor:
    def __init__(self):
        self.client = None
        if settings.openai_api_key:
            http_client = httpx.Client(
                verify=settings.verify_ssl,
                timeout=settings.llm_timeout,
            )
            self.client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url if settings.openai_base_url else None,
                http_client=http_client,
            )
            logger.info(
                "LLM client initialized: base_url=%s model=%s verify_ssl=%s timeout=%ds stream=%s send_images=%s",
                settings.openai_base_url or "(default)",
                settings.llm_model,
                settings.verify_ssl,
                settings.llm_timeout,
                settings.stream,
                settings.llm_send_images,
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

    def _estimate_token_count(self, text: str) -> int:
        """Rough token estimate: ~4 chars per token for English text."""
        return len(text) // 4

    def _estimate_image_tokens(self, image_path: str) -> int:
        """Rough token estimate for an image based on file size.

        OpenAI-compatible APIs typically budget ~85 tokens for low-detail
        and up to ~765+ tokens for high-detail images (based on tile count).
        We use file-size as a proxy since we don't control the detail param.
        """
        try:
            size_bytes = os.path.getsize(image_path)
            # Conservative: ~1 token per 100 bytes for base64-encoded images
            return max(85, size_bytes // 100)
        except OSError:
            return 85

    def _split_into_chunks(self, content: str, max_chars: int, overlap: int = 500) -> List[str]:
        """Split content into chunks that fit within max_chars, with overlap for context."""
        if len(content) <= max_chars:
            return [content]

        chunks: List[str] = []
        start = 0
        while start < len(content):
            end = start + max_chars

            # Try to break at a paragraph or line boundary to avoid splitting mid-sentence
            if end < len(content):
                # Look for the last paragraph break within the chunk
                last_para = content.rfind("\n\n", start + max_chars // 2, end)
                if last_para > start:
                    end = last_para
                else:
                    # Fall back to line break
                    last_line = content.rfind("\n", start + max_chars // 2, end)
                    if last_line > start:
                        end = last_line

            chunks.append(content[start:end].strip())

            # Next chunk starts with overlap for context continuity
            start = end - overlap if end < len(content) else end

        return chunks

    def _build_image_content_blocks(
        self,
        image_paths: Optional[List[str]],
        image_path: Optional[str],
    ) -> tuple:
        """Encode images and return (content_blocks, images_attached, total_bytes, total_tokens_est)."""
        images_to_send = image_paths or ([image_path] if image_path else [])
        content_blocks: List[Dict[str, Any]] = []
        images_attached = 0
        total_image_bytes = 0
        total_image_tokens_est = 0

        for img_path in images_to_send:
            if img_path and os.path.exists(img_path):
                file_size = os.path.getsize(img_path)
                base64_image = self._encode_image(img_path)
                media_type = self._get_image_media_type(img_path)
                content_blocks.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{base64_image}"},
                    }
                )
                img_tokens = self._estimate_image_tokens(img_path)
                total_image_bytes += file_size
                total_image_tokens_est += img_tokens
                images_attached += 1
                logger.info(
                    "  Image %d: %s | size=%d bytes | b64_len=%d | ~%d tokens",
                    images_attached,
                    os.path.basename(img_path),
                    file_size,
                    len(base64_image),
                    img_tokens,
                )

        return content_blocks, images_attached, total_image_bytes, total_image_tokens_est

    @staticmethod
    def _is_response_format_error(exc: Exception) -> bool:
        """Detect if the LLM rejected the response_format parameter."""
        text = str(exc).lower()
        return "response_format" in text and any(
            kw in text for kw in (
                "unsupported", "invalid", "not supported", "unknown",
                "extra inputs are not permitted", "unexpected keyword",
            )
        )

    def _build_request_body(
        self,
        system_prompt: str,
        user_content: Any,
        include_response_format: bool = True,
    ) -> Dict[str, Any]:
        """Build the request body matching the SSI extraction pattern."""
        body: Dict[str, Any] = {
            "model": settings.llm_model,
            "temperature": settings.llm_temperature,
            "max_tokens": 4096,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        if include_response_format:
            body["response_format"] = {"type": "json_object"}
        if settings.stream:
            body["stream"] = True
        return body

    @staticmethod
    def _safe_get(obj: Any, attr: str, default: Any = None) -> Any:
        """Safely get an attribute from an object or dict."""
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    def _collect_stream_text(self, stream: Any) -> str:
        """Collect text from a streaming response, matching the SSI extraction pattern.

        Handles both string and list content formats from different LLM providers.
        """
        parts: List[str] = []
        events = 0

        for chunk in stream:
            events += 1
            choices = self._safe_get(chunk, "choices", []) or []
            if not choices:
                continue

            delta = self._safe_get(choices[0], "delta")
            if not delta:
                continue

            content = self._safe_get(delta, "content")

            # Handle string content (most common)
            if isinstance(content, str) and content:
                parts.append(content)
            # Handle list content (some LLM providers return this)
            elif isinstance(content, list):
                for item in content:
                    text_part = self._safe_get(item, "text") if isinstance(item, (dict,)) else None
                    if isinstance(text_part, str):
                        parts.append(text_part)
                    elif isinstance(item, str):
                        parts.append(item)

        text = "".join(parts)
        logger.info("  Stream collected: %d events, %d chars", events, len(text))
        return text

    def _send_request(self, body: Dict[str, Any], fallback_label: str = "") -> str:
        """Send request with streaming/non-streaming support."""
        is_stream = body.pop("stream", False)

        if is_stream:
            result = self.client.chat.completions.create(**body, stream=True)
            text = self._collect_stream_text(result)
            logger.info("  %sStreaming response: %d chars", fallback_label, len(text))
            if text:
                logger.debug("  %sRaw response (first 500): %s", fallback_label, text[:500])
            else:
                logger.warning("  %sStreaming returned EMPTY response", fallback_label)
            return text

        response = self.client.chat.completions.create(**body)
        text = response.choices[0].message.content or ""
        if hasattr(response, "usage") and response.usage:
            logger.info(
                "  %sLLM usage — prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                fallback_label,
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                response.usage.total_tokens,
            )
        logger.info("  %sResponse: %d chars", fallback_label, len(text))
        if text:
            logger.debug("  %sRaw response (first 500): %s", fallback_label, text[:500])
        return text

    def _call_llm(self, system_prompt: str, user_content: Any) -> str:
        """Send an LLM request with automatic response_format fallback."""
        body = self._build_request_body(system_prompt, user_content, include_response_format=True)

        try:
            return self._send_request(body)
        except Exception as exc:
            if self._is_response_format_error(exc):
                logger.warning(
                    "LLM rejected response_format; retrying without it: %s", exc
                )
                fallback_body = self._build_request_body(
                    system_prompt, user_content, include_response_format=False
                )
                return self._send_request(fallback_body, fallback_label="[fallback] ")
            raise

    def _merge_extracted_fields(
        self,
        all_fields: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Merge fields from multiple chunk extractions — highest confidence wins per field."""
        merged: Dict[str, Any] = {}
        for fields in all_fields:
            for field_name, field_data in fields.items():
                if not isinstance(field_data, dict):
                    continue
                value = field_data.get("value")
                confidence = float(field_data.get("confidence", 0.0) or 0.0)

                # Skip null/empty values
                if value is None or (isinstance(value, str) and not value.strip()):
                    continue

                existing = merged.get(field_name)
                if not existing or confidence > float(existing.get("confidence", 0.0) or 0.0):
                    merged[field_name] = field_data

        return merged

    async def extract_trade_data(
        self,
        content: str,
        image_path: Optional[str] = None,
        image_paths: Optional[List[str]] = None,
        trade_type: Optional[str] = None,
    ) -> ExtractedTrade:
        _ = trade_type

        if not self.client:
            logger.info("No LLM client configured — using mock extraction")
            return self._mock_extraction(content)

        system_prompt = self._build_extraction_prompt()
        max_chars = settings.max_content_chars
        original_content_len = len(content)

        # Only build image blocks if the LLM supports multipart image input
        images_attached = 0
        total_image_bytes = 0
        total_image_tokens_est = 0
        image_blocks: List[Dict[str, Any]] = []

        if settings.llm_send_images:
            image_blocks, images_attached, total_image_bytes, total_image_tokens_est = (
                self._build_image_content_blocks(image_paths, image_path)
            )
        else:
            img_count = len(image_paths or ([image_path] if image_path else []))
            if img_count:
                logger.info(
                    "  Skipping %d image(s) — LLM_SEND_IMAGES=false (text-only mode)", img_count
                )

        # Split content into chunks if needed
        chunks = self._split_into_chunks(content, max_chars)
        num_chunks = len(chunks)

        logger.info("=" * 60)
        logger.info("LLM EXTRACTION REQUEST SUMMARY")
        logger.info("-" * 60)
        logger.info("  Model:            %s", settings.llm_model)
        logger.info("  Base URL:         %s", settings.openai_base_url or "(default)")
        logger.info("  Temperature:      %s", settings.llm_temperature)
        logger.info("  Stream:           %s", settings.stream)
        logger.info("  Timeout:          %ds", settings.llm_timeout)
        logger.info("  Send images:      %s", settings.llm_send_images)
        logger.info("  Max tokens (out): %d", 4096)
        logger.info("-" * 60)
        logger.info("  System prompt:    %d chars", len(system_prompt))
        logger.info("  Content length:   %d chars", original_content_len)
        logger.info("  Max chunk size:   %d chars", max_chars)
        logger.info("  Chunks:           %d", num_chunks)
        for i, chunk in enumerate(chunks):
            logger.info("    Chunk %d/%d: %d chars (~%d tokens)", i + 1, num_chunks, len(chunk), self._estimate_token_count(chunk))
        if settings.llm_send_images:
            logger.info("  Images attached:  %d", images_attached)
            logger.info("  Image bytes:      %d total", total_image_bytes)
            logger.info("  Image tokens est: ~%d", total_image_tokens_est)
        logger.info("=" * 60)

        try:
            all_chunk_fields: List[Dict[str, Any]] = []
            last_parsed: Dict[str, Any] = {}

            for chunk_idx, chunk_content in enumerate(chunks):
                chunk_label = f"Chunk {chunk_idx + 1}/{num_chunks}"
                logger.info("%s: sending %d chars to LLM...", chunk_label, len(chunk_content))

                # Build user content
                chunk_note = ""
                if num_chunks > 1:
                    chunk_note = (
                        f"\n\nNOTE: This is chunk {chunk_idx + 1} of {num_chunks} from a large document. "
                        "Extract all trade fields you can find in this chunk. "
                        "Fields not present in this chunk should have value null and confidence 0.0."
                    )

                user_text = f"Evidence content:{chunk_note}\n{chunk_content}"

                # Use multipart content only if we have images for this chunk
                if chunk_idx == 0 and image_blocks:
                    # Multipart: images + text
                    user_content: Any = list(image_blocks) + [{"type": "text", "text": user_text}]
                else:
                    # Plain text — matches the SSI extraction pattern
                    user_content = user_text

                result_text = self._call_llm(system_prompt, user_content)

                # Strip markdown code fences if present (some LLMs wrap JSON in ```json...```)
                cleaned = result_text.strip()
                if cleaned.startswith("```"):
                    # Remove opening fence (```json or ```)
                    first_newline = cleaned.index("\n") if "\n" in cleaned else 3
                    cleaned = cleaned[first_newline + 1:]
                    # Remove closing fence
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3].strip()
                    result_text = cleaned

                if not result_text.strip():
                    logger.error("%s: LLM returned empty response — skipping chunk", chunk_label)
                    all_chunk_fields.append({})
                    continue

                try:
                    last_parsed = json.loads(result_text)
                except json.JSONDecodeError as jde:
                    logger.error("%s: JSON decode failed: %s", chunk_label, jde)
                    logger.error("  Raw response (first 1000 chars): %s", result_text[:1000])
                    logger.error("  Raw response (last 200 chars):   %s", result_text[-200:])
                    all_chunk_fields.append({})
                    continue

                chunk_fields = last_parsed.get("fields", {})
                non_null = sum(
                    1 for f in chunk_fields.values()
                    if isinstance(f, dict) and f.get("value") is not None
                )
                logger.info("%s: extracted %d fields (%d non-null)", chunk_label, len(chunk_fields), non_null)
                all_chunk_fields.append(chunk_fields)

            # Merge results across chunks — highest confidence wins
            if num_chunks == 1:
                merged_fields = all_chunk_fields[0]
            else:
                merged_fields = self._merge_extracted_fields(all_chunk_fields)
                logger.info(
                    "Merged %d chunks → %d fields with values",
                    num_chunks,
                    sum(1 for f in merged_fields.values() if isinstance(f, dict) and f.get("value") is not None),
                )

            normalized_fields = self._normalize_fields(merged_fields)

            return ExtractedTrade(
                trade_type="TRS",
                schema_version=str(last_parsed.get("schema_version") or self.schema.get("version", "v1")),
                fields=normalized_fields,
                raw_text=content,
            )
        except Exception as exc:
            logger.error("=" * 60)
            logger.error("LLM EXTRACTION FAILED")
            logger.error("  Error type:  %s", type(exc).__name__)
            logger.error("  Error:       %s", exc)
            if hasattr(exc, "response"):
                try:
                    err_body = exc.response.text if hasattr(exc.response, "text") else str(exc.response)
                    logger.error("  Response:    %s", err_body[:2000])
                except Exception:
                    pass
            if hasattr(exc, "status_code"):
                logger.error("  Status code: %s", exc.status_code)
            logger.error("  Falling back to mock extraction")
            logger.error("=" * 60)
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
            "You are a trade confirmation extraction engine for Total Return Swap (TRS) trades.\n\n"
            "You are given evidence that may include:\n"
            "- Email body text\n"
            "- Attached document content (DOCX termsheets, PDFs)\n"
            "- Images of trade confirmations or termsheets (provided as attached images)\n"
            "- OCR text extracted from images\n\n"
            "Carefully analyze ALL provided content — text, documents, and images — to extract "
            "trade details. Use your understanding of TRS trades to identify relevant entities "
            "even if the field names in the evidence don't exactly match the schema.\n\n"
            "The following schema fields are expected. Extract these fields where present, "
            "but also extract any additional TRS-relevant fields you identify in the evidence "
            "(e.g., spread, financing rate, reset frequency, day count, payment dates, "
            "reference obligation details, etc.). Include additional fields under the same "
            "JSON structure with descriptive snake_case names.\n\n"
            "Formatting rules:\n"
            "- Use YYYY-MM-DD for dates.\n"
            "- Use numeric values for numeric fields with no separators or currency signs.\n"
            "- Use PartyA/PartyB exactly for payer/receiver fields.\n"
            "- If a field is missing, set value to null and confidence to 0.0.\n"
            "- Set confidence based on how clearly the value appears in the evidence "
            "(1.0 = explicitly stated, 0.7-0.9 = inferred with high certainty, "
            "<0.7 = uncertain or partially visible).\n"
            "- Infer provenance source_type as one of: email_body, attachment, ocr, unknown.\n\n"
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
            "Expected schema fields:\n"
            + "\n".join(field_lines)
        )

    def _normalize_fields(self, fields: Dict[str, Any]) -> Dict[str, ExtractedField]:
        normalized: Dict[str, ExtractedField] = {}
        schema_field_names = {f["name"] for f in self.schema.get("fields", [])}

        # First, populate all expected schema fields
        for field in self.schema.get("fields", []):
            field_name = field["name"]
            value_block = fields.get(field_name, {}) or {}
            normalized[field_name] = ExtractedField(
                value=value_block.get("value"),
                confidence=float(value_block.get("confidence", 0.0) or 0.0),
                provenance=value_block.get("provenance"),
            )

        # Then, include any additional fields the LLM discovered
        for field_name, value_block in fields.items():
            if field_name not in schema_field_names:
                value_block = value_block or {}
                if isinstance(value_block, dict):
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
