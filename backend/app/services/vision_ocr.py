"""
macOS Vision Framework OCR Service
Extracts text with bounding box coordinates from documents
"""
import os
import io
import base64
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import fitz  # pymupdf


@dataclass
class OCRWord:
    """Represents a word with its bounding box"""
    text: str
    x: float  # Left position (0-1 normalized)
    y: float  # Top position (0-1 normalized)
    width: float  # Width (0-1 normalized)
    height: float  # Height (0-1 normalized)
    confidence: float


@dataclass
class OCRResult:
    """Result of OCR processing"""
    words: List[OCRWord]
    full_text: str
    image_width: int
    image_height: int
    image_base64: str  # Base64 encoded image for frontend display (optional)


def pdf_to_image(pdf_path: str, page_num: int = 0, dpi: int = 150) -> Tuple[bytes, int, int]:
    """
    Convert a PDF page to PNG image bytes using pymupdf
    Returns: (image_bytes, width, height)
    """
    doc = fitz.open(pdf_path)
    if page_num >= len(doc):
        page_num = 0

    page = doc[page_num]

    # Create a matrix for the desired DPI
    zoom = dpi / 72  # 72 is the default PDF DPI
    matrix = fitz.Matrix(zoom, zoom)

    # Render page to pixmap
    pixmap = page.get_pixmap(matrix=matrix)

    # Convert to PNG bytes
    image_bytes = pixmap.tobytes("png")

    doc.close()

    return image_bytes, pixmap.width, pixmap.height


def image_to_bytes(image_path: str) -> Tuple[bytes, int, int]:
    """
    Read an image file and return bytes with dimensions
    """
    import fitz

    # Use pymupdf to read the image and get dimensions
    doc = fitz.open(image_path)
    page = doc[0]
    pixmap = page.get_pixmap()
    image_bytes = pixmap.tobytes("png")

    doc.close()

    return image_bytes, pixmap.width, pixmap.height


def run_vision_ocr(image_bytes: bytes) -> List[OCRWord]:
    """
    Run macOS Vision framework OCR on image bytes
    Returns list of words with bounding boxes
    """
    import Vision
    import Quartz
    from Foundation import NSData

    # Create NSData from bytes
    ns_data = NSData.dataWithBytes_length_(image_bytes, len(image_bytes))

    # Create CGImage from data
    image_source = Quartz.CGImageSourceCreateWithData(ns_data, None)
    if not image_source:
        raise ValueError("Could not create image source from data")

    cg_image = Quartz.CGImageSourceCreateImageAtIndex(image_source, 0, None)
    if not cg_image:
        raise ValueError("Could not create CGImage from source")

    # Create Vision request handler
    request_handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
        cg_image, None
    )

    # Create text recognition request
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(True)

    # Perform the request
    success, error = request_handler.performRequests_error_([request], None)

    if not success:
        raise ValueError(f"Vision OCR failed: {error}")

    # Extract results
    words = []
    results = request.results()

    if results:
        for observation in results:
            # Get the top candidate
            candidates = observation.topCandidates_(1)
            if candidates:
                text = candidates[0].string()
                confidence = candidates[0].confidence()

                # Get bounding box (normalized coordinates, origin at bottom-left)
                bbox = observation.boundingBox()

                # Vision uses bottom-left origin, convert to top-left
                x = bbox.origin.x
                y = 1.0 - bbox.origin.y - bbox.size.height  # Flip Y coordinate
                width = bbox.size.width
                height = bbox.size.height

                # Split the observation text into individual words if needed
                # Vision often returns full lines, so we'll keep them as-is for matching
                words.append(OCRWord(
                    text=text,
                    x=x,
                    y=y,
                    width=width,
                    height=height,
                    confidence=confidence
                ))

    return words


def process_document(file_path: str, page_num: int = 0, include_image: bool = True) -> OCRResult:
    """
    Process a document (PDF or image) and return OCR results with bounding boxes
    """
    # Determine file type
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        image_bytes, width, height = pdf_to_image(file_path, page_num)
    elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
        image_bytes, width, height = image_to_bytes(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    # Run OCR
    words = run_vision_ocr(image_bytes)

    # Build full text
    full_text = "\n".join([w.text for w in words])

    # Encode image only when needed (viewer endpoints)
    image_base64 = base64.b64encode(image_bytes).decode('utf-8') if include_image else ""

    return OCRResult(
        words=words,
        full_text=full_text,
        image_width=width,
        image_height=height,
        image_base64=image_base64
    )


def match_value_to_boxes(
    value: str,
    ocr_words: List[OCRWord],
    fuzzy_threshold: float = 0.8
) -> Optional[Dict[str, Any]]:
    """
    Find the bounding box(es) that contain a specific value
    Returns the bounding box coordinates if found
    """
    from difflib import SequenceMatcher

    value_str = str(value).strip().lower()
    if not value_str:
        return None

    best_match = None
    best_score = 0

    for word in ocr_words:
        word_text = word.text.strip().lower()

        # Check for exact containment
        if value_str in word_text or word_text in value_str:
            score = 1.0 if value_str == word_text else 0.95
            if score > best_score:
                best_score = score
                best_match = word
        else:
            # Fuzzy matching
            ratio = SequenceMatcher(None, value_str, word_text).ratio()
            if ratio > fuzzy_threshold and ratio > best_score:
                best_score = ratio
                best_match = word

    if best_match:
        return {
            "x": best_match.x,
            "y": best_match.y,
            "width": best_match.width,
            "height": best_match.height,
            "matched_text": best_match.text,
            "confidence": best_score
        }

    return None


def get_field_coordinates(
    extracted_fields: Dict[str, Any],
    ocr_words: List[OCRWord]
) -> Dict[str, Dict[str, Any]]:
    """
    Match extracted field values to their bounding boxes in the document
    Returns a dict mapping field names to their coordinates
    """
    field_coordinates = {}

    for field_name, field_data in extracted_fields.items():
        # Handle both simple values and dict with value/confidence
        if isinstance(field_data, dict):
            value = field_data.get('value', '')
        else:
            value = field_data

        if value is not None and str(value).strip():
            coords = match_value_to_boxes(str(value), ocr_words)
            if coords:
                field_coordinates[field_name] = {
                    **coords,
                    "field_value": str(value)
                }

    return field_coordinates
