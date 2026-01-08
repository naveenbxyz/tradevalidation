import json
import os
from typing import List, Optional, Dict, Any
from app.models import (
    FXTrade, FXTradeCreate,
    SwapTrade, SwapTradeCreate,
    Document, MatchingRule, ValidationResult
)
from app.models.schemas import generate_id
from datetime import datetime


def to_dict(obj) -> Dict[str, Any]:
    """Convert Pydantic model to dict, compatible with both v1 and v2."""
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    elif hasattr(obj, 'dict'):
        return obj.dict()
    else:
        raise ValueError(f"Cannot convert {type(obj)} to dict")


class JSONDatabase:
    """Simple JSON file-based database for the prototype."""

    def __init__(self, db_path: str = "../data/database.json"):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            self._save({
                "fx_trades": [],
                "swap_trades": [],
                "documents": [],
                "matching_rules": [],
                "validation_results": []
            })

    def _load(self) -> Dict[str, Any]:
        with open(self.db_path, 'r') as f:
            return json.load(f)

    def _save(self, data: Dict[str, Any]):
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)

    # FX Trades
    def get_fx_trades(self) -> List[FXTrade]:
        data = self._load()
        return [FXTrade(**t) for t in data.get("fx_trades", [])]

    def get_fx_trade(self, trade_id: str) -> Optional[FXTrade]:
        trades = self.get_fx_trades()
        for t in trades:
            if t.id == trade_id or t.trade_id == trade_id:
                return t
        return None

    def create_fx_trade(self, trade: FXTradeCreate) -> FXTrade:
        data = self._load()
        new_trade = FXTrade(
            id=generate_id(),
            **to_dict(trade),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        data["fx_trades"].append(to_dict(new_trade))
        self._save(data)
        return new_trade

    def update_fx_trade(self, trade_id: str, trade: FXTradeCreate) -> Optional[FXTrade]:
        data = self._load()
        for i, t in enumerate(data["fx_trades"]):
            if t["id"] == trade_id:
                updated = FXTrade(
                    id=trade_id,
                    **to_dict(trade),
                    created_at=t.get("created_at", datetime.now().isoformat()),
                    updated_at=datetime.now().isoformat()
                )
                data["fx_trades"][i] = to_dict(updated)
                self._save(data)
                return updated
        return None

    def delete_fx_trade(self, trade_id: str) -> bool:
        data = self._load()
        original_len = len(data["fx_trades"])
        data["fx_trades"] = [t for t in data["fx_trades"] if t["id"] != trade_id]
        if len(data["fx_trades"]) < original_len:
            self._save(data)
            return True
        return False

    # Swap Trades
    def get_swap_trades(self) -> List[SwapTrade]:
        data = self._load()
        return [SwapTrade(**t) for t in data.get("swap_trades", [])]

    def get_swap_trade(self, trade_id: str) -> Optional[SwapTrade]:
        trades = self.get_swap_trades()
        for t in trades:
            if t.id == trade_id or t.trade_id == trade_id:
                return t
        return None

    def create_swap_trade(self, trade: SwapTradeCreate) -> SwapTrade:
        data = self._load()
        new_trade = SwapTrade(
            id=generate_id(),
            **to_dict(trade),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        data["swap_trades"].append(to_dict(new_trade))
        self._save(data)
        return new_trade

    def update_swap_trade(self, trade_id: str, trade: SwapTradeCreate) -> Optional[SwapTrade]:
        data = self._load()
        for i, t in enumerate(data["swap_trades"]):
            if t["id"] == trade_id:
                updated = SwapTrade(
                    id=trade_id,
                    **to_dict(trade),
                    created_at=t.get("created_at", datetime.now().isoformat()),
                    updated_at=datetime.now().isoformat()
                )
                data["swap_trades"][i] = to_dict(updated)
                self._save(data)
                return updated
        return None

    def delete_swap_trade(self, trade_id: str) -> bool:
        data = self._load()
        original_len = len(data["swap_trades"])
        data["swap_trades"] = [t for t in data["swap_trades"] if t["id"] != trade_id]
        if len(data["swap_trades"]) < original_len:
            self._save(data)
            return True
        return False

    # Documents
    def get_documents(self) -> List[Document]:
        data = self._load()
        return [Document(**d) for d in data.get("documents", [])]

    def get_document(self, doc_id: str) -> Optional[Document]:
        docs = self.get_documents()
        for d in docs:
            if d.id == doc_id:
                return d
        return None

    def create_document(self, doc: Document) -> Document:
        data = self._load()
        data["documents"].append(to_dict(doc))
        self._save(data)
        return doc

    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> Optional[Document]:
        data = self._load()
        for i, d in enumerate(data["documents"]):
            if d["id"] == doc_id:
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
        data["matching_rules"] = [to_dict(r) for r in rules]
        self._save(data)
        return rules

    # Validation Results
    def get_validation_results(self) -> List[ValidationResult]:
        data = self._load()
        return [ValidationResult(**r) for r in data.get("validation_results", [])]

    def create_validation_result(self, result: ValidationResult) -> ValidationResult:
        data = self._load()
        data["validation_results"].append(to_dict(result))
        self._save(data)
        return result

    def import_trades(self, fx_trades: List[FXTradeCreate], swap_trades: List[SwapTradeCreate]):
        data = self._load()

        for trade in fx_trades:
            new_trade = FXTrade(
                id=generate_id(),
                **to_dict(trade),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            data["fx_trades"].append(to_dict(new_trade))

        for trade in swap_trades:
            new_trade = SwapTrade(
                id=generate_id(),
                **to_dict(trade),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            data["swap_trades"].append(to_dict(new_trade))

        self._save(data)


# Global database instance
db = JSONDatabase()
