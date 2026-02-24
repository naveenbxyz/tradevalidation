# TRS Automated Trade Validation - Refreshed Design

## 1. Objective

Convert the prototype into a working end-to-end solution for **Total Return Swap (TRS)** validation from unstructured counterparty evidence.

The solution must demonstrate:
- ingestion of Outlook `.msg` evidence and attachments,
- schema-driven structured extraction,
- field-level comparison against a simulated source-of-truth trade record,
- confidence-driven automation with checker intervention,
- downloadable validation reporting.

## 2. Scope Implemented (Current Iteration)

- Product scope: **TRS only**.
- Evidence input:
  - direct upload (`.msg`, `.pdf`, `.docx`, images),
  - scan predefined inbox folder for files.
- `.msg` handling:
  - parse email body,
  - parse supported attachments (`pdf`, `docx`, images),
  - ignore unsupported attachments,
  - ignore `.zip` attachments for now.
- Structured extraction:
  - TRS schema loaded from JSON config at runtime.
- Validation:
  - compare extracted fields against local mock TRS trades in JSON DB.
  - per-field matching rule + per-field min confidence.
- Decisioning:
  - machine status (`MATCH`, `PARTIAL`, `MISMATCH`),
  - auto-pass if machine confidence >= 0.85 and status is `MATCH`,
  - checker actions: `Approve`, `Reject`, `Override`.
- Reporting:
  - export validations as CSV.

## 3. Data and Schema Design

### 3.1 TRS trade schema (system of record)
- `trade_id`
- `party_a`
- `party_b`
- `trade_date`
- `effective_date`
- `scheduled_termination_date`
- `bond_return_payer` (`PartyA`/`PartyB`)
- `bond_return_receiver` (`PartyA`/`PartyB`)
- `local_currency`
- `notional_amount`
- `usd_notional_amount`
- `initial_spot_rate`
- `current_market_price`
- optional: `underlier`, `isin`

### 3.2 Extraction schema
Configured in: `backend/app/schema_configs/trs_schema.json`

This schema can evolve without backend code changes as long as the field names remain aligned with matching rules and source trade records.

### 3.3 Matching rule model
Per field:
- `rule_type`: exact, tolerance, fuzzy, date_tolerance
- `tolerance_value` + `tolerance_unit`
- `min_confidence`
- `enabled`

## 4. End-to-End Workflow

1. Ingest evidence (`/api/documents/upload` or `/api/documents/scan-folder`).
2. Normalize evidence (`/api/documents/{id}/extract`):
   - parse body + attachments,
   - OCR fallback for images/scanned PDFs,
   - build merged text context.
3. Extract structured TRS fields via schema-driven LLM extractor.
4. Validate against mock source-of-truth (`/api/documents/{id}/validate`).
5. Auto-pass if threshold condition is met.
6. Checker reviews and acts (`/api/validations/{id}/checker`).
7. Download report (`/api/validations/report`).

## 5. UI Capability Map

- **Evidence page**: upload/scan, extract, validate, field confidence display.
- **TRS trades page**: CRUD + import/export source-of-truth records.
- **Matching rules page**: per-field rule and confidence threshold tuning.
- **Validation dashboard**: machine result, checker decisioning, override controls, report download.

## 6. Key Assumptions

- `.msg` samples and parser behavior will be iterated after running in air-gapped environment.
- Attachment scope is intentionally narrow in this iteration (`pdf`, `docx`, images).
- Field-level bounding-box provenance from attachments is partial today; full attachment-page/bbox provenance is a planned next iteration.

## 7. Current Limitations

- JSON persistence (prototype only; no concurrency controls).
- Synchronous extraction/validation API (no background queue).
- `.zip` attachment content is not unpacked.
- No mailbox connector yet; folder scan simulates exchange inbox ingestion.
- No auth/entitlements for checker actions.

## 8. Next Iteration Priorities

1. Harden `.msg` parsing based on real sample edge cases.
2. Add richer provenance links (attachment name + page + bbox per field).
3. Add async extraction/validation workers and retry policy.
4. Extend TRS schema (financing leg, spread, reset frequency, valuation terms).
5. Add immutable audit/event history for checker actions.
