import os
import aiofiles
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models import (
    FXTrade, FXTradeCreate,
    SwapTrade, SwapTradeCreate,
    Document, MatchingRule, ValidationResult,
    TextInput, TradeImport
)
from app.models.schemas import generate_id
from app.db import db
from app.services import extractor, comparison_engine
from app.config import settings
from datetime import datetime

router = APIRouter()


# ============== FX Trades ==============

@router.get("/trades/fx", response_model=List[FXTrade])
async def get_fx_trades():
    """Get all FX trades from the system."""
    return db.get_fx_trades()


@router.get("/trades/fx/{trade_id}", response_model=FXTrade)
async def get_fx_trade(trade_id: str):
    """Get a specific FX trade by ID."""
    trade = db.get_fx_trade(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="FX trade not found")
    return trade


@router.post("/trades/fx", response_model=FXTrade)
async def create_fx_trade(trade: FXTradeCreate):
    """Create a new FX trade."""
    return db.create_fx_trade(trade)


@router.put("/trades/fx/{trade_id}", response_model=FXTrade)
async def update_fx_trade(trade_id: str, trade: FXTradeCreate):
    """Update an existing FX trade."""
    updated = db.update_fx_trade(trade_id, trade)
    if not updated:
        raise HTTPException(status_code=404, detail="FX trade not found")
    return updated


@router.delete("/trades/fx/{trade_id}")
async def delete_fx_trade(trade_id: str):
    """Delete an FX trade."""
    if not db.delete_fx_trade(trade_id):
        raise HTTPException(status_code=404, detail="FX trade not found")
    return {"status": "deleted"}


# ============== Swap Trades ==============

@router.get("/trades/swap", response_model=List[SwapTrade])
async def get_swap_trades():
    """Get all Swap trades from the system."""
    return db.get_swap_trades()


