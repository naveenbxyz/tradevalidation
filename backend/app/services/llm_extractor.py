import base64
import json
import os
from typing import Optional
from openai import OpenAI
from app.config import settings
from app.models import ExtractedTrade, ExtractedField


FX_EXTRACTION_PROMPT = """You are a trade data extraction expert. Extract the following fields from the trade confirmation document:

For FX/Forex trades, extract:
- trade_id: The unique trade identifier/reference number
- counterparty: The counterparty name (bank/institution)
- currency_pair: The currency pair (e.g., EUR/USD, GBP/USD)
- direction: BUY or SELL (from our perspective)
- notional: The principal/notional amount (numeric only, no currency symbols)
- rate: The exchange rate (numeric)
- trade_date: The trade date (YYYY-MM-DD format)
- value_date: The settlement/value date (YYYY-MM-DD format)

Return ONLY a JSON object in this exact format:
{
  "trade_type": "FX",
  "fields": {
    "trade_id": {"value": "...", "confidence": 0.95},
    "counterparty": {"value": "...", "confidence": 0.9},
    "currency_pair": {"value": "...", "confidence": 0.95},
    "direction": {"value": "BUY or SELL", "confidence": 0.9},
    "notional": {"value": 1000000, "confidence": 0.85},
    "rate": {"value": 1.0850, "confidence": 0.95},
    "trade_date": {"value": "2024-01-15", "confidence": 0.9},
    "value_date": {"value": "2024-01-17", "confidence": 0.9}
  }
}

The confidence score should reflect how certain you are about the extraction (0.0 to 1.0).
If a field cannot be found, use null for the value and 0.0 for confidence.
"""

SWAP_EXTRACTION_PROMPT = """You are a trade data extraction expert. Extract the following fields from the trade confirmation document:

For Interest Rate Swap / Cross Currency Swap trades, extract:
- trade_id: The unique trade identifier/reference number
- counterparty: The counterparty name (bank/institution)
- trade_type: IRS (Interest Rate Swap), CCS (Cross Currency Swap), or BASIS
- notional: The notional principal amount (numeric only)
- currency: The currency (e.g., USD, EUR)
- fixed_rate: The fixed rate as a percentage (e.g., 4.25)
- floating_index: The floating rate index (e.g., SOFR, EURIBOR, LIBOR)
- spread: The spread over the floating index as percentage (e.g., 0.15)
- effective_date: The effective/start date (YYYY-MM-DD format)
- maturity_date: The maturity/end date (YYYY-MM-DD format)
- payment_frequency: Payment frequency (Monthly, Quarterly, Semi-Annual, Annual)

Return ONLY a JSON object in this exact format:
{
  "trade_type": "SWAP",
  "fields": {
    "trade_id": {"value": "...", "confidence": 0.95},
    "counterparty": {"value": "...", "confidence": 0.9},
    "trade_type": {"value": "IRS", "confidence": 0.95},
    "notional": {"value": 10000000, "confidence": 0.9},
    "currency": {"value": "USD", "confidence": 0.95},
    "fixed_rate": {"value": 4.25, "confidence": 0.9},
    "floating_index": {"value": "SOFR", "confidence": 0.85},
    "spread": {"value": 0.15, "confidence": 0.8},
    "effective_date": {"value": "2024-01-20", "confidence": 0.9},
    "maturity_date": {"value": "2029-01-20", "confidence": 0.9},
    "payment_frequency": {"value": "Quarterly", "confidence": 0.85}
  }
}

The confidence score should reflect how certain you are about the extraction (0.0 to 1.0).
If a field cannot be found, use null for the value and 0.0 for confidence.
"""

DETECTION_PROMPT = """Analyze this trade confirmation document and determine if it's an FX (Foreign Exchange) trade or a Swap/Derivatives trade.

FX trades typically mention: currency pairs (EUR/USD), spot/forward, exchange rate, buy/sell currencies
Swap trades typically mention: interest rate swap, cross currency swap, notional, fixed rate, floating rate, SOFR/LIBOR/EURIBOR, effective date, maturity date

Respond with ONLY one word: "FX" or "SWAP"
"""


