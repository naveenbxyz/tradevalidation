import csv
import io
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.config import settings
from app.db import db
from app.models import (
    CheckerActionRequest,
    Document,
    FolderScanRequest,
    MatchingRule,
    TRSTrade,
    TRSTradeCreate,
    TextInput,
    TradeImport,
    ValidationResult,
)
from app.models.schemas import generate_id
from app.services import comparison_engine, evidence_processor, extractor

router = APIRouter()


# ============== Chat ==============


class ChatRequest(BaseModel):
    message: str
    context: list = []


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
async def chat_with_context(request: ChatRequest):
    """Chat endpoint that answers questions about validation results."""
    from openai import OpenAI

    context_summary = build_context_summary(request.context)

    system_prompt = f"""You are an assistant for a TRS trade validation system.

Use only the validation context below:
{context_summary}

Keep responses concise and factual.
If information is missing in context, say so clearly."""

    try:
        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url if settings.openai_base_url else None,
        )

        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message},
            ],
            max_tokens=500,
            temperature=0.2,
        )

        return ChatResponse(response=response.choices[0].message.content)
    except Exception:
        return ChatResponse(response=generate_fallback_response(request.message, request.context))


def build_context_summary(validations: list) -> str:
    if not validations:
        return "No validation results available."

    total = len(validations)
    matched = sum(1 for v in validations if v.get("status") == "MATCH")
    partial = sum(1 for v in validations if v.get("status") == "PARTIAL")
    mismatched = sum(1 for v in validations if v.get("status") == "MISMATCH")

    return (
        f"Total validations: {total}\n"
        f"Matched: {matched}\n"
        f"Partial: {partial}\n"
        f"Mismatched: {mismatched}\n"
    )


def generate_fallback_response(message: str, validations: list) -> str:
    text = message.lower()

    total = len(validations)
    matched = sum(1 for v in validations if v.get("status") == "MATCH")
    partial = sum(1 for v in validations if v.get("status") == "PARTIAL")
    mismatched = sum(1 for v in validations if v.get("status") == "MISMATCH")

    if "how many" in text and "match" in text:
        return (
            f"Out of {total} validations: {matched} matched, "
            f"{partial} partial, {mismatched} mismatched."
        )

    if "checker" in text:
        approved = sum(1 for v in validations if v.get("checker_decision") == "APPROVED")
        rejected = sum(1 for v in validations if v.get("checker_decision") == "REJECTED")
        overridden = sum(1 for v in validations if v.get("checker_decision") == "OVERRIDDEN")
        return (
            f"Checker decisions: approved={approved}, rejected={rejected}, "
            f"overridden={overridden}."
        )

    return "Ask about match counts, mismatch trades, or checker decisions."


# ============== TRS Trades ==============


@router.get("/trades/trs", response_model=List[TRSTrade])
async def get_trs_trades():
    return db.get_trs_trades()


@router.get("/trades/trs/{trade_id}", response_model=TRSTrade)
async def get_trs_trade(trade_id: str):
    trade = db.get_trs_trade(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="TRS trade not found")
    return trade


@router.post("/trades/trs", response_model=TRSTrade)
async def create_trs_trade(trade: TRSTradeCreate):
    return db.create_trs_trade(trade)


@router.put("/trades/trs/{trade_id}", response_model=TRSTrade)
async def update_trs_trade(trade_id: str, trade: TRSTradeCreate):
    updated = db.update_trs_trade(trade_id, trade)
    if not updated:
        raise HTTPException(status_code=404, detail="TRS trade not found")
    return updated


@router.delete("/trades/trs/{trade_id}")
async def delete_trs_trade(trade_id: str):
    if not db.delete_trs_trade(trade_id):
        raise HTTPException(status_code=404, detail="TRS trade not found")
    return {"status": "deleted"}


# ============== Trade Import ==============


@router.post("/trades/import")
async def import_trades(data: TradeImport):
    db.import_trades(data.trs_trades)
    return {"status": "imported", "trs_count": len(data.trs_trades)}


# ============== Documents ==============


@router.get("/documents", response_model=List[Document])
async def get_documents():
    return db.get_documents()


def _resolve_upload_file_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "docx"
    if ext == ".msg":
        return "msg"
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp"}:
        return "image"
    raise ValueError(f"File type not allowed: {ext}")


