"""
Test script to check Vision OCR output on a document.
Usage: python test_vision_ocr.py <path_to_pdf_or_image>
"""
import sys
import os

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.vision_ocr import process_document, OCRResult


def test_ocr(file_path: str):
    """Test OCR on a file and print results."""
    print(f"\n{'='*60}")
    print(f"Testing Vision OCR on: {file_path}")
    print(f"{'='*60}\n")

    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return

    try:
        result: OCRResult = process_document(file_path)

        print(f"Image dimensions: {result.image_width} x {result.image_height}")
        print(f"Number of text blocks detected: {len(result.words)}")
        print(f"\n{'='*60}")
        print("FULL TEXT EXTRACTED:")
        print(f"{'='*60}")
        print(result.full_text)

        print(f"\n{'='*60}")
        print("INDIVIDUAL TEXT BLOCKS WITH COORDINATES:")
        print(f"{'='*60}")
        for i, word in enumerate(result.words):
            print(f"\n[Block {i+1}]")
            print(f"  Text: {word.text[:100]}{'...' if len(word.text) > 100 else ''}")
            print(f"  Position: x={word.x:.3f}, y={word.y:.3f}")
            print(f"  Size: w={word.width:.3f}, h={word.height:.3f}")
            print(f"  Confidence: {word.confidence:.2%}")

        # Check image base64 size
        print(f"\n{'='*60}")
        print(f"Image base64 size: {len(result.image_base64)} characters")
        print(f"{'='*60}")

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_vision_ocr.py <path_to_pdf_or_image>")
        print("\nExample:")
        print("  python test_vision_ocr.py ../data/uploads/sample.pdf")
        sys.exit(1)

    test_ocr(sys.argv[1])
