from typing import List, Optional, Union
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from app.models import (
    ExtractedTrade, FXTrade, SwapTrade,
    MatchingRule, ValidationResult, FieldComparison
)
from app.models.schemas import generate_id


class ComparisonEngine:
    """Engine for comparing extracted trade data with system records."""

    def __init__(self, rules: List[MatchingRule] = None):
        self.rules = rules or []

    def set_rules(self, rules: List[MatchingRule]):
        self.rules = rules

    def get_rule(self, field_name: str) -> Optional[MatchingRule]:
        """Get the matching rule for a specific field."""
        for rule in self.rules:
            if rule.field_name == field_name and rule.enabled:
                return rule
        return None

    def compare_values(
        self,
        field_name: str,
        extracted_value: any,
        system_value: any,
        confidence: float = 1.0
    ) -> FieldComparison:
        """Compare two values according to the matching rules."""

        rule = self.get_rule(field_name)

        if rule is None:
            # Default to exact match if no rule found
            match_status = "MATCH" if str(extracted_value).lower() == str(system_value).lower() else "MISMATCH"
            return FieldComparison(
                field_name=field_name,
                extracted_value=extracted_value,
                system_value=system_value,
                match_status=match_status,
                confidence=confidence,
                rule_applied="default_exact"
            )

        if rule.rule_type == "exact":
            match_status = self._exact_match(extracted_value, system_value)
        elif rule.rule_type == "tolerance":
            match_status = self._tolerance_match(
                extracted_value, system_value,
                rule.tolerance_value or 0,
                rule.tolerance_unit or "absolute"
            )
        elif rule.rule_type == "fuzzy":
            match_status = self._fuzzy_match(extracted_value, system_value)
        elif rule.rule_type == "date_tolerance":
            match_status = self._date_tolerance_match(
                extracted_value, system_value,
                int(rule.tolerance_value or 0)
            )
        else:
            match_status = "MATCH" if extracted_value == system_value else "MISMATCH"

        return FieldComparison(
            field_name=field_name,
            extracted_value=extracted_value,
            system_value=system_value,
            match_status=match_status,
            confidence=confidence,
            rule_applied=f"{rule.rule_type}_{rule.tolerance_value or ''}{rule.tolerance_unit or ''}"
        )

    def _exact_match(self, val1: any, val2: any) -> str:
        """Exact string/value match (case-insensitive for strings)."""
        if isinstance(val1, str) and isinstance(val2, str):
            return "MATCH" if val1.lower().strip() == val2.lower().strip() else "MISMATCH"
        return "MATCH" if val1 == val2 else "MISMATCH"

    def _tolerance_match(
        self,
        val1: Union[int, float],
        val2: Union[int, float],
        tolerance: float,
        unit: str
    ) -> str:
        """Numeric match with tolerance."""
        try:
            v1 = float(val1)
            v2 = float(val2)

            if unit == "percent":
                # Tolerance as percentage of system value
                if v2 == 0:
                    return "MATCH" if v1 == 0 else "MISMATCH"
                diff_percent = abs(v1 - v2) / abs(v2) * 100
                if diff_percent == 0:
                    return "MATCH"
                elif diff_percent <= tolerance:
                    return "WITHIN_TOLERANCE"
                else:
                    return "MISMATCH"
            else:
                # Absolute tolerance
                diff = abs(v1 - v2)
                if diff == 0:
                    return "MATCH"
                elif diff <= tolerance:
                    return "WITHIN_TOLERANCE"
                else:
                    return "MISMATCH"
        except (ValueError, TypeError):
            return "MISMATCH"

    def _fuzzy_match(self, val1: str, val2: str, threshold: float = 0.8) -> str:
        """Fuzzy string matching using sequence similarity."""
        try:
            s1 = str(val1).lower().strip()
            s2 = str(val2).lower().strip()

            if s1 == s2:
                return "MATCH"

            ratio = SequenceMatcher(None, s1, s2).ratio()

            if ratio >= 0.95:
                return "MATCH"
            elif ratio >= threshold:
                return "WITHIN_TOLERANCE"
            else:
                return "MISMATCH"
        except Exception:
            return "MISMATCH"

    def _date_tolerance_match(
        self,
        val1: str,
        val2: str,
        tolerance_days: int
    ) -> str:
        """Date match with day tolerance."""
        try:
            # Parse dates in various formats
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]:
                try:
                    d1 = datetime.strptime(str(val1), fmt)
                    break
                except ValueError:
                    continue
            else:
                return "MISMATCH"

            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]:
                try:
                    d2 = datetime.strptime(str(val2), fmt)
                    break
                except ValueError:
                    continue
            else:
                return "MISMATCH"

            diff_days = abs((d1 - d2).days)

            if diff_days == 0:
                return "MATCH"
            elif diff_days <= tolerance_days:
                return "WITHIN_TOLERANCE"
            else:
                return "MISMATCH"
        except Exception:
            return "MISMATCH"

    def compare_fx_trade(
        self,
        extracted: ExtractedTrade,
        system_trade: FXTrade,
        document_id: str
    ) -> ValidationResult:
        """Compare extracted FX trade data with system record."""

        field_comparisons = []

        fx_fields = [
            "trade_id", "counterparty", "currency_pair", "direction",
            "notional", "rate", "trade_date", "value_date"
        ]

        for field_name in fx_fields:
            extracted_field = extracted.fields.get(field_name)
            if extracted_field is None:
                continue

            system_value = getattr(system_trade, field_name, None)
            if system_value is None:
                continue

            comparison = self.compare_values(
                field_name,
                extracted_field.value,
                system_value,
                extracted_field.confidence
            )
            field_comparisons.append(comparison)

        # Determine overall status
        status = self._determine_overall_status(field_comparisons)

        return ValidationResult(
            id=generate_id(),
            document_id=document_id,
            system_trade_id=system_trade.trade_id,
            status=status,
            field_comparisons=field_comparisons
        )

    def compare_swap_trade(
        self,
        extracted: ExtractedTrade,
        system_trade: SwapTrade,
        document_id: str
    ) -> ValidationResult:
        """Compare extracted Swap trade data with system record."""

        field_comparisons = []

        swap_fields = [
            "trade_id", "counterparty", "trade_type", "notional", "currency",
            "fixed_rate", "floating_index", "spread", "effective_date",
            "maturity_date", "payment_frequency"
        ]

        for field_name in swap_fields:
            extracted_field = extracted.fields.get(field_name)
            if extracted_field is None:
                continue

            system_value = getattr(system_trade, field_name, None)
            if system_value is None:
                continue

            comparison = self.compare_values(
                field_name,
                extracted_field.value,
                system_value,
                extracted_field.confidence
            )
            field_comparisons.append(comparison)

        # Determine overall status
        status = self._determine_overall_status(field_comparisons)

        return ValidationResult(
            id=generate_id(),
            document_id=document_id,
            system_trade_id=system_trade.trade_id,
            status=status,
            field_comparisons=field_comparisons
        )

    def _determine_overall_status(self, comparisons: List[FieldComparison]) -> str:
        """Determine the overall validation status from field comparisons."""
        if not comparisons:
            return "PENDING"

        match_count = sum(1 for c in comparisons if c.match_status == "MATCH")
        tolerance_count = sum(1 for c in comparisons if c.match_status == "WITHIN_TOLERANCE")
        mismatch_count = sum(1 for c in comparisons if c.match_status == "MISMATCH")

        if mismatch_count == 0 and tolerance_count == 0:
            return "MATCH"
        elif mismatch_count == 0:
            return "PARTIAL"  # All within tolerance
        elif match_count + tolerance_count > mismatch_count:
            return "PARTIAL"
        else:
            return "MISMATCH"

    def find_best_match(
        self,
        extracted: ExtractedTrade,
        fx_trades: List[FXTrade],
        swap_trades: List[SwapTrade],
        document_id: str
    ) -> Optional[ValidationResult]:
        """Find the best matching system trade for the extracted data."""

        if extracted.trade_type == "FX":
            candidates = fx_trades
            compare_func = self.compare_fx_trade
        else:
            candidates = swap_trades
            compare_func = self.compare_swap_trade

        if not candidates:
            return None

        best_result = None
        best_score = -1

        # Try to match by trade_id first
        extracted_trade_id = extracted.fields.get("trade_id")
        if extracted_trade_id and extracted_trade_id.value:
            for trade in candidates:
                if trade.trade_id.lower() == str(extracted_trade_id.value).lower():
                    return compare_func(extracted, trade, document_id)

        # If no exact trade_id match, find best overall match
        for trade in candidates:
            result = compare_func(extracted, trade, document_id)

            # Calculate score based on matches
            score = sum(
                1 if c.match_status == "MATCH" else 0.5 if c.match_status == "WITHIN_TOLERANCE" else 0
                for c in result.field_comparisons
            )

            if score > best_score:
                best_score = score
                best_result = result

        return best_result


# Global comparison engine instance
comparison_engine = ComparisonEngine()
