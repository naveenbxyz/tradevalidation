from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
import uuid

from pydantic import BaseModel, Field


def generate_id() -> str:
    return str(uuid.uuid4())


class TRSTradeBase(BaseModel):
    trade_id: str
    party_a: str
    party_b: str
    trade_date: str
    effective_date: str
    scheduled_termination_date: str
    bond_return_payer: Literal["PartyA", "PartyB"]
    bond_return_receiver: Literal["PartyA", "PartyB"]
    local_currency: str
    notional_amount: float
    usd_notional_amount: float
    initial_spot_rate: float
    current_market_price: float
    underlier: Optional[str] = None
    isin: Optional[str] = None


class TRSTradeCreate(TRSTradeBase):
    pass


class TRSTrade(TRSTradeBase):
    id: str = Field(default_factory=generate_id)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class FieldProvenance(BaseModel):
    source_type: Literal["email_body", "attachment", "ocr", "unknown"] = "unknown"
    source_name: Optional[str] = None
    page: Optional[int] = None
    bbox: Optional[Dict[str, float]] = None


class ExtractedField(BaseModel):
    value: Any
    confidence: float = 1.0
    provenance: Optional[FieldProvenance] = None


class ExtractedTrade(BaseModel):
    trade_type: Literal["TRS"] = "TRS"
    fields: Dict[str, ExtractedField]
    raw_text: Optional[str] = None
    schema_version: Optional[str] = None


class MatchingRule(BaseModel):
    id: str
    field_name: str
    rule_type: Literal["exact", "tolerance", "fuzzy", "date_tolerance"]
    tolerance_value: Optional[float] = None
    tolerance_unit: Optional[Literal["percent", "absolute", "days"]] = None
    min_confidence: float = 0.0
    enabled: bool = True


class FieldComparison(BaseModel):
    field_name: str
    extracted_value: Any
    system_value: Any
    match_status: Literal["MATCH", "MISMATCH", "WITHIN_TOLERANCE", "LOW_CONFIDENCE"]
    confidence: float
    min_required_confidence: Optional[float] = None
    rule_applied: Optional[str] = None


class ValidationResult(BaseModel):
    id: str = Field(default_factory=generate_id)
    document_id: str
    system_trade_id: str
    status: Literal["MATCH", "MISMATCH", "PARTIAL", "PENDING"] = "PENDING"
    field_comparisons: List[FieldComparison] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # Enriched fields for dashboard display
    party_a: Optional[str] = None
    party_b: Optional[str] = None
    product: str = "TRS"
    trade_date: Optional[str] = None
    effective_date: Optional[str] = None
    scheduled_termination_date: Optional[str] = None
    local_currency: Optional[str] = None
    notional_amount: Optional[float] = None
    machine_confidence: Optional[float] = None
    auto_passed: bool = False

    # Checker workflow fields
    checker_decision: Literal["PENDING", "APPROVED", "REJECTED", "OVERRIDDEN"] = "PENDING"
    checker_comment: Optional[str] = None
    checker_override_status: Optional[Literal["MATCH", "MISMATCH", "PARTIAL"]] = None
    checker_override_trade_id: Optional[str] = None
    checked_at: Optional[str] = None


class Document(BaseModel):
    id: str = Field(default_factory=generate_id)
    filename: str
    file_type: Literal["pdf", "image", "text", "msg", "docx"]
    upload_date: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: Literal["PENDING", "PROCESSING", "EXTRACTED", "VALIDATED", "ERROR"] = "PENDING"
    file_path: Optional[str] = None
    content: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    validation_result: Optional[Dict[str, Any]] = None
    processing_warnings: List[str] = Field(default_factory=list)


class TextInput(BaseModel):
    content: str


class TradeImport(BaseModel):
    trs_trades: List[TRSTradeCreate] = Field(default_factory=list)


class FolderScanRequest(BaseModel):
    folder_path: Optional[str] = None


class CheckerActionRequest(BaseModel):
    decision: Literal["APPROVE", "REJECT", "OVERRIDE"]
    override_status: Optional[Literal["MATCH", "MISMATCH", "PARTIAL"]] = None
    override_system_trade_id: Optional[str] = None
    comment: Optional[str] = None