@router.post("/documents/upload", response_model=Document)
async def upload_document(file: UploadFile = File(...)):
    try:
        file_type = _resolve_upload_file_type(file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    content = await file.read()
    if len(content) > settings.max_file_size:
        raise HTTPException(status_code=400, detail="File too large")

    doc_id = generate_id()
    ext = os.path.splitext(file.filename)[1].lower()
    file_path = os.path.join(settings.upload_dir, f"{doc_id}{ext}")

    async with aiofiles.open(file_path, "wb") as output_file:
        await output_file.write(content)

    doc = Document(
        id=doc_id,
        filename=file.filename,
        file_type=file_type,
        file_path=file_path,
        status="PENDING",
    )

    db.create_document(doc)
    return doc


@router.post("/documents/scan-folder")
async def scan_documents_folder(request: FolderScanRequest):
    folder = request.folder_path or settings.ingest_scan_dir
    folder_path = Path(folder)

    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Folder not found: {folder}")

    existing_paths = {doc.file_path for doc in db.get_documents() if doc.file_path}
    created: List[Document] = []
    skipped: List[str] = []

    for file_path in sorted(folder_path.iterdir()):
        if not file_path.is_file():
            continue

        try:
            file_type = _resolve_upload_file_type(file_path.name)
        except ValueError:
            skipped.append(f"Unsupported: {file_path.name}")
            continue

        if str(file_path) in existing_paths:
            skipped.append(f"Already ingested: {file_path.name}")
            continue

        doc = Document(
            id=generate_id(),
            filename=file_path.name,
            file_type=file_type,
            file_path=str(file_path),
            status="PENDING",
        )
        db.create_document(doc)
        created.append(doc)

    return {
        "folder": str(folder_path),
        "created_count": len(created),
        "created_ids": [doc.id for doc in created],
        "skipped": skipped,
    }


@router.post("/documents/text", response_model=Document)
async def submit_text(text_input: TextInput):
    doc_id = generate_id()

    doc = Document(
        id=doc_id,
        filename=f"text_input_{doc_id[:8]}.txt",
        file_type="text",
        content=text_input.content,
        status="PENDING",
    )

    db.create_document(doc)
    return doc


@router.post("/documents/{doc_id}/extract", response_model=Document)
async def extract_document(doc_id: str):
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    db.update_document(doc_id, {"status": "PROCESSING"})

    try:
        evidence = evidence_processor.prepare_document_content(doc)
        extracted_data = await extractor.extract_trade_data(
            content=evidence.content,
            image_path=evidence.image_path,
        )

        extracted_payload = extracted_data.model_dump()
        extracted_payload["evidence_metadata"] = evidence.metadata

        updated_doc = db.update_document(
            doc_id,
            {
                "status": "EXTRACTED",
                "content": evidence.content,
                "extracted_data": extracted_payload,
                "processing_warnings": evidence.metadata.get("warnings", []),
            },
        )

        return updated_doc
    except Exception as exc:
        db.update_document(doc_id, {"status": "ERROR", "processing_warnings": [str(exc)]})
        raise HTTPException(status_code=500, detail=f"Extraction failed: {exc}") from exc


@router.get("/documents/{doc_id}/viewer")
async def get_document_viewer_data(doc_id: str, page: int = 0):
    from app.services import vision_ocr

    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not doc.file_path:
        raise HTTPException(status_code=400, detail="Document has no file for viewing")

    if doc.file_type not in {"pdf", "image"}:
        raise HTTPException(status_code=400, detail="Viewer supports only PDF/image documents")

    try:
        ocr_result = vision_ocr.process_document(doc.file_path, page_num=page)

        field_coordinates: Dict[str, Dict] = {}
        if doc.extracted_data and doc.extracted_data.get("fields"):
            field_coordinates = vision_ocr.get_field_coordinates(
                doc.extracted_data["fields"],
                ocr_result.words,
            )

        return {
            "document_id": doc_id,
            "filename": doc.filename,
            "page": page,
            "image_base64": ocr_result.image_base64,
            "image_width": ocr_result.image_width,
            "image_height": ocr_result.image_height,
            "ocr_words": [
                {
                    "text": word.text,
                    "x": word.x,
                    "y": word.y,
                    "width": word.width,
                    "height": word.height,
                    "confidence": word.confidence,
                }
                for word in ocr_result.words
            ],
            "field_coordinates": field_coordinates,
            "extracted_data": doc.extracted_data,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {exc}") from exc


@router.post("/documents/{doc_id}/validate", response_model=Document)
async def validate_document(doc_id: str):
    from app.models import ExtractedField, ExtractedTrade

    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not doc.extracted_data:
        raise HTTPException(status_code=400, detail="Document has not been extracted yet")

    try:
        extracted = ExtractedTrade(
            trade_type="TRS",
            schema_version=doc.extracted_data.get("schema_version"),
            fields={
                key: ExtractedField(**value)
                if isinstance(value, dict)
                else ExtractedField(value=value, confidence=0.5)
                for key, value in doc.extracted_data.get("fields", {}).items()
            },
            raw_text=doc.extracted_data.get("raw_text"),
        )

        comparison_engine.set_rules(db.get_matching_rules())

        validation_result = comparison_engine.find_best_match(
            extracted=extracted,
            trs_trades=db.get_trs_trades(),
            document_id=doc_id,
        )

        if not validation_result:
            validation_result = comparison_engine.build_unmatched_result(
                extracted=extracted,
                document_id=doc_id,
            )

        machine_conf = validation_result.machine_confidence or 0.0
        auto_passed = validation_result.status == "MATCH" and machine_conf >= settings.auto_pass_threshold

        validation_payload = validation_result.model_dump()
        validation_payload["auto_passed"] = auto_passed
        if auto_passed:
            validation_payload["checker_decision"] = "APPROVED"
            validation_payload["checked_at"] = datetime.now().isoformat()
            validation_payload["checker_comment"] = (
                f"Auto-approved by threshold >= {settings.auto_pass_threshold:.2f}"
            )

        stored_result = ValidationResult(**validation_payload)
        db.create_validation_result(stored_result)

        updated_doc = db.update_document(
            doc_id,
            {"status": "VALIDATED", "validation_result": stored_result.model_dump()},
        )
        return updated_doc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Validation failed: {exc}") from exc


# ============== Matching Rules ==============


@router.get("/rules", response_model=List[MatchingRule])
async def get_matching_rules():
    return db.get_matching_rules()


@router.put("/rules", response_model=List[MatchingRule])
async def save_matching_rules(rules: List[MatchingRule]):
    return db.save_matching_rules(rules)


# ============== Validation Results ==============


@router.get("/validations", response_model=List[ValidationResult])
async def get_validation_results():
    return db.get_validation_results()


@router.post("/validations/{validation_id}/checker", response_model=ValidationResult)
async def checker_action(validation_id: str, request: CheckerActionRequest):
    validation = db.get_validation_result(validation_id)
    if not validation:
        raise HTTPException(status_code=404, detail="Validation not found")

    updates: Dict[str, object] = {
        "checked_at": datetime.now().isoformat(),
        "checker_comment": request.comment,
    }

    if request.decision == "APPROVE":
        updates["checker_decision"] = "APPROVED"
    elif request.decision == "REJECT":
        updates["checker_decision"] = "REJECTED"
    else:
        if not request.override_status:
            raise HTTPException(status_code=400, detail="override_status is required for OVERRIDE")
        updates["checker_decision"] = "OVERRIDDEN"
        updates["checker_override_status"] = request.override_status
        updates["status"] = request.override_status
        if request.override_system_trade_id:
            updates["checker_override_trade_id"] = request.override_system_trade_id
            updates["system_trade_id"] = request.override_system_trade_id

    updated_validation = db.update_validation_result(validation_id, updates)
    if not updated_validation:
        raise HTTPException(status_code=500, detail="Failed to update validation")

    doc = db.get_document(updated_validation.document_id)
    if doc:
        db.update_document(doc.id, {"validation_result": updated_validation.model_dump()})

    return updated_validation


@router.get("/validations/report")
async def export_validation_report():
    validations = db.get_validation_results()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "validation_id",
            "document_id",
            "machine_status",
            "checker_decision",
            "system_trade_id",
            "party_a",
            "party_b",
            "trade_date",
            "effective_date",
            "scheduled_termination_date",
            "local_currency",
            "notional_amount",
            "machine_confidence",
            "auto_passed",
            "checked_at",
            "checker_comment",
            "created_at",
        ]
    )

    for result in validations:
        writer.writerow(
            [
                result.id,
                result.document_id,
                result.status,
                result.checker_decision,
                result.system_trade_id,
                result.party_a or "",
                result.party_b or "",
                result.trade_date or "",
                result.effective_date or "",
                result.scheduled_termination_date or "",
                result.local_currency or "",
                result.notional_amount or "",
                result.machine_confidence or "",
                result.auto_passed,
                result.checked_at or "",
                result.checker_comment or "",
                result.created_at,
            ]
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trs_validation_report.csv"},
    )


@router.get("/schema/trs")
async def get_trs_schema():
    return extractor.schema
