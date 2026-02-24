from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pypdf import PdfReader

from app.models import Document
from . import vision_ocr

try:
    import extract_msg  # type: ignore
except Exception:  # pragma: no cover - optional dependency in local dev
    extract_msg = None

try:
    from docx import Document as DocxFile  # type: ignore
except Exception:  # pragma: no cover - optional dependency in local dev
    DocxFile = None


SUPPORTED_ATTACHMENT_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg", ".gif", ".bmp"}


@dataclass
class NormalizedEvidence:
    """Canonical evidence payload passed to the extraction service."""

    content: str
    image_path: Optional[str]
    metadata: Dict[str, Any]


class EvidenceProcessor:
    """
    Normalizes raw evidence into text for extraction.

    Supported input types:
    - text (manual input)
    - pdf
    - docx
    - image
    - msg (Outlook email with supported attachments)
    """

    def __init__(self, min_pdf_text_length: int = 80, max_pdf_ocr_pages: int = 3):
        self.min_pdf_text_length = min_pdf_text_length
        self.max_pdf_ocr_pages = max_pdf_ocr_pages

    def prepare_document_content(self, doc: Document) -> NormalizedEvidence:
        if doc.file_type == "text":
            content = (doc.content or "").strip()
            return NormalizedEvidence(
                content=content,
                image_path=None,
                metadata={"source_type": "text", "has_content": bool(content), "warnings": []},
            )

        if not doc.file_path:
            raise ValueError("Document has no file path")

        if doc.file_type == "image":
            return self._prepare_image_evidence(doc.file_path)

        if doc.file_type == "pdf":
            return self._prepare_pdf_evidence(doc.file_path)

        if doc.file_type == "docx":
            return self._prepare_docx_evidence(doc.file_path)

        if doc.file_type == "msg":
            return self._prepare_msg_evidence(doc.file_path, doc.id)

        raise ValueError(f"Unsupported file type: {doc.file_type}")

    def _prepare_msg_evidence(self, file_path: str, doc_id: str) -> NormalizedEvidence:
        if extract_msg is None:
            raise ValueError("MSG processing requires 'extract-msg'. Add extract-msg to backend dependencies.")

        warnings: List[str] = []
        message = extract_msg.Message(file_path)

        subject = (message.subject or "").strip()
        sender = (message.sender or "").strip()
        body = self._clean_text((message.body or "").strip())

        attachment_text_parts: List[str] = []
        attachment_metadata: List[Dict[str, Any]] = []
        first_image_path: Optional[str] = None

        attachment_dir = os.path.join(os.path.dirname(file_path), f"{doc_id}_attachments")
        os.makedirs(attachment_dir, exist_ok=True)

        for index, attachment in enumerate(message.attachments):
            filename = self._safe_attachment_name(
                attachment.longFilename
                or attachment.shortFilename
                or f"attachment_{index}"
            )
            ext = os.path.splitext(filename)[1].lower()

            if ext == ".zip":
                warnings.append(f"Ignored zip attachment: {filename}")
                continue

            if ext not in SUPPORTED_ATTACHMENT_EXTENSIONS:
                warnings.append(f"Ignored unsupported attachment type: {filename}")
                continue

            attachment_path = os.path.join(attachment_dir, f"{index}_{filename}")

            try:
                with open(attachment_path, "wb") as output_file:
                    output_file.write(attachment.data)
            except Exception as exc:
                warnings.append(f"Failed to save attachment {filename}: {exc}")
                continue

            extracted_text, item_meta = self._extract_attachment_text(attachment_path)
            item_meta["attachment_name"] = filename
            attachment_metadata.append(item_meta)

            if extracted_text.strip():
                attachment_text_parts.append(f"[Attachment: {filename}]\n{extracted_text.strip()}")

            if item_meta.get("source_type") == "image" and not first_image_path:
                first_image_path = attachment_path

        email_header_block = "\n".join(
            line for line in [
                f"Subject: {subject}" if subject else "",
                f"From: {sender}" if sender else "",
                "[Email Body]",
                body,
            ]
            if line
        )

        combined_parts = [email_header_block] if email_header_block else []
        combined_parts.extend(attachment_text_parts)
        combined_content = "\n\n".join(part for part in combined_parts if part)

        if not combined_content.strip():
            combined_content = "[MSG evidence: no extractable content]"

        return NormalizedEvidence(
            content=combined_content,
            image_path=first_image_path,
            metadata={
                "source_type": "msg",
                "subject": subject,
                "sender": sender,
                "attachments_processed": len(attachment_metadata),
                "attachments": attachment_metadata,
                "warnings": warnings,
            },
        )

    def _extract_attachment_text(self, attachment_path: str) -> Tuple[str, Dict[str, Any]]:
        ext = os.path.splitext(attachment_path)[1].lower()

        if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp"}:
            image_evidence = self._prepare_image_evidence(attachment_path)
            return image_evidence.content, {
                "source_type": "image",
                "ocr_text_length": image_evidence.metadata.get("ocr_text_length", 0),
                "warnings": image_evidence.metadata.get("warnings", []),
            }

        if ext == ".pdf":
            pdf_evidence = self._prepare_pdf_evidence(attachment_path)
            return pdf_evidence.content, {
                "source_type": "pdf",
                "pdf_text_length": pdf_evidence.metadata.get("pdf_text_length", 0),
                "ocr_used": pdf_evidence.metadata.get("ocr_used", False),
                "ocr_text_length": pdf_evidence.metadata.get("ocr_text_length", 0),
                "warnings": pdf_evidence.metadata.get("warnings", []),
            }

        if ext == ".docx":
            docx_evidence = self._prepare_docx_evidence(attachment_path)
            return docx_evidence.content, {
                "source_type": "docx",
                "docx_text_length": len(docx_evidence.content),
                "warnings": docx_evidence.metadata.get("warnings", []),
            }

        return "", {"source_type": "unknown", "warnings": [f"Unsupported attachment extension: {ext}"]}

    def _prepare_image_evidence(self, file_path: str) -> NormalizedEvidence:
        warnings: List[str] = []
        ocr_text = ""
        try:
            ocr_result = vision_ocr.process_document(file_path, include_image=False)
            ocr_text = ocr_result.full_text.strip()
        except Exception as exc:
            warnings.append(f"Image OCR failed: {exc}")

        content = ocr_text or "[Image evidence: OCR text unavailable]"
        return NormalizedEvidence(
            content=content,
            image_path=file_path,
            metadata={
                "source_type": "image",
                "ocr_used": True,
                "ocr_text_length": len(ocr_text),
                "warnings": warnings,
            },
        )

    def _prepare_pdf_evidence(self, file_path: str) -> NormalizedEvidence:
        warnings: List[str] = []
        extracted_text = self._extract_pdf_text(file_path)
        needs_ocr = len(extracted_text.strip()) < self.min_pdf_text_length

        ocr_text = ""
        ocr_pages = 0
        if needs_ocr:
            ocr_text, ocr_pages = self._extract_pdf_ocr_text(file_path)
            if not ocr_text.strip():
                warnings.append("PDF OCR fallback produced no text")

        content = self._combine_text(extracted_text, ocr_text)
        if not content:
            content = "[PDF evidence: no extractable text]"

        return NormalizedEvidence(
            content=content,
            image_path=None,
            metadata={
                "source_type": "pdf",
                "pdf_text_length": len(extracted_text),
                "ocr_used": needs_ocr,
                "ocr_pages_processed": ocr_pages,
                "ocr_text_length": len(ocr_text),
                "warnings": warnings,
            },
        )

    def _prepare_docx_evidence(self, file_path: str) -> NormalizedEvidence:
        warnings: List[str] = []

        if DocxFile is None:
            raise ValueError("DOCX processing requires 'python-docx'. Add python-docx to backend dependencies.")

        text_parts: List[str] = []
        try:
            doc = DocxFile(file_path)
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    text_parts.append(text)

            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                    if row_text:
                        text_parts.append(row_text)
        except Exception as exc:
            warnings.append(f"DOCX extraction failed: {exc}")

        content = "\n".join(text_parts).strip() or "[DOCX evidence: no extractable text]"
        return NormalizedEvidence(
            content=content,
            image_path=None,
            metadata={"source_type": "docx", "warnings": warnings},
        )

    def _extract_pdf_text(self, file_path: str) -> str:
        try:
            reader = PdfReader(file_path)
            text_parts = [(page.extract_text() or "").strip() for page in reader.pages]
            return "\n".join(part for part in text_parts if part)
        except Exception as exc:
            print(f"PDF text extraction failed for {file_path}: {exc}")
            return ""

    def _extract_pdf_ocr_text(self, file_path: str) -> Tuple[str, int]:
        try:
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
        except Exception as exc:
            print(f"Could not determine PDF page count for OCR: {exc}")
            return "", 0

        max_pages = min(page_count, self.max_pdf_ocr_pages)
        text_parts: List[str] = []

        for page_num in range(max_pages):
            try:
                ocr_result = vision_ocr.process_document(file_path, page_num=page_num, include_image=False)
                if ocr_result.full_text.strip():
                    text_parts.append(ocr_result.full_text.strip())
            except Exception as exc:
                print(f"PDF OCR failed for page {page_num} in {file_path}: {exc}")

        return "\n".join(text_parts), max_pages

    def _combine_text(self, pdf_text: str, ocr_text: str) -> str:
        pdf_clean = pdf_text.strip()
        ocr_clean = ocr_text.strip()

        if pdf_clean and ocr_clean:
            return f"{pdf_clean}\n\n[OCR FALLBACK]\n{ocr_clean}"
        return pdf_clean or ocr_clean

    def _clean_text(self, content: str) -> str:
        # If we receive HTML body text, strip tags as best-effort fallback.
        if "<" in content and ">" in content:
            no_tags = re.sub(r"<[^>]+>", " ", content)
            return re.sub(r"\s+", " ", no_tags).strip()
        return content

    def _safe_attachment_name(self, name: str) -> str:
        safe = Path(name).name
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", safe)
        return safe or "attachment.bin"


evidence_processor = EvidenceProcessor()
