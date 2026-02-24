"""Initialize the prototype database with TRS sample data and default rules."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import db
from app.models import MatchingRule, TRSTradeCreate


DEFAULT_RULES = [
    MatchingRule(id="trs-trade_id", field_name="trade_id", rule_type="exact", min_confidence=0.7, enabled=True),
    MatchingRule(id="trs-party_a", field_name="party_a", rule_type="fuzzy", min_confidence=0.8, enabled=True),
    MatchingRule(id="trs-party_b", field_name="party_b", rule_type="fuzzy", min_confidence=0.8, enabled=True),
    MatchingRule(id="trs-trade_date", field_name="trade_date", rule_type="date_tolerance", tolerance_value=0, tolerance_unit="days", min_confidence=0.85, enabled=True),
    MatchingRule(id="trs-effective_date", field_name="effective_date", rule_type="date_tolerance", tolerance_value=1, tolerance_unit="days", min_confidence=0.85, enabled=True),
    MatchingRule(id="trs-scheduled_termination_date", field_name="scheduled_termination_date", rule_type="date_tolerance", tolerance_value=1, tolerance_unit="days", min_confidence=0.85, enabled=True),
    MatchingRule(id="trs-bond_return_payer", field_name="bond_return_payer", rule_type="exact", min_confidence=0.9, enabled=True),
    MatchingRule(id="trs-bond_return_receiver", field_name="bond_return_receiver", rule_type="exact", min_confidence=0.9, enabled=True),
    MatchingRule(id="trs-local_currency", field_name="local_currency", rule_type="exact", min_confidence=0.9, enabled=True),
    MatchingRule(id="trs-notional_amount", field_name="notional_amount", rule_type="tolerance", tolerance_value=0.1, tolerance_unit="percent", min_confidence=0.85, enabled=True),
    MatchingRule(id="trs-usd_notional_amount", field_name="usd_notional_amount", rule_type="tolerance", tolerance_value=0.1, tolerance_unit="percent", min_confidence=0.85, enabled=True),
    MatchingRule(id="trs-initial_spot_rate", field_name="initial_spot_rate", rule_type="tolerance", tolerance_value=0.001, tolerance_unit="absolute", min_confidence=0.8, enabled=True),
    MatchingRule(id="trs-current_market_price", field_name="current_market_price", rule_type="tolerance", tolerance_value=0.25, tolerance_unit="absolute", min_confidence=0.8, enabled=True),
    MatchingRule(id="trs-underlier", field_name="underlier", rule_type="fuzzy", min_confidence=0.7, enabled=True),
    MatchingRule(id="trs-isin", field_name="isin", rule_type="exact", min_confidence=0.7, enabled=True),
]


def init_sample_data() -> None:
    sample_file = os.path.join(os.path.dirname(__file__), "..", "data", "sample_trs_trades.json")

    if os.path.exists(sample_file):
        with open(sample_file, "r") as handle:
            payload = json.load(handle)

        existing_trade_ids = {trade.trade_id for trade in db.get_trs_trades()}
        created = 0

        for trade_data in payload.get("trs_trades", []):
            if trade_data["trade_id"] in existing_trade_ids:
                continue

            db.create_trs_trade(TRSTradeCreate(**trade_data))
            created += 1

        print(f"Created {created} TRS trades")
    else:
        print(f"Sample file not found: {sample_file}")

    if not db.get_matching_rules():
        db.save_matching_rules(DEFAULT_RULES)
        print(f"Created {len(DEFAULT_RULES)} default TRS matching rules")

    print("\nInitialization complete")
    print(f"TRS Trades: {len(db.get_trs_trades())}")
    print(f"Matching Rules: {len(db.get_matching_rules())}")
    print(f"Validation Results: {len(db.get_validation_results())}")


if __name__ == "__main__":
    init_sample_data()
