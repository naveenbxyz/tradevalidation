"""Script to initialize the database with sample data."""
import json
import os
import sys
from datetime import datetime, timedelta

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import db
from app.models import FXTradeCreate, SwapTradeCreate, MatchingRule, ValidationResult, FieldComparison
from app.models.schemas import generate_id


def init_sample_data():
    """Initialize the database with sample trades and matching rules."""

    # Load sample trades
    sample_file = os.path.join(os.path.dirname(__file__), "..", "data", "sample_trades.json")

    if os.path.exists(sample_file):
        with open(sample_file, 'r') as f:
            data = json.load(f)

        # Create FX trades
        for trade_data in data.get("fx_trades", []):
            existing = db.get_fx_trade(trade_data["trade_id"])
            if not existing:
                trade = FXTradeCreate(**trade_data)
                db.create_fx_trade(trade)
                print(f"Created FX trade: {trade_data['trade_id']}")

        # Create Swap trades
        for trade_data in data.get("swap_trades", []):
            existing = db.get_swap_trade(trade_data["trade_id"])
            if not existing:
                trade = SwapTradeCreate(**trade_data)
                db.create_swap_trade(trade)
                print(f"Created Swap trade: {trade_data['trade_id']}")

    # Initialize default matching rules
    existing_rules = db.get_matching_rules()
    if not existing_rules:
        default_rules = [
            # FX Rules
            MatchingRule(id="fx-trade_id", field_name="trade_id", rule_type="exact", enabled=True),
            MatchingRule(id="fx-counterparty", field_name="counterparty", rule_type="fuzzy", enabled=True),
            MatchingRule(id="fx-currency_pair", field_name="currency_pair", rule_type="exact", enabled=True),
            MatchingRule(id="fx-direction", field_name="direction", rule_type="exact", enabled=True),
            MatchingRule(id="fx-notional", field_name="notional", rule_type="tolerance", tolerance_value=0.01, tolerance_unit="percent", enabled=True),
            MatchingRule(id="fx-rate", field_name="rate", rule_type="tolerance", tolerance_value=0.0001, tolerance_unit="absolute", enabled=True),
            MatchingRule(id="fx-trade_date", field_name="trade_date", rule_type="date_tolerance", tolerance_value=0, tolerance_unit="days", enabled=True),
            MatchingRule(id="fx-value_date", field_name="value_date", rule_type="date_tolerance", tolerance_value=1, tolerance_unit="days", enabled=True),

            # Swap Rules
            MatchingRule(id="swap-trade_type", field_name="trade_type", rule_type="exact", enabled=True),
            MatchingRule(id="swap-currency", field_name="currency", rule_type="exact", enabled=True),
            MatchingRule(id="swap-fixed_rate", field_name="fixed_rate", rule_type="tolerance", tolerance_value=0.01, tolerance_unit="absolute", enabled=True),
            MatchingRule(id="swap-floating_index", field_name="floating_index", rule_type="exact", enabled=True),
            MatchingRule(id="swap-spread", field_name="spread", rule_type="tolerance", tolerance_value=0.01, tolerance_unit="absolute", enabled=True),
            MatchingRule(id="swap-effective_date", field_name="effective_date", rule_type="date_tolerance", tolerance_value=0, tolerance_unit="days", enabled=True),
            MatchingRule(id="swap-maturity_date", field_name="maturity_date", rule_type="date_tolerance", tolerance_value=0, tolerance_unit="days", enabled=True),
            MatchingRule(id="swap-payment_frequency", field_name="payment_frequency", rule_type="exact", enabled=True),
        ]

        db.save_matching_rules(default_rules)
        print(f"Created {len(default_rules)} default matching rules")

    # Initialize sample validation results for demo
    existing_validations = db.get_validation_results()
    if not existing_validations:
        init_sample_validations()

    print("\nSample data initialization complete!")
    print(f"FX Trades: {len(db.get_fx_trades())}")
    print(f"Swap Trades: {len(db.get_swap_trades())}")
    print(f"Matching Rules: {len(db.get_matching_rules())}")
    print(f"Validation Results: {len(db.get_validation_results())}")