@router.get("/trades/swap/{trade_id}", response_model=SwapTrade)
async def get_swap_trade(trade_id: str):
    """Get a specific Swap trade by ID."""
    trade = db.get_swap_trade(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Swap trade not found")
    return trade


@router.post("/trades/swap", response_model=SwapTrade)
async def create_swap_trade(trade: SwapTradeCreate):
    """Create a new Swap trade."""
    return db.create_swap_trade(trade)


@router.put("/trades/swap/{trade_id}", response_model=SwapTrade)
async def update_swap_trade(trade_id: str, trade: SwapTradeCreate):
    """Update an existing Swap trade."""
    updated = db.update_swap_trade(trade_id, trade)
    if not updated:
        raise HTTPException(status_code=404, detail="Swap trade not found")
    return updated


@router.delete("/trades/swap/{trade_id}")
async def delete_swap_trade(trade_id: str):
    """Delete a Swap trade."""
    if not db.delete_swap_trade(trade_id):
        raise HTTPException(status_code=404, detail="Swap trade not found")
    return {"status": "deleted"}


# ============== Trade Import/Export ==============

@router.post("/trades/import")
async def import_trades(data: TradeImport):
    """Import trades from JSON."""
    db.import_trades(data.fx_trades, data.swap_trades)
    return {"status": "imported", "fx_count": len(data.fx_trades), "swap_count": len(data.swap_trades)}


# ============== Documents ==============

@router.get("/documents", response_model=List[Document])
async def get_documents():
    """Get all uploaded documents."""
    return db.get_documents()


@router.post("/documents/upload", response_model=Document)
async def upload_document(file: UploadFile = File(...)):
    """Upload a document for processing."""
    # Validate file type
    allowed_extensions = [".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"File type not allowed: {ext}")

    # Check file size
    content = await file.read()
    if len(content) > settings.max_file_size:
        raise HTTPException(status_code=400, detail="File too large")

    # Determine file type
    if ext == ".pdf":
        file_type = "pdf"
    else:
        file_type = "image"

    # Save file
    doc_id = generate_id()
    file_path = os.path.join(settings.upload_dir, f"{doc_id}{ext}")

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Create document record
    doc = Document(
        id=doc_id,
        filename=file.filename,
        file_type=file_type,
        file_path=file_path,
        status="PENDING"
    )

    db.create_document(doc)
    return doc


@router.post("/documents/text", response_model=Document)
async def submit_text(text_input: TextInput):
    """Submit text content directly (e.g., pasted email)."""
    doc_id = generate_id()

    doc = Document(
        id=doc_id,
        filename=f"text_input_{doc_id[:8]}.txt",
        file_type="text",
        content=text_input.content,
        status="PENDING"
    )

    db.create_document(doc)
    return doc


@router.post("/documents/{doc_id}/extract", response_model=Document)
async def extract_document(doc_id: str):
    """Extract trade data from a document using LLM."""
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Update status to processing
    db.update_document(doc_id, {"status": "PROCESSING"})

    try:
        # Get content from document
        content = doc.content or ""

        if doc.file_type == "text":
            # Text content is already available
            pass
        elif doc.file_type == "pdf" and doc.file_path:
            # Extract text from PDF
            try:
                from pypdf import PdfReader
                reader = PdfReader(doc.file_path)
                content = "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception as e:
                print(f"PDF extraction failed: {e}")
                content = f"[PDF content from {doc.filename}]"
        elif doc.file_type == "image" and doc.file_path:
            # For images, we'll use the LLM's vision capabilities
            content = f"[Image content from {doc.filename}]"

        # Extract trade data using LLM
        extracted_data = await extractor.extract_trade_data(
            content=content,
            image_path=doc.file_path if doc.file_type == "image" else None
        )

        # Update document with extracted data
        updated_doc = db.update_document(doc_id, {
            "status": "EXTRACTED",
            "content": content,
            "extracted_data": extracted_data.model_dump()
        })

        return updated_doc
    except Exception as e:
        db.update_document(doc_id, {"status": "ERROR"})
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.get("/documents/{doc_id}/viewer")
async def get_document_viewer_data(doc_id: str, page: int = 0):
    """
    Get document image with OCR bounding boxes for the document viewer.
    Returns the document as a base64 image with field coordinates highlighted.
    """
    from app.services import vision_ocr

    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Only works for PDFs and images with file paths
    if not doc.file_path:
        raise HTTPException(status_code=400, detail="Document has no file for viewing")

    if doc.file_type == "text":
        raise HTTPException(status_code=400, detail="Text documents cannot be viewed as images")

    try:
        # Process document with Vision OCR
        ocr_result = vision_ocr.process_document(doc.file_path, page_num=page)

        # Get field coordinates if document has been extracted
        field_coordinates = {}
        if doc.extracted_data and doc.extracted_data.get("fields"):
            field_coordinates = vision_ocr.get_field_coordinates(
                doc.extracted_data["fields"],
                ocr_result.words
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
                    "text": w.text,
                    "x": w.x,
                    "y": w.y,
                    "width": w.width,
                    "height": w.height,
                    "confidence": w.confidence
                }
                for w in ocr_result.words
            ],
            "field_coordinates": field_coordinates,
            "extracted_data": doc.extracted_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@router.post("/documents/{doc_id}/validate", response_model=Document)
async def validate_document(doc_id: str):
    """Validate extracted document data against system records."""
    doc = db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not doc.extracted_data:
        raise HTTPException(status_code=400, detail="Document has not been extracted yet")

    try:
        from app.models import ExtractedTrade, ExtractedField

        # Reconstruct ExtractedTrade from stored dict
        extracted = ExtractedTrade(
            trade_type=doc.extracted_data.get("trade_type", "FX"),
            fields={
                k: ExtractedField(**v) if isinstance(v, dict) else ExtractedField(value=v, confidence=0.5)
                for k, v in doc.extracted_data.get("fields", {}).items()
            },
            raw_text=doc.extracted_data.get("raw_text")
        )

        # Load matching rules
        rules = db.get_matching_rules()
        comparison_engine.set_rules(rules)

        # Get system trades
        fx_trades = db.get_fx_trades()
        swap_trades = db.get_swap_trades()

        # Find best match and compare
        validation_result = comparison_engine.find_best_match(
            extracted=extracted,
            fx_trades=fx_trades,
            swap_trades=swap_trades,
            document_id=doc_id
        )

        if validation_result:
            db.create_validation_result(validation_result)

            updated_doc = db.update_document(doc_id, {
                "status": "VALIDATED",
                "validation_result": validation_result.model_dump()
            })
            return updated_doc
        else:
            updated_doc = db.update_document(doc_id, {
                "status": "ERROR",
                "validation_result": {
                    "id": generate_id(),
                    "document_id": doc_id,
                    "system_trade_id": "NOT_FOUND",
                    "status": "MISMATCH",
                    "field_comparisons": [],
                    "created_at": datetime.now().isoformat()
                }
            })
            return updated_doc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


# ============== Matching Rules ==============

@router.get("/rules", response_model=List[MatchingRule])
async def get_matching_rules():
    """Get all matching rules."""
    return db.get_matching_rules()


@router.put("/rules", response_model=List[MatchingRule])
async def save_matching_rules(rules: List[MatchingRule]):
    """Save matching rules."""
    return db.save_matching_rules(rules)


# ============== Validation Results ==============

@router.get("/validations", response_model=List[ValidationResult])
async def get_validation_results():
    """Get all validation results."""
    return db.get_validation_results()
