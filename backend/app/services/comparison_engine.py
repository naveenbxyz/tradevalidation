from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, List, Optional, Union

from app.models import (
    ExtractedTrade,
    FieldComparison,
    MatchingRule,
    TRSTrade,
    ValidationResult,
)
from app.models.schemas import generate_id


class ComparisonEngine:
    """Engine for comparing extracted TRS data with system records."""

    def __init__(self, rules: Optional[List[MatchingRule]] = None):
        self.rules = rules or []

    def set_rules(self, rules: List[MatchingRule]):
        self.rules = rules

    def get_rule(self, field_name: str) -> Optional[MatchingRule]:
        for rule in self.rules:
            if rule.field_name == field_name and rule.enabled:
                return rule
        return None

    def compare_values(
        self,
        field_name: str,
        extracted_value: Any,
        system_value: Any,
        confidence: float = 1.0,
    ) -> FieldComparison:
        rule = self.get_rule(field_name)
        min_confidence = rule.min_confidence if rule else 0.0

        if confidence < min_confidence:
            return FieldComparison(
                field_name=field_name,
                extracted_value=extracted_value,
                system_value=system_value,
                match_status="LOW_CONFIDENCE",
                confidence=confidence,
                min_required_confidence=min_confidence,
                rule_applied=f"min_confidence_{min_confidence}",
            )

        if rule is None:
            match_status = "MATCH" if str(extracted_value).strip().lower() == str(system_value).strip().lower() else "MISMATCH"
            return FieldComparison(
                field_name=field_name,
                extracted_value=extracted_value,
                system_value=system_value,
                match_status=match_status,
                confidence=confidence,
                min_required_confidence=min_confidence,
                rule_applied="default_exact",
            )

        if rule.rule_type == "exact":
            match_status = self._exact_match(extracted_value, system_value)
        elif rule.rule_type == "tolerance":
            match_status = self._tolerance_match(
                extracted_value,
                system_value,
                rule.tolerance_value or 0,
                rule.tolerance_unit or "absolute",
            )
        elif rule.rule_type == "fuzzy":
            match_status = self._fuzzy_match(extracted_value, system_value)
        elif rule.rule_type == "date_tolerance":
            match_status = self._date_tolerance_match(
                extracted_value,
                system_value,
                int(rule.tolerance_value or 0),
            )
        else:
            match_status = "MATCH" if extracted_value == system_value else "MISMATCH"

        return FieldComparison(
            field_name=field_name,
            extracted_value=extracted_value,
            system_value=system_value,
            match_status=match_status,
            confidence=confidence,
            min_required_confidence=min_confidence,
            rule_applied=f"{rule.rule_type}_{rule.tolerance_value or ''}{rule.tolerance_unit or ''}",
        )

    def _exact_match(self, val1: Any, val2: Any) -> str:
        if isinstance(val1, str) and isinstance(val2, str):
            return "MATCH" if val1.strip().lower() == val2.strip().lower() else "MISMATCH"
        return "MATCH" if val1 == val2 else "MISMATCH"

    def _tolerance_match(
        self,
        val1: Union[int, float],
        val2: Union[int, float],
        tolerance: float,
        unit: str,
    ) -> str:
        try:
            v1 = float(val1)
            v2 = float(val2)
        except (TypeError, ValueError):
            return "MISMATCH"

        if unit == "percent":
            if v2 == 0:
                return "MATCH" if v1 == 0 else "MISMATCH"
            diff_percent = abs(v1 - v2) / abs(v2) * 100
            if diff_percent == 0:
                return "MATCH"
            return "WITHIN_TOLERANCE" if diff_percent <= tolerance else "MISMATCH"

        diff = abs(v1 - v2)
        if diff == 0:
            return "MATCH"
        return "WITHIN_TOLERANCE" if diff <= tolerance else "MISMATCH"

    def _fuzzy_match(self, val1: str, val2: str, threshold: float = 0.8) -> str:
        try:
            s1 = str(val1).lower().strip()
            s2 = str(val2).lower().strip()
            if s1 == s2:
                return "MATCH"

            ratio = SequenceMatcher(None, s1, s2).ratio()
            if ratio >= 0.95:
                return "MATCH"
            if ratio >= threshold:
                return "WITHIN_TOLERANCE"
            return "MISMATCH"
        except Exception:
            return "MISMATCH"

    def _date_tolerance_match(self, val1: str, val2: str, tolerance_days: int) -> str:
        d1 = self._parse_date(val1)
        d2 = self._parse_date(val2)

        if not d1 or not d2:
            return "MISMATCH"

        diff_days = abs((d1 - d2).days)
        if diff_days == 0:
            return "MATCH"
        return "WITHIN_TOLERANCE" if diff_days <= tolerance_days else "MISMATCH"

    def _parse_date(self, value: Any) -> Optional[datetime]:
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y", "%m-%d-%Y"]:
            try:
                return datetime.strptime(str(value), fmt)
            except ValueError:
                continue
        return None

    def compare_trs_trade(self, extracted: ExtractedTrade, system_trade: TRSTrade, document_id: str) -> ValidationResult:
        field_comparisons: List[FieldComparison] = []

        trs_fields = [
            "trade_id",
            "party_a",
            "party_b",
            "trade_date",
            "effective_date",
            "scheduled_termination_date",
            "bond_return_payer",
            "bond_return_receiver",
            "local_currency",
            "notional_amount",
            "usd_notional_amount",
            "initial_spot_rate",
            "current_market_price",
            "underlier",
            "isin",
        ]

        for field_name in trs_fields:
            extracted_field = extracted.fields.get(field_name)
            if extracted_field is None:
                continue

            system_value = getattr(system_trade, field_name, None)
            if system_value is None:
                continue

            field_comparisons.append(
                self.compare_values(
                    field_name=field_name,
                    extracted_value=extracted_field.value,
                    system_value=system_value,
                    confidence=extracted_field.confidence,
                )
            )

        status = self._determine_overall_status(field_comparisons)

        return ValidationResult(
            id=generate_id(),
            document_id=document_id,
            system_trade_id=system_trade.trade_id,
            status=status,
            field_comparisons=field_comparisons,
            party_a=system_trade.party_a,
            party_b=system_trade.party_b,
            trade_date=system_trade.trade_date,
            effective_date=system_trade.effective_date,
            scheduled_termination_date=system_trade.scheduled_termination_date,
            local_currency=system_trade.local_currency,
            notional_amount=system_trade.notional_amount,
            machine_confidence=self._average_comparison_confidence(field_comparisons),
        )

    def build_unmatched_result(self, extracted: ExtractedTrade, document_id: str) -> ValidationResult:
        return ValidationResult(
            id=generate_id(),
            document_id=document_id,
            system_trade_id="NOT_FOUND",
            status="MISMATCH",
            field_comparisons=[],
            party_a=self._extract_field_value(extracted, "party_a", as_type=str),
            party_b=self._extract_field_value(extracted, "party_b", as_type=str),
            trade_date=self._extract_field_value(extracted, "trade_date", as_type=str),
            effective_date=self._extract_field_value(extracted, "effective_date", as_type=str),
            scheduled_termination_date=self._extract_field_value(
                extracted,
                "scheduled_termination_date",
                as_type=str,
            ),
            local_currency=self._extract_field_value(extracted, "local_currency", as_type=str),
            notional_amount=self._extract_field_value(extracted, "notional_amount", as_type=float),
            machine_confidence=self._average_extracted_confidence(extracted),
        )

    def _determine_overall_status(self, comparisons: List[FieldComparison]) -> str:
        if not comparisons:
            return "PENDING"

        match_count = sum(1 for c in comparisons if c.match_status == "MATCH")
        tolerance_count = sum(1 for c in comparisons if c.match_status == "WITHIN_TOLERANCE")
        low_conf_count = sum(1 for c in comparisons if c.match_status == "LOW_CONFIDENCE")
        mismatch_count = sum(1 for c in comparisons if c.match_status == "MISMATCH")

        if mismatch_count == 0 and tolerance_count == 0 and low_conf_count == 0:
            return "MATCH"

        if mismatch_count == 0 and (tolerance_count > 0 or low_conf_count > 0):
            return "PARTIAL"

        if match_count + tolerance_count > mismatch_count:
            return "PARTIAL"

        return "MISMATCH"

    def find_best_match(
        self,
        extracted: ExtractedTrade,
        trs_trades: List[TRSTrade],
        document_id: str,
    ) -> Optional[ValidationResult]:
        if not trs_trades:
            return None

        extracted_trade_id = extracted.fields.get("trade_id")
        if extracted_trade_id and extracted_trade_id.value:
            for trade in trs_trades:
                if trade.trade_id.lower() == str(extracted_trade_id.value).strip().lower():
                    return self.compare_trs_trade(extracted, trade, document_id)

        best_result: Optional[ValidationResult] = None
        best_score = -1.0

        for trade in trs_trades:
            result = self.compare_trs_trade(extracted, trade, document_id)
            score = sum(
                1.0
                if c.match_status == "MATCH"
                else 0.6
                if c.match_status == "WITHIN_TOLERANCE"
                else 0.25
                if c.match_status == "LOW_CONFIDENCE"
                else 0.0
                for c in result.field_comparisons
            )

            if score > best_score:
                best_score = score
                best_result = result

        if best_result and not best_result.field_comparisons:
            return None

        return best_result

    def _average_comparison_confidence(self, comparisons: List[FieldComparison]) -> Optional[float]:
        if not comparisons:
            return None
        return round(sum(c.confidence for c in comparisons) / len(comparisons), 4)

    def _average_extracted_confidence(self, extracted: ExtractedTrade) -> Optional[float]:
        if not extracted.fields:
            return None
        confidences = [field.confidence for field in extracted.fields.values()]
        if not confidences:
            return None
        return round(sum(confidences) / len(confidences), 4)

    def _extract_field_value(self, extracted: ExtractedTrade, field_name: str, as_type: type = str) -> Optional[Any]:
        field = extracted.fields.get(field_name)
        if not field or field.value in (None, ""):
            return None

        value = field.value
        if as_type is str:
            return str(value)
        if as_type is float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        return value


comparison_engine = ComparisonEngine()