def init_sample_validations():
    """Create sample validation results for dashboard demo."""

    now = datetime.now()

    # 1. MATCHED - Goldman Sachs FX trade confirmation (perfect match)
    matched_fx = ValidationResult(
        id=generate_id(),
        document_id=generate_id(),
        system_trade_id="FX-2024-001",
        status="MATCH",
        document_name="GS_FX_Confirmation_Jan15.pdf",
        counterparty="Goldman Sachs",
        trade_type="FX",
        notional=1000000,
        currency="EUR",
        confidence=0.95,
        created_at=(now - timedelta(hours=2)).isoformat(),
        field_comparisons=[
            FieldComparison(field_name="counterparty", extracted_value="Goldman Sachs", system_value="Goldman Sachs", match_status="MATCH", confidence=0.98, rule_applied="fuzzy"),
            FieldComparison(field_name="currency_pair", extracted_value="EUR/USD", system_value="EUR/USD", match_status="MATCH", confidence=0.99, rule_applied="exact"),
            FieldComparison(field_name="direction", extracted_value="BUY", system_value="BUY", match_status="MATCH", confidence=0.95, rule_applied="exact"),
            FieldComparison(field_name="notional", extracted_value=1000000, system_value=1000000, match_status="MATCH", confidence=0.92, rule_applied="tolerance_0.01percent"),
            FieldComparison(field_name="rate", extracted_value=1.0850, system_value=1.0850, match_status="MATCH", confidence=0.97, rule_applied="tolerance_0.0001absolute"),
            FieldComparison(field_name="trade_date", extracted_value="2024-01-15", system_value="2024-01-15", match_status="MATCH", confidence=0.94, rule_applied="date_tolerance_0days"),
            FieldComparison(field_name="value_date", extracted_value="2024-01-17", system_value="2024-01-17", match_status="MATCH", confidence=0.93, rule_applied="date_tolerance_1days"),
        ]
    )
    db.create_validation_result(matched_fx)
    print("Created validation: Matched FX (Goldman Sachs)")

    # 2. PARTIAL MATCH - Citibank Swap with rate discrepancy
    partial_swap = ValidationResult(
        id=generate_id(),
        document_id=generate_id(),
        system_trade_id="IRS-2024-001",
        status="PARTIAL",
        document_name="Citi_IRS_Confirmation.pdf",
        counterparty="Citibank",
        trade_type="IRS",
        notional=10000000,
        currency="USD",
        confidence=0.78,
        created_at=(now - timedelta(hours=5)).isoformat(),
        field_comparisons=[
            FieldComparison(field_name="counterparty", extracted_value="Citibank N.A.", system_value="Citibank", match_status="WITHIN_TOLERANCE", confidence=0.85, rule_applied="fuzzy"),
            FieldComparison(field_name="trade_type", extracted_value="IRS", system_value="IRS", match_status="MATCH", confidence=0.98, rule_applied="exact"),
            FieldComparison(field_name="notional", extracted_value=10000000, system_value=10000000, match_status="MATCH", confidence=0.95, rule_applied="tolerance_0.01percent"),
            FieldComparison(field_name="currency", extracted_value="USD", system_value="USD", match_status="MATCH", confidence=0.99, rule_applied="exact"),
            FieldComparison(field_name="fixed_rate", extracted_value=4.30, system_value=4.25, match_status="MISMATCH", confidence=0.88, rule_applied="tolerance_0.01absolute"),
            FieldComparison(field_name="floating_index", extracted_value="SOFR", system_value="SOFR", match_status="MATCH", confidence=0.97, rule_applied="exact"),
            FieldComparison(field_name="effective_date", extracted_value="2024-01-20", system_value="2024-01-20", match_status="MATCH", confidence=0.92, rule_applied="date_tolerance_0days"),
            FieldComparison(field_name="maturity_date", extracted_value="2029-01-20", system_value="2029-01-20", match_status="MATCH", confidence=0.90, rule_applied="date_tolerance_0days"),
        ]
    )
    db.create_validation_result(partial_swap)
    print("Created validation: Partial Match Swap (Citibank)")

    # 3. NOT MATCHED - Unknown counterparty, no matching trade found
    not_matched = ValidationResult(
        id=generate_id(),
        document_id=generate_id(),
        system_trade_id="NOT_FOUND",
        status="MISMATCH",
        document_name="HSBC_FX_Email_Jan18.msg",
        counterparty="HSBC London",
        trade_type="FX",
        notional=750000,
        currency="GBP",
        confidence=0.72,
        created_at=(now - timedelta(hours=8)).isoformat(),
        field_comparisons=[]  # No comparisons since no match found
    )
    db.create_validation_result(not_matched)
    print("Created validation: Not Matched (HSBC)")

    # 4. MATCHED - JP Morgan FX trade
    matched_jpm = ValidationResult(
        id=generate_id(),
        document_id=generate_id(),
        system_trade_id="FX-2024-002",
        status="MATCH",
        document_name="JPM_GBP_Confirmation.pdf",
        counterparty="JP Morgan",
        trade_type="FX",
        notional=500000,
        currency="GBP",
        confidence=0.93,
        created_at=(now - timedelta(days=1)).isoformat(),
        field_comparisons=[
            FieldComparison(field_name="counterparty", extracted_value="JP Morgan", system_value="JP Morgan", match_status="MATCH", confidence=0.96, rule_applied="fuzzy"),
            FieldComparison(field_name="currency_pair", extracted_value="GBP/USD", system_value="GBP/USD", match_status="MATCH", confidence=0.98, rule_applied="exact"),
            FieldComparison(field_name="direction", extracted_value="SELL", system_value="SELL", match_status="MATCH", confidence=0.94, rule_applied="exact"),
            FieldComparison(field_name="notional", extracted_value=500000, system_value=500000, match_status="MATCH", confidence=0.91, rule_applied="tolerance_0.01percent"),
            FieldComparison(field_name="rate", extracted_value=1.2650, system_value=1.2650, match_status="MATCH", confidence=0.95, rule_applied="tolerance_0.0001absolute"),
            FieldComparison(field_name="trade_date", extracted_value="2024-01-16", system_value="2024-01-16", match_status="MATCH", confidence=0.93, rule_applied="date_tolerance_0days"),
            FieldComparison(field_name="value_date", extracted_value="2024-01-18", system_value="2024-01-18", match_status="MATCH", confidence=0.92, rule_applied="date_tolerance_1days"),
        ]
    )
    db.create_validation_result(matched_jpm)
    print("Created validation: Matched FX (JP Morgan)")

    # 5. PARTIAL MATCH - Deutsche Bank CCS with date within tolerance
    partial_db = ValidationResult(
        id=generate_id(),
        document_id=generate_id(),
        system_trade_id="CCS-2024-001",
        status="PARTIAL",
        document_name="DB_CCS_Trade_Confirm.pdf",
        counterparty="Deutsche Bank",
        trade_type="CCS",
        notional=5000000,
        currency="EUR",
        confidence=0.82,
        created_at=(now - timedelta(days=1, hours=3)).isoformat(),
        field_comparisons=[
            FieldComparison(field_name="counterparty", extracted_value="Deutsche Bank AG", system_value="Deutsche Bank", match_status="WITHIN_TOLERANCE", confidence=0.88, rule_applied="fuzzy"),
            FieldComparison(field_name="trade_type", extracted_value="CCS", system_value="CCS", match_status="MATCH", confidence=0.97, rule_applied="exact"),
            FieldComparison(field_name="notional", extracted_value=5000000, system_value=5000000, match_status="MATCH", confidence=0.94, rule_applied="tolerance_0.01percent"),
            FieldComparison(field_name="currency", extracted_value="EUR", system_value="EUR", match_status="MATCH", confidence=0.99, rule_applied="exact"),
            FieldComparison(field_name="fixed_rate", extracted_value=3.50, system_value=3.50, match_status="MATCH", confidence=0.93, rule_applied="tolerance_0.01absolute"),
            FieldComparison(field_name="floating_index", extracted_value="EURIBOR", system_value="EURIBOR", match_status="MATCH", confidence=0.96, rule_applied="exact"),
            FieldComparison(field_name="effective_date", extracted_value="2024-02-02", system_value="2024-02-01", match_status="WITHIN_TOLERANCE", confidence=0.75, rule_applied="date_tolerance_1days"),
            FieldComparison(field_name="payment_frequency", extracted_value="Semi-Annual", system_value="Semi-Annual", match_status="MATCH", confidence=0.91, rule_applied="exact"),
        ]
    )
    db.create_validation_result(partial_db)
    print("Created validation: Partial Match CCS (Deutsche Bank)")

    # 6. NOT MATCHED - BNP Paribas with significant discrepancies
    not_matched_bnp = ValidationResult(
        id=generate_id(),
        document_id=generate_id(),
        system_trade_id="NOT_FOUND",
        status="MISMATCH",
        document_name="BNP_Swap_Bloomberg_Chat.png",
        counterparty="BNP Paribas",
        trade_type="IRS",
        notional=25000000,
        currency="EUR",
        confidence=0.65,
        created_at=(now - timedelta(days=2)).isoformat(),
        field_comparisons=[]
    )
    db.create_validation_result(not_matched_bnp)
    print("Created validation: Not Matched (BNP Paribas)")


if __name__ == "__main__":
    init_sample_data()
