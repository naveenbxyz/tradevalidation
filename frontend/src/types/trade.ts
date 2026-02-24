export type TradeType = 'TRS';

export interface TRSTrade {
  id: string;
  trade_id: string;
  party_a: string;
  party_b: string;
  trade_date: string;
  effective_date: string;
  scheduled_termination_date: string;
  bond_return_payer: 'PartyA' | 'PartyB';
  bond_return_receiver: 'PartyA' | 'PartyB';
  local_currency: string;
  notional_amount: number;
  usd_notional_amount: number;
  initial_spot_rate: number;
  current_market_price: number;
  underlier?: string;
  isin?: string;
  created_at?: string;
  updated_at?: string;
}

export interface FieldProvenance {
  source_type: 'email_body' | 'attachment' | 'ocr' | 'unknown';
  source_name?: string | null;
  page?: number | null;
  bbox?: Record<string, number> | null;
}

export interface ExtractedField {
  value: string | number | null;
  confidence: number;
  provenance?: FieldProvenance;
}

export interface ExtractedTrade {
  trade_type: TradeType;
  schema_version?: string;
  fields: Record<string, ExtractedField>;
  raw_text?: string;
  evidence_metadata?: Record<string, unknown>;
}

export interface MatchingRule {
  id: string;
  field_name: string;
  rule_type: 'exact' | 'tolerance' | 'fuzzy' | 'date_tolerance';
  tolerance_value?: number;
  tolerance_unit?: 'percent' | 'absolute' | 'days';
  min_confidence: number;
  enabled: boolean;
}

export interface ValidationResult {
  id: string;
  document_id: string;
  system_trade_id: string;
  status: 'MATCH' | 'MISMATCH' | 'PARTIAL' | 'PENDING';
  field_comparisons: FieldComparison[];
  created_at: string;
  party_a?: string;
  party_b?: string;
  product: 'TRS';
  trade_date?: string;
  effective_date?: string;
  scheduled_termination_date?: string;
  local_currency?: string;
  notional_amount?: number;
  machine_confidence?: number;
  auto_passed: boolean;
  checker_decision: 'PENDING' | 'APPROVED' | 'REJECTED' | 'OVERRIDDEN';
  checker_comment?: string;
  checker_override_status?: 'MATCH' | 'MISMATCH' | 'PARTIAL';
  checker_override_trade_id?: string;
  checked_at?: string;
}

export interface FieldComparison {
  field_name: string;
  extracted_value: string | number | null;
  system_value: string | number | null;
  match_status: 'MATCH' | 'MISMATCH' | 'WITHIN_TOLERANCE' | 'LOW_CONFIDENCE';
  confidence: number;
  min_required_confidence?: number;
  rule_applied?: string;
}

export interface Document {
  id: string;
  filename: string;
  file_type: 'pdf' | 'image' | 'text' | 'msg' | 'docx';
  upload_date: string;
  status: 'PENDING' | 'PROCESSING' | 'EXTRACTED' | 'VALIDATED' | 'ERROR';
  extracted_data?: ExtractedTrade;
  validation_result?: ValidationResult;
  processing_warnings?: string[];
}

export interface OCRWord {
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
}

export interface FieldCoordinate {
  x: number;
  y: number;
  width: number;
  height: number;
  matched_text: string;
  confidence: number;
  field_value: string;
}

export interface DocumentViewerData {
  document_id: string;
  filename: string;
  page: number;
  image_base64: string;
  image_width: number;
  image_height: number;
  ocr_words: OCRWord[];
  field_coordinates: Record<string, FieldCoordinate>;
  extracted_data?: ExtractedTrade;
}
