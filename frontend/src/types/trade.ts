export type TradeType = 'FX' | 'SWAP';

export interface FXTrade {
  id: string;
  trade_id: string;
  counterparty: string;
  currency_pair: string;
  direction: 'BUY' | 'SELL';
  notional: number;
  rate: number;
  trade_date: string;
  value_date: string;
  created_at?: string;
  updated_at?: string;
}

export interface SwapTrade {
  id: string;
  trade_id: string;
  counterparty: string;
  trade_type: 'IRS' | 'CCS' | 'BASIS';
  notional: number;
  currency: string;
  fixed_rate: number;
  floating_index: string;
  spread: number;
  effective_date: string;
  maturity_date: string;
  payment_frequency: string;
  created_at?: string;
  updated_at?: string;
}

export type Trade = FXTrade | SwapTrade;

export interface ExtractedTrade {
  trade_type: TradeType;
  fields: Record<string, { value: string | number; confidence: number }>;
  raw_text?: string;
}

export interface MatchingRule {
  id: string;
  field_name: string;
  rule_type: 'exact' | 'tolerance' | 'fuzzy' | 'date_tolerance';
  tolerance_value?: number;
  tolerance_unit?: 'percent' | 'absolute' | 'days';
  enabled: boolean;
}

export interface ValidationResult {
  id: string;
  document_id: string;
  system_trade_id: string;
  status: 'MATCH' | 'MISMATCH' | 'PARTIAL' | 'PENDING';
  field_comparisons: FieldComparison[];
  created_at: string;
  // Enriched fields for dashboard display
  document_name?: string;
  counterparty?: string;
  trade_type?: TradeType | 'IRS' | 'CCS' | 'BASIS';
  notional?: number;
  currency?: string;
  confidence?: number;
}

export interface FieldComparison {
  field_name: string;
  extracted_value: string | number;
  system_value: string | number;
  match_status: 'MATCH' | 'MISMATCH' | 'WITHIN_TOLERANCE';
  confidence: number;
  rule_applied?: string;
}

export interface Document {
  id: string;
  filename: string;
  file_type: 'pdf' | 'image' | 'text';
  upload_date: string;
  status: 'PENDING' | 'PROCESSING' | 'EXTRACTED' | 'VALIDATED' | 'ERROR';
  extracted_data?: ExtractedTrade;
  validation_result?: ValidationResult;
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
