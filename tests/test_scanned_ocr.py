"""
Test suite for scanned / raster PDF layout parsing and OCR extraction.
Verifies that PDFs with no digital font layer are automatically detected and extracted via OCR.
"""

import os
import pytest
import fitz
from src.parsing.parser import parse_pdf_layout, get_or_download_tessdata, is_page_two_column


def test_tessdata_presence():
    """Verify that tesseract language data directory is resolved and eng.traineddata is accessible."""
    tess_dir = get_or_download_tessdata()
    assert os.path.exists(tess_dir), f"tess_dir does not exist: {tess_dir}"
    eng_model = os.path.join(tess_dir, "eng.traineddata")
    assert os.path.exists(eng_model), f"eng.traineddata missing at: {eng_model}"
    assert os.path.getsize(eng_model) > 1000000, "eng.traineddata file size is too small"


def test_scanned_pdf_layout_extraction():
    """Verify parse_pdf_layout on a scanned page PDF automatically triggers OCR."""
    pdf_sample = "C:/Users/shubh/.gemini/antigravity/brain/cc4b0a38-24bf-4d7d-9e6c-f810ff8a484b/.user_uploaded/media_1791823005942_70896f72.pdf"
    if not os.path.exists(pdf_sample):
        pytest.skip("Scanned PDF fixture not found in user uploaded directory")

    parsed = parse_pdf_layout(pdf_sample)
    assert parsed is not None
    assert parsed["total_pages"] >= 16

    # Verify that text blocks were extracted across pages
    total_lines = sum(
        len(block.get("lines", []))
        for page in parsed["pages"]
        for block in page.get("blocks", [])
        if block.get("type") == "text"
    )
    assert total_lines > 100, f"Expected > 100 extracted text lines from scanned PDF, got {total_lines}"

