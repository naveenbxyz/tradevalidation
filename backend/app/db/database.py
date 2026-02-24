import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models import (
    Document,
    MatchingRule,
    TRSTrade,
    TRSTradeCreate,
    ValidationResult,
)
from app.models.schemas import generate_id
from app.config import settings


DB_DEFAULTS: Dict[str, Any] = {
    "trs_trades": [],
    "documents": [],
    "matching_rules": [],
    "validation_results": [],
}


def to_dict(obj: Any) -> Dict[str, Any]:
    """Convert Pydantic model to dict, compatible with both v1 and v2."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    raise ValueError(f"Cannot convert {type(obj)} to dict")


class JSONDatabase:
    """Simple JSON file-based database for the prototype."""

    def __init__(self, db_path: str = "../data/database.json"):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            self._save(DB_DEFAULTS.copy())

    def _load(self) -> Dict[str, Any]:
        with open(self.db_path, "r") as f:
            data = json.load(f)

        changed = False
        for key, value in DB_DEFAULTS.items():
            if key not in data:
                data[key] = value.copy() if isinstance(value, list) else value
                changed = True

        if changed:
            self._save(data)

        return data

    def _save(self, data: Dict[str, Any]):
        with open(self.db_path, "w") as f:
            json.dump(data, f, indent=2)

    # TRS Trades
    def get_trs_trades(self) -> List[TRSTrade]:
        data = self._load()
        return [TRSTrade(**t) for t in data.get("trs_trades", [])]

    def get_trs_trade(self, trade_id: str) -> Optional[TRSTrade]:
        trades = self.get_trs_trades()
        for trade in trades:
            if trade.id == trade_id or trade.trade_id == trade_id:
                return trade
        return None

    def create_trs_trade(self, trade: TRSTradeCreate) -> TRSTrade:
        data = self._load()
        new_trade = TRSTrade(
            id=generate_id(),
            **to_dict(trade),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        data["trs_trades"].append(to_dict(new_trade))
        self._save(data)
        return new_trade

    def update_trs_trade(self, trade_id: str, trade: TRSTradeCreate) -> Optional[TRSTrade]:
        data = self._load()
        for i, existing in enumerate(data["trs_trades"]):
            if existing["id"] == trade_id:
                updated = TRSTrade(
                    id=trade_id,
                    **to_dict(trade),
                    created_at=existing.get("created_at", datetime.now().isoformat()),
                    updated_at=datetime.now().isoformat(),
                )
                data["trs_trades"][i] = to_dict(updated)
                self._save(data)
                return updated
        return None

    def delete_trs_trade(self, trade_id: str) -> bool:
        data = self._load()
        original_len = len(data["trs_trades"])
        data["trs_trades"] = [t for t in data["trs_trades"] if t["id"] != trade_id]
        if len(data["trs_trades"]) < original_len:
            self._save(data)
            return True
        return False

    # Documents
    def get_documents(self) -> List[Document]:
        data = self._load()
        return [Document(**d) for d in data.get("documents", [])]

    def get_document(self, doc_id: str) -> Optional[Document]:
        docs = self.get_documents()
        for doc in docs:
            if doc.id == doc_id:
                return doc
        return None

    def create_document(self, doc: Document) -> Document:
        data = self._load()
        data["documents"].append(to_dict(doc))
        self._save(data)
        return doc

    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> Optional[Document]:
        data = self._load()
        for i, doc in enumerate(data["documents"]):
            if doc["id"] == doc_id:
                data["documents"][i].update(updates)
                self._save(data)
                return Document(**data["documents"][i])
        return None

    # Matching Rules
    def get_matching_rules(self) -> List[MatchingRule]:
        data = self._load()
        return [MatchingRule(**r) for r in data.get("matching_rules", [])]

    def save_matching_rules(self, rules: List[MatchingRule]) -> List[MatchingRule]:
        data = self._load()
        data["matching_rules"] = [to_dict(rule) for rule in rules]
        self._save(data)
        return rules

    # Validation Results
    def get_validation_results(self) -> List[ValidationResult]:
        data = self._load()
        return [ValidationResult(**r) for r in data.get("validation_results", [])]

    def get_validation_result(self, validation_id: str) -> Optional[ValidationResult]:
        for result in self.get_validation_results():
            if result.id == validation_id:
                return result
        return None

    def create_validation_result(self, result: ValidationResult) -> ValidationResult:
        data = self._load()
        data["validation_results"].append(to_dict(result))
        self._save(data)
        return result

    def update_validation_result(self, validation_id: str, updates: Dict[str, Any]) -> Optional[ValidationResult]:
        data = self._load()
        for i, result in enumerate(data["validation_results"]):
            if result["id"] == validation_id:
                data["validation_results"][i].update(updates)
                self._save(data)
                return ValidationResult(**data["validation_results"][i])
        return None

    def import_trades(self, trs_trades: List[TRSTradeCreate]):
        data = self._load()

        for trade in trs_trades:
            new_trade = TRSTrade(
                id=generate_id(),
                **to_dict(trade),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )
            data["trs_trades"].append(to_dict(new_trade))

        self._save(data)


# Global database instance
db = JSONDatabase(db_path=settings.database_path)
