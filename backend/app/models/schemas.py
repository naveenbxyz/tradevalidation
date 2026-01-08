from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal, TYPE_CHECKING
from datetime import datetime
import uuid


def generate_id():
    return str(uuid.uuid4())


class FXTradeBase(BaseModel):
    trade_id: str
    counterparty: str
    currency_pair: str
    direction: Literal["BUY", "SELL"]
    notional: float
    rate: float
    trade_date: str
    value_date: str


class FXTradeCreate(FXTradeBase):
    pass


class FXTrade(FXTradeBase):
    id: str = Field(default_factory=generate_id)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class SwapTradeBase(BaseModel):
    trade_id: str
    counterparty: str
    trade_type: Literal["IRS", "CCS", "BASIS"]
    notional: float
    currency: str
    fixed_rate: float
    floating_index: str
    spread: float
    effective_date: str
    maturity_date: str
    payment_frequency: str


class SwapTradeCreate(SwapTradeBase):
    pass


class SwapTrade(SwapTradeBase):
    id: str = Field(default_factory=generate_id)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ExtractedField(BaseModel):
    value: Any
    confidence: float = 1.0


class ExtractedTrade(BaseModel):
    trade_type: Literal["FX", "SWAP"]
    fields: Dict[str, ExtractedField]
    raw_text: Optional[str] = None


class MatchingRule(BaseModel):
    id: str
    field_name: str
    rule_type: Literal["exact", "tolerance", "fuzzy", "date_tolerance"]
    tolerance_value: Optional[float] = None
    tolerance_unit: Optional[Literal["percent", "absolute", "days"]] = None
    enabled: bool = True


class FieldComparison(BaseModel):
    field_name: str
    extracted_value: Any
    system_value: Any
    match_status: Literal["MATCH", "MISMATCH", "WITHIN_TOLERANCE"]
    confidence: float
    rule_applied: Optional[str] = None


class ValidationResult(BaseModel):
    id: str = Field(default_factory=generate_id)
    document_id: str
    system_trade_id: str
    status: Literal["MATCH", "MISMATCH", "PARTIAL", "PENDING"] = "PENDING"
    field_comparisons: List[FieldComparison] = []
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    # Enriched fields for dashboard display
    document_name: Optional[str] = None
    counterparty: Optional[str] = None
    trade_type: Optional[str] = None
    notional: Optional[float] = None
    currency: Optional[str] = None
    confidence: Optional[float] = None


class Document(BaseModel):
    id: str = Field(default_factory=generate_id)
    filename: str
    file_type: Literal["pdf", "image", "text"]
    upload_date: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: Literal["PENDING", "PROCESSING", "EXTRACTED", "VALIDATED", "ERROR"] = "PENDING"
    file_path: Optional[str] = None
    content: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    validation_result: Optional[Dict[str, Any]] = None


class TextInput(BaseModel):
    content: str


class TradeImport(BaseModel):
    fx_trades: List[FXTradeCreate] = []
    swap_trades: List[SwapTradeCreate] = []
