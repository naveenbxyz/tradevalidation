# TRS Automated Trade Validation Prototype

TRS-only prototype for automated trade validation using unstructured evidence (`.msg`, PDF, DOCX, images), LLM extraction, rule-based matching, and checker review.

## Key Components

- `backend/main.py`: FastAPI entrypoint.
- `backend/app/api/routes.py`: APIs for ingest, extract, validate, checker decisions, and report export.
- `backend/app/services/evidence_processor.py`: Evidence normalization (`.msg` body + attachments, OCR fallback, DOCX/PDF parsing).
- `backend/app/services/llm_extractor.py`: Schema-driven TRS extraction.
- `backend/app/services/comparison_engine.py`: Field-level matching logic + confidence-aware status.
- `backend/app/schema_configs/trs_schema.json`: Configurable TRS extraction schema.
- `backend/app/models/schemas.py`: Pydantic models for TRS trade, extraction fields, matching rules, validation results.
- `backend/app/db/database.py`: JSON-file persistence.
- `frontend/src/pages/DocumentUpload.tsx`: Upload and folder-scan ingestion UI.
- `frontend/src/pages/Trades.tsx`: Source-of-truth TRS trade records (CRUD/import/export).
- `frontend/src/pages/MatchingRules.tsx`: Field-level rule + minimum confidence configuration.
- `frontend/src/pages/ValidationDashboard.tsx`: Machine outcomes, checker approve/reject/override, report download.

## Supported Workflow

1. Upload evidence (`.msg`, `.pdf`, `.docx`, images) or scan predefined folder.
2. Extract structured TRS fields from normalized evidence.
3. Validate against mock source-of-truth TRS trades.
4. Auto-pass `MATCH` trades above configured confidence threshold.
5. Checker approves/rejects/overrides remaining items.
6. Download CSV report.

## Run Locally

### Backend

```bash
./start_backend.sh
```

### Frontend

```bash
./start_frontend.sh
```

- API docs: `http://localhost:8000/docs`
- UI: `http://localhost:5173`

## Configuration

Use `backend/.env` (see `backend/.env.example`):

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` (optional)
- `LLM_MODEL`
- `DATABASE_PATH`
- `UPLOAD_DIR`
- `INGEST_SCAN_DIR`
- `TRS_SCHEMA_PATH`
- `AUTO_PASS_THRESHOLD`
- `MAX_FILE_SIZE`

## How To Update the TRS Extraction Schema

Primary config file:
- `backend/app/schema_configs/trs_schema.json`

### Safe change procedure

1. Add/update field definitions in `trs_schema.json`.
2. Keep names aligned with `TRSTradeBase` in `backend/app/models/schemas.py`.
3. Add comparison coverage in `trs_fields` list inside `backend/app/services/comparison_engine.py`.
4. Add default matching rule in `backend/init_data.py` (optional but recommended).
5. Expose/edit in UI if required:
   - trade editor: `frontend/src/pages/Trades.tsx`
   - rule editor defaults: `frontend/src/pages/MatchingRules.tsx`
6. Re-run backend + frontend build checks.

### Example: add a new field `financing_spread`

1. Add to `trs_schema.json`:
```json
{"name": "financing_spread", "type": "number", "required": false}
```
2. Add `financing_spread: Optional[float] = None` in `TRSTradeBase`.
3. Add `"financing_spread"` to `trs_fields` in comparison engine.
4. Add a default tolerance rule in `init_data.py`.
5. Add form input in `Trades.tsx` and optionally display it in dashboard.

## Current Constraints

- JSON DB only (prototype; no concurrency controls).
- `.zip` attachments are ignored.
- Full attachment-level bbox provenance is partial and planned for a later iteration.
- Mailbox connector is not implemented yet; folder scan simulates inbox ingestion.