class LLMExtractor:
    def __init__(self):
        self.client = None
        if settings.openai_api_key:
            self.client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url if settings.openai_base_url else None
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
            ".webp": "image/webp"
        }
        return media_types.get(ext, "image/jpeg")

    async def detect_trade_type(self, content: str, image_path: Optional[str] = None) -> str:
        """Detect whether the document contains FX or Swap trade data."""
        if not self.client:
            # Default to FX if no API key configured
            if any(term in content.lower() for term in ["swap", "irs", "ccs", "fixed rate", "floating", "sofr", "euribor", "maturity"]):
                return "SWAP"
            return "FX"

        messages = [{"role": "user", "content": []}]

        if image_path and os.path.exists(image_path):
            base64_image = self._encode_image(image_path)
            media_type = self._get_image_media_type(image_path)
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{base64_image}"}
            })

        messages[0]["content"].append({
            "type": "text",
            "text": f"{DETECTION_PROMPT}\n\nDocument content:\n{content}"
        })

        try:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                max_tokens=10
            )
            result = response.choices[0].message.content.strip().upper()
            return "SWAP" if "SWAP" in result else "FX"
        except Exception as e:
            print(f"Trade type detection failed: {e}")
            # Fallback to keyword detection
            if any(term in content.lower() for term in ["swap", "irs", "ccs", "fixed rate", "floating", "sofr", "euribor", "maturity"]):
                return "SWAP"
            return "FX"

    async def extract_trade_data(
        self,
        content: str,
        image_path: Optional[str] = None,
        trade_type: Optional[str] = None
    ) -> ExtractedTrade:
        """Extract trade data from document content using LLM."""

        # Detect trade type if not provided
        if not trade_type:
            trade_type = await self.detect_trade_type(content, image_path)

        # If no API key, use mock extraction for demo
        if not self.client:
            return self._mock_extraction(content, trade_type)

        prompt = FX_EXTRACTION_PROMPT if trade_type == "FX" else SWAP_EXTRACTION_PROMPT

        messages = [{"role": "user", "content": []}]

        # Add image if provided
        if image_path and os.path.exists(image_path):
            base64_image = self._encode_image(image_path)
            media_type = self._get_image_media_type(image_path)
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{base64_image}"}
            })

        messages[0]["content"].append({
            "type": "text",
            "text": f"{prompt}\n\nDocument content:\n{content}"
        })

        try:
            response = self.client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            return ExtractedTrade(
                trade_type=result.get("trade_type", trade_type),
                fields={
                    k: ExtractedField(
                        value=v.get("value"),
                        confidence=v.get("confidence", 0.5)
                    )
                    for k, v in result.get("fields", {}).items()
                },
                raw_text=content
            )
        except Exception as e:
            print(f"LLM extraction failed: {e}")
            return self._mock_extraction(content, trade_type)

    def _mock_extraction(self, content: str, trade_type: str) -> ExtractedTrade:
        """Provide mock extraction for demo purposes when no API key is configured."""
        content_lower = content.lower()

        if trade_type == "FX":
            # Simple keyword extraction for demo
            fields = {
                "trade_id": ExtractedField(value=self._extract_pattern(content, ["trade id", "reference", "ref"]) or "FX-DEMO-001", confidence=0.7),
                "counterparty": ExtractedField(value=self._extract_pattern(content, ["counterparty", "client", "party"]) or "Demo Bank", confidence=0.6),
                "currency_pair": ExtractedField(value=self._extract_currency_pair(content) or "EUR/USD", confidence=0.8),
                "direction": ExtractedField(value="BUY" if "buy" in content_lower else "SELL", confidence=0.7),
                "notional": ExtractedField(value=self._extract_number(content, ["notional", "amount", "principal"]) or 1000000, confidence=0.6),
                "rate": ExtractedField(value=self._extract_rate(content) or 1.0850, confidence=0.7),
                "trade_date": ExtractedField(value=self._extract_date(content, ["trade date"]) or "2024-01-15", confidence=0.6),
                "value_date": ExtractedField(value=self._extract_date(content, ["value date", "settlement"]) or "2024-01-17", confidence=0.6),
            }
        else:
            fields = {
                "trade_id": ExtractedField(value=self._extract_pattern(content, ["trade id", "reference"]) or "IRS-DEMO-001", confidence=0.7),
                "counterparty": ExtractedField(value=self._extract_pattern(content, ["counterparty", "client"]) or "Demo Bank", confidence=0.6),
                "trade_type": ExtractedField(value="IRS" if "interest rate" in content_lower else "CCS", confidence=0.7),
                "notional": ExtractedField(value=self._extract_number(content, ["notional", "amount"]) or 10000000, confidence=0.6),
                "currency": ExtractedField(value=self._extract_currency(content) or "USD", confidence=0.7),
                "fixed_rate": ExtractedField(value=self._extract_rate(content) or 4.25, confidence=0.6),
                "floating_index": ExtractedField(value=self._extract_index(content) or "SOFR", confidence=0.7),
                "spread": ExtractedField(value=0.15, confidence=0.5),
                "effective_date": ExtractedField(value=self._extract_date(content, ["effective", "start"]) or "2024-01-20", confidence=0.6),
                "maturity_date": ExtractedField(value=self._extract_date(content, ["maturity", "end"]) or "2029-01-20", confidence=0.6),
                "payment_frequency": ExtractedField(value="Quarterly", confidence=0.5),
            }

        return ExtractedTrade(
            trade_type=trade_type,
            fields=fields,
            raw_text=content
        )

    def _extract_pattern(self, content: str, keywords: list) -> Optional[str]:
        """Simple pattern extraction helper."""
        lines = content.split('\n')
        for line in lines:
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    parts = line.split(':')
                    if len(parts) > 1:
                        return parts[1].strip()
        return None

    def _extract_currency_pair(self, content: str) -> Optional[str]:
        """Extract currency pair."""
        import re
        pattern = r'[A-Z]{3}/[A-Z]{3}'
        match = re.search(pattern, content.upper())
        return match.group() if match else None

    def _extract_currency(self, content: str) -> Optional[str]:
        """Extract single currency."""
        currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD"]
        for curr in currencies:
            if curr in content.upper():
                return curr
        return None

    def _extract_number(self, content: str, keywords: list) -> Optional[float]:
        """Extract numeric value."""
        import re
        lines = content.split('\n')
        for line in lines:
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    numbers = re.findall(r'[\d,]+\.?\d*', line)
                    if numbers:
                        return float(numbers[0].replace(',', ''))
        return None

    def _extract_rate(self, content: str) -> Optional[float]:
        """Extract exchange rate or fixed rate."""
        import re
        patterns = [
            r'rate[:\s]+(\d+\.?\d*)',
            r'(\d+\.\d{4})',  # 4 decimal places typical for FX
            r'(\d+\.\d{2})%?'  # percentage
        ]
        for pattern in patterns:
            match = re.search(pattern, content.lower())
            if match:
                return float(match.group(1))
        return None

    def _extract_date(self, content: str, keywords: list) -> Optional[str]:
        """Extract date in various formats."""
        import re
        lines = content.split('\n')
        for line in lines:
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    # Try YYYY-MM-DD
                    match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                    if match:
                        return match.group(1)
                    # Try DD/MM/YYYY or MM/DD/YYYY
                    match = re.search(r'(\d{2}/\d{2}/\d{4})', line)
                    if match:
                        return match.group(1)
        return None

    def _extract_index(self, content: str) -> Optional[str]:
        """Extract floating rate index."""
        indices = ["SOFR", "EURIBOR", "SONIA", "LIBOR", "TONAR", "ESTR"]
        for idx in indices:
            if idx in content.upper():
                return idx
        return None


# Global extractor instance
extractor = LLMExtractor()
