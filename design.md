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

## 9. Accuracy Strategy: Prompt Engineering vs Model Training

### Context

Users raised whether model training (fine-tuning) is needed if per-field extraction accuracy remains low. The strategic position is to **exhaust prompt/context engineering first** and defer model training given the regulatory cost (SR 11-7 model governance, purpose-trained model approvals, ongoing monitoring burden).

### Why defer training

- Regulatory approval for purpose-trained models is expensive and slow (months).
- Insufficient labeled data today — need hundreds of examples per counterparty format.
- Frontier models are improving rapidly; context windows growing (128K → 1M+). Standard termsheet formats will likely be handled well by general models within 12-18 months.
- The current pipeline is exactly what generates the training data over time.

### Where training may eventually help

- Tail-end counterparty formats (low volume, unusual layouts).
- Firm-specific entity normalization (internal IDs, desk shorthand, booking entity names).
- Confidence calibration (prompted confidence is unreliable; trained models can be statistically meaningful).
- Consistency (same input → same output reliably).

### Accuracy improvement roadmap (prompt engineering first)

| Phase | Action | Expected lift |
|-------|--------|---------------|
| Now | Ship with schema-driven prompt + context engineering | Baseline |
| +1 quarter | Golden examples library → few-shot prompts per counterparty format | 5-15% |
| +2 quarters | Per-counterparty prompt templates for top 10 formats | Incremental |
| +3 quarters | Evaluate plateau → decide whether to start training conversation | Decision gate |

### TODO: Build the feedback data asset (do now, use later)

The data captured below is valuable regardless of whether we ever train — it drives prompt improvement today and keeps the training option open.

- [ ] **Capture checker corrections** — for every extraction, log the diff between LLM output and human-corrected values:
  ```
  {
    document_id, counterparty_format, input_content_hash,
    llm_extracted_fields, checker_corrections,
    final_validated_fields, model_used, prompt_version, accuracy_score
  }
  ```
- [ ] **Track accuracy over time** — per field, per counterparty format, per model version. Surface in a dashboard so we can see where the model is improving and where it's stuck.
- [ ] **Golden examples library** — monthly review of worst-performing formats. Promote 2-3 corrected examples per format into a curated set used for few-shot prompting.
- [ ] **Per-counterparty prompt templates** — for top N counterparties by volume, craft format-specific extraction prompts that account for their layout conventions.
- [ ] **Retrieval-augmented few-shot** — dynamically pull the most similar previously-validated trade as a reference example into the prompt at extraction time.
- [ ] **Prompt versioning** — tag each extraction with the prompt version used, so we can A/B compare prompt changes against accuracy metrics.

### Decision gate for model training

Trigger the training conversation when:
1. Prompt engineering + few-shot examples have been optimized for top formats.
2. Accuracy is plateauing below target on specific counterparty formats.
3. Sufficient labeled data exists (100+ corrected examples per target format).
4. Business case justifies the regulatory approval investment.

Until then: build the data, improve the prompts, and let the models catch up.
