"""
Stage 0 & Stage 1: PDF Type Detection & Unified Markdown Extraction.
Handles:
1. Stage 0: Type Detection (native vs scanned) via PyMuPDF text character density heuristic.
2. Stage 1: Native branch structured extraction (spans, font sizes, bold flags, bboxes) and conversion to unified markdown format.
"""

import os
import fitz
import re


def detect_pdf_type(pdf_path: str) -> str:
    """
    Stage 0: Inspects the PDF file to determine whether it is native or scanned.
    Native PDFs have embedded text streams (avg_chars_per_page > 200).
    Scanned PDFs contain mostly bitmap images (avg_chars_per_page <= 200).
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at {pdf_path}")

    doc = fitz.open(pdf_path)
    try:
        sample_pages = doc[:min(3, len(doc))]
        if not sample_pages:
            return "scanned"
        
        text_chars = sum(len(p.get_text().strip()) for p in sample_pages)
        avg_chars_per_page = text_chars / max(len(sample_pages), 1)
        return "native" if avg_chars_per_page > 200 else "scanned"
    finally:
        doc.close()


def extract_native_structure(pdf_path: str) -> list[dict]:
    """
    Stage 1: Extracts text spans with position, font size, bold flag, and bbox metadata for native PDFs.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at {pdf_path}")

    doc = fitz.open(pdf_path)
    blocks = []
    try:
        for page_num, page in enumerate(doc):
            raw_dict = page.get_text("dict")
            for block_idx, block in enumerate(raw_dict.get("blocks", [])):
                if block.get("type") != 0 or "lines" not in block:
                    continue
                for line_idx, line in enumerate(block["lines"]):
                    for span_idx, span in enumerate(line.get("spans", [])):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        flags = span.get("flags", 0)
                        font_name = span.get("font", "").lower()
                        is_bold = bool(flags & 2**4) or "bold" in font_name or "heavy" in font_name
                        blocks.append({
                            "page": page_num + 1,
                            "block_id": block_idx,
                            "line_id": line_idx,
                            "span_id": span_idx,
                            "text": span.get("text", ""),
                            "size": round(span.get("size", 0.0), 2),
                            "bold": is_bold,
                            "font": span.get("font", ""),
                            "bbox": [round(c, 2) for c in span.get("bbox", [0, 0, 0, 0])]
                        })
    finally:
        doc.close()
    return blocks


def generate_unified_markdown(pdf_path: str) -> dict:
    """
    Stage 1: Generates unified Markdown string and block manifest from PDF layout.
    Works for both native and scanned (via OCR fallback) PDFs.
    """
    pdf_type = detect_pdf_type(pdf_path)
    doc = fitz.open(pdf_path)

    markdown_lines = []
    page_manifest = []

    try:
        for page_idx, page in enumerate(doc):
            page_num = page_idx + 1
            page_text = page.get_text("text")

            # Fallback to OCR if scanned or page text is sparse
            if pdf_type == "scanned" or len(page_text.strip()) < 50:
                try:
                    textpage = page.get_textpage_ocr()
                    page_text = textpage.extractText()
                except Exception:
                    pass

            lines = [l.strip() for l in page_text.split("\n") if l.strip()]
            formatted_page_lines = []

            for line in lines:
                # Detect section headers
                if re.match(r"^(SECTION\s*[A-E]|Section\s*[A-E]|PART\s*[A-E])", line, re.IGNORECASE):
                    formatted_page_lines.append(f"\n# {line}\n")
                # Detect question headers
                elif re.match(r"^(Q\.?\s*\d+|\d+\.)", line):
                    formatted_page_lines.append(f"\n## {line}")
                else:
                    formatted_page_lines.append(line)

            page_md = "\n".join(formatted_page_lines)
            markdown_lines.append(f"<!-- PAGE {page_num} START -->\n{page_md}\n<!-- PAGE {page_num} END -->")
            page_manifest.append({
                "page_num": page_num,
                "text_length": len(page_md),
                "char_count": len(page_text)
            })

    finally:
        doc.close()

    return {
        "pdf_type": pdf_type,
        "total_pages": len(page_manifest),
        "markdown": "\n\n".join(markdown_lines),
        "pages": page_manifest
    }
