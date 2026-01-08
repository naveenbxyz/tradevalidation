"""Script to initialize the database with sample data."""
import json
import os
import sys
import random
from datetime import datetime, timedelta

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import db
from app.models import FXTradeCreate, SwapTradeCreate, MatchingRule, ValidationResult, FieldComparison
from app.models.schemas import generate_id


def generate_trade_id():
    """Generate 11-digit trade ID starting with 40."""
    return f"40{random.randint(100000000, 999999999)}"


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

    # 1. MATCHED - Goldman Sachs FX Spot (USD)
    matched_fx_spot = ValidationResult(
        id=generate_id(),
        document_id=generate_id(),
        system_trade_id="40847291056",
        status="MATCH",
        counterparty="Goldman Sachs",
        product="FX Spot",
        notional=5000000,
        currency="USD",
        trade_date="2025-01-06",
        confidence=0.96,
        created_at=(now - timedelta(hours=1)).isoformat(),
        field_comparisons=[
            FieldComparison(field_name="counterparty", extracted_value="Goldman Sachs & Co", system_value="Goldman Sachs", match_status="WITHIN_TOLERANCE", confidence=0.92, rule_applied="fuzzy"),
            FieldComparison(field_name="currency_pair", extracted_value="EUR/USD", system_value="EUR/USD", match_status="MATCH", confidence=0.99, rule_applied="exact"),
            FieldComparison(field_name="direction", extracted_value="BUY", system_value="BUY", match_status="MATCH", confidence=0.98, rule_applied="exact"),
            FieldComparison(field_name="notional", extracted_value=5000000, system_value=5000000, match_status="MATCH", confidence=0.97, rule_applied="tolerance_0.01percent"),
            FieldComparison(field_name="rate", extracted_value=1.0842, system_value=1.0842, match_status="MATCH", confidence=0.99, rule_applied="tolerance_0.0001absolute"),
            FieldComparison(field_name="trade_date", extracted_value="2025-01-06", system_value="2025-01-06", match_status="MATCH", confidence=0.95, rule_applied="date_tolerance_0days"),
            FieldComparison(field_name="value_date", extracted_value="2025-01-08", system_value="2025-01-08", match_status="MATCH", confidence=0.94, rule_applied="date_tolerance_1days"),
        ]
    )
    db.create_validation_result(matched_fx_spot)
    print("Created validation: Matched FX Spot (Goldman Sachs)")

    # 2. MATCHED - HDFC Bank IRS (INR)
    matched_irs = ValidationResult(
        id=generate_id(),
        document_id=generate_id(),
        system_trade_id="40529183746",
        status="MATCH",
        counterparty="HDFC Bank",
        product="IRS",
        notional=500000000,
        currency="INR",
        trade_date="2025-01-03",
        effective_date="2025-01-10",
        maturity_date="2030-01-10",
        confidence=0.94,
        created_at=(now - timedelta(hours=3)).isoformat(),
        field_comparisons=[
            FieldComparison(field_name="counterparty", extracted_value="HDFC Bank", system_value="HDFC Bank", match_status="MATCH", confidence=0.98, rule_applied="fuzzy"),
            FieldComparison(field_name="trade_type", extracted_value="IRS", system_value="IRS", match_status="MATCH", confidence=0.99, rule_applied="exact"),
            FieldComparison(field_name="notional", extracted_value=500000000, system_value=500000000, match_status="MATCH", confidence=0.96, rule_applied="tolerance_0.01percent"),
            FieldComparison(field_name="currency", extracted_value="INR", system_value="INR", match_status="MATCH", confidence=0.99, rule_applied="exact"),
            FieldComparison(field_name="fixed_rate", extracted_value=7.25, system_value=7.25, match_status="MATCH", confidence=0.97, rule_applied="tolerance_0.01absolute"),
            FieldComparison(field_name="floating_index", extracted_value="MIBOR", system_value="MIBOR", match_status="MATCH", confidence=0.98, rule_applied="exact"),
            FieldComparison(field_name="effective_date", extracted_value="2025-01-10", system_value="2025-01-10", match_status="MATCH", confidence=0.93, rule_applied="date_tolerance_0days"),
            FieldComparison(field_name="maturity_date", extracted_value="2030-01-10", system_value="2030-01-10", match_status="MATCH", confidence=0.92, rule_applied="date_tolerance_0days"),
        ]
    )
    db.create_validation_result(matched_irs)
    print("Created validation: Matched IRS (HDFC Bank)")

    # 3. PARTIAL MATCH - JP Morgan FX NDF with rate discrepancy (USD)
    partial_ndf = ValidationResult(
        id=generate_id(),
        document_id=generate_id(),
        system_trade_id="40738291054",
        status="PARTIAL",
        counterparty="JP Morgan",
        product="FX NDF",
        notional=10000000,
        currency="USD",
        trade_date="2025-01-02",
        maturity_date="2025-04-02",
        confidence=0.79,
        created_at=(now - timedelta(hours=6)).isoformat(),
        field_comparisons=[
            FieldComparison(field_name="counterparty", extracted_value="JP Morgan Chase", system_value="JP Morgan", match_status="WITHIN_TOLERANCE", confidence=0.88, rule_applied="fuzzy"),
            FieldComparison(field_name="currency_pair", extracted_value="USD/INR", system_value="USD/INR", match_status="MATCH", confidence=0.99, rule_applied="exact"),
            FieldComparison(field_name="notional", extracted_value=10000000, system_value=10000000, match_status="MATCH", confidence=0.95, rule_applied="tolerance_0.01percent"),
            FieldComparison(field_name="rate", extracted_value=84.15, system_value=84.05, match_status="MISMATCH", confidence=0.72, rule_applied="tolerance_0.0001absolute"),
            FieldComparison(field_name="trade_date", extracted_value="2025-01-02", system_value="2025-01-02", match_status="MATCH", confidence=0.94, rule_applied="date_tolerance_0days"),
            FieldComparison(field_name="maturity_date", extracted_value="2025-04-02", system_value="2025-04-02", match_status="MATCH", confidence=0.91, rule_applied="date_tolerance_0days"),
        ]
    )
    db.create_validation_result(partial_ndf)
    print("Created validation: Partial Match FX NDF (JP Morgan)")

    # 4. MATCHED - State Bank of India FX Swap (INR)
    matched_fx_swap = ValidationResult(
        id=generate_id(),
        document_id=generate_id(),
        system_trade_id="40193847562",
        status="MATCH",
        counterparty="State Bank of India",
        product="FX Swap",
        notional=250000000,
        currency="INR",
        trade_date="2025-01-03",
        effective_date="2025-01-07",
        maturity_date="2025-07-07",
        confidence=0.95,
        created_at=(now - timedelta(hours=12)).isoformat(),
        field_comparisons=[
            FieldComparison(field_name="counterparty", extracted_value="State Bank of India", system_value="State Bank of India", match_status="MATCH", confidence=0.99, rule_applied="fuzzy"),
            FieldComparison(field_name="currency_pair", extracted_value="USD/INR", system_value="USD/INR", match_status="MATCH", confidence=0.98, rule_applied="exact"),
            FieldComparison(field_name="notional", extracted_value=250000000, system_value=250000000, match_status="MATCH", confidence=0.96, rule_applied="tolerance_0.01percent"),
            FieldComparison(field_name="near_leg_rate", extracted_value=83.50, system_value=83.50, match_status="MATCH", confidence=0.97, rule_applied="tolerance_0.0001absolute"),
            FieldComparison(field_name="far_leg_rate", extracted_value=84.20, system_value=84.20, match_status="MATCH", confidence=0.95, rule_applied="tolerance_0.0001absolute"),
            FieldComparison(field_name="trade_date", extracted_value="2025-01-03", system_value="2025-01-03", match_status="MATCH", confidence=0.94, rule_applied="date_tolerance_0days"),
            FieldComparison(field_name="effective_date", extracted_value="2025-01-07", system_value="2025-01-07", match_status="MATCH", confidence=0.93, rule_applied="date_tolerance_0days"),
            FieldComparison(field_name="maturity_date", extracted_value="2025-07-07", system_value="2025-07-07", match_status="MATCH", confidence=0.92, rule_applied="date_tolerance_0days"),
        ]
    )
    db.create_validation_result(matched_fx_swap)
    print("Created validation: Matched FX Swap (SBI)")

    # 5. NOT MATCHED - Deutsche Bank CCS (no matching trade found) (EUR)
    not_matched = ValidationResult(
        id=generate_id(),
        document_id=generate_id(),
        system_trade_id="NOT_FOUND",
        status="MISMATCH",
        counterparty="Deutsche Bank",
        product="CCS",
        notional=15000000,
        currency="EUR",
        trade_date="2025-01-04",
        effective_date="2025-01-15",
        maturity_date="2028-01-15",
        confidence=0.68,
        created_at=(now - timedelta(days=1)).isoformat(),
        field_comparisons=[]
    )
    db.create_validation_result(not_matched)
    print("Created validation: Not Matched CCS (Deutsche Bank)")

    # 6. PARTIAL MATCH - Citibank IRS with date discrepancy (USD)
    partial_irs = ValidationResult(
        id=generate_id(),
        document_id=generate_id(),
        system_trade_id="40629481735",
        status="PARTIAL",
        counterparty="Citibank",
        product="IRS",
        notional=25000000,
        currency="USD",
        trade_date="2024-12-30",
        effective_date="2025-01-06",
        maturity_date="2027-01-06",
        confidence=0.81,
        created_at=(now - timedelta(days=1, hours=5)).isoformat(),
        field_comparisons=[
            FieldComparison(field_name="counterparty", extracted_value="Citibank N.A.", system_value="Citibank", match_status="WITHIN_TOLERANCE", confidence=0.89, rule_applied="fuzzy"),
            FieldComparison(field_name="trade_type", extracted_value="IRS", system_value="IRS", match_status="MATCH", confidence=0.98, rule_applied="exact"),
            FieldComparison(field_name="notional", extracted_value=25000000, system_value=25000000, match_status="MATCH", confidence=0.95, rule_applied="tolerance_0.01percent"),
            FieldComparison(field_name="currency", extracted_value="USD", system_value="USD", match_status="MATCH", confidence=0.99, rule_applied="exact"),
            FieldComparison(field_name="fixed_rate", extracted_value=4.35, system_value=4.35, match_status="MATCH", confidence=0.96, rule_applied="tolerance_0.01absolute"),
            FieldComparison(field_name="floating_index", extracted_value="SOFR", system_value="SOFR", match_status="MATCH", confidence=0.98, rule_applied="exact"),
            FieldComparison(field_name="effective_date", extracted_value="2025-01-07", system_value="2025-01-06", match_status="WITHIN_TOLERANCE", confidence=0.78, rule_applied="date_tolerance_1days"),
            FieldComparison(field_name="maturity_date", extracted_value="2027-01-06", system_value="2027-01-06", match_status="MATCH", confidence=0.92, rule_applied="date_tolerance_0days"),
        ]
    )
    db.create_validation_result(partial_irs)
    print("Created validation: Partial Match IRS (Citibank)")

    # 7. MATCHED - Barclays Commodity (USD)
    matched_commodity = ValidationResult(
        id=generate_id(),
        document_id=generate_id(),
        system_trade_id="40582947163",
        status="MATCH",
        counterparty="Barclays",
        product="Commodity",
        notional=8000000,
        currency="USD",
        trade_date="2025-01-02",
        maturity_date="2025-03-31",
        confidence=0.93,
        created_at=(now - timedelta(days=2)).isoformat(),
        field_comparisons=[
            FieldComparison(field_name="counterparty", extracted_value="Barclays Bank PLC", system_value="Barclays", match_status="WITHIN_TOLERANCE", confidence=0.91, rule_applied="fuzzy"),
            FieldComparison(field_name="commodity", extracted_value="Crude Oil", system_value="Crude Oil", match_status="MATCH", confidence=0.99, rule_applied="exact"),
            FieldComparison(field_name="notional", extracted_value=8000000, system_value=8000000, match_status="MATCH", confidence=0.95, rule_applied="tolerance_0.01percent"),
            FieldComparison(field_name="price", extracted_value=72.50, system_value=72.50, match_status="MATCH", confidence=0.96, rule_applied="tolerance_0.01absolute"),
            FieldComparison(field_name="trade_date", extracted_value="2025-01-02", system_value="2025-01-02", match_status="MATCH", confidence=0.94, rule_applied="date_tolerance_0days"),
            FieldComparison(field_name="maturity_date", extracted_value="2025-03-31", system_value="2025-03-31", match_status="MATCH", confidence=0.91, rule_applied="date_tolerance_0days"),
        ]
    )
    db.create_validation_result(matched_commodity)
    print("Created validation: Matched Commodity (Barclays)")

    # 8. MATCHED - ICICI Bank FX Spot (INR)
    matched_fx_spot_2 = ValidationResult(
        id=generate_id(),
        document_id=generate_id(),
        system_trade_id="40918273645",
        status="MATCH",
        counterparty="ICICI Bank",
        product="FX Spot",
        notional=75000000,
        currency="INR",
        trade_date="2025-01-06",
        confidence=0.97,
        created_at=(now - timedelta(hours=2)).isoformat(),
        field_comparisons=[
            FieldComparison(field_name="counterparty", extracted_value="ICICI Bank Ltd", system_value="ICICI Bank", match_status="WITHIN_TOLERANCE", confidence=0.93, rule_applied="fuzzy"),
            FieldComparison(field_name="currency_pair", extracted_value="USD/INR", system_value="USD/INR", match_status="MATCH", confidence=0.98, rule_applied="exact"),
            FieldComparison(field_name="direction", extracted_value="SELL", system_value="SELL", match_status="MATCH", confidence=0.97, rule_applied="exact"),
            FieldComparison(field_name="notional", extracted_value=75000000, system_value=75000000, match_status="MATCH", confidence=0.96, rule_applied="tolerance_0.01percent"),
            FieldComparison(field_name="rate", extracted_value=83.42, system_value=83.42, match_status="MATCH", confidence=0.98, rule_applied="tolerance_0.0001absolute"),
            FieldComparison(field_name="trade_date", extracted_value="2025-01-06", system_value="2025-01-06", match_status="MATCH", confidence=0.95, rule_applied="date_tolerance_0days"),
            FieldComparison(field_name="value_date", extracted_value="2025-01-08", system_value="2025-01-08", match_status="MATCH", confidence=0.94, rule_applied="date_tolerance_1days"),
        ]
    )
    db.create_validation_result(matched_fx_spot_2)
    print("Created validation: Matched FX Spot (ICICI Bank)")


if __name__ == "__main__":
    init_sample_data()
