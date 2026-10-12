"""
Phase 2 Parser: Raw Parsing Bench (text + layout data).
Extracts text along with bounding boxes, font metadata, and line structures per page,
writing pages.json under data/parsed/<class>/<subject>/<year>/<paper_id>/.
"""

import os
import json
import re
import io
try:
    import fitz
except ImportError:
    import pymupdf as fitz
from PIL import Image
from datetime import datetime, timezone
from src.segmentation.segmenter import is_english_dominant

from src.config import PROJECT_ROOT, CONTEXT_PATH


def spans_to_math_text(spans: list[dict]) -> str:
    """Preserve mathematical super/subscripts without changing question labels."""
    visible_spans = [span for span in spans if span.get("text", "").strip()]
    if not visible_spans:
        return "".join(span.get("text", "") for span in spans)

    max_size = max(float(span.get("size", 0)) for span in visible_spans)
    baseline_spans = [
        span for span in visible_spans
        if float(span.get("size", 0)) >= max_size * 0.92
    ]
    baseline_bottom = max(span["bbox"][3] for span in baseline_spans)
    result = []
    previous_visible = None

    for span in spans:
        text = span.get("text", "")
        if not text.strip():
            result.append(text)
            continue

        size = float(span.get("size", 0))
        x0, _, _, y1 = span.get("bbox", [0, 0, 0, 0])
        compact_math = bool(re.fullmatch(r"[0-9+\-−–=()]+", text.strip()))
        follows_math_base = bool(
            previous_visible
            and re.search(r"[A-Za-z0-9)]$", previous_visible.get("text", "").strip())
            and x0 - previous_visible["bbox"][2] <= 3
        )
        is_superscript = (
            compact_math
            and follows_math_base
            and size < max_size * 0.90
            and y1 < baseline_bottom - 2
        )

        result.append(f"^{{{text.strip()}}}" if is_superscript else text)
        previous_visible = span

    return "".join(result)


def _round_bbox(bbox: list) -> list:
    """Rounds coordinates of a bounding box [x0, y0, x1, y1] to 2 decimal places."""
    return [round(float(coord), 2) for coord in bbox] if bbox else [0.0, 0.0, 0.0, 0.0]


def get_or_download_tessdata(root_dir: str = PROJECT_ROOT) -> str:
    """Ensures tesseract language data exists and returns tessdata folder path."""
    tess_dir = os.path.join(root_dir, "data", "tessdata")
    os.makedirs(tess_dir, exist_ok=True)
    eng_path = os.path.join(tess_dir, "eng.traineddata")
    if not os.path.exists(eng_path) or os.path.getsize(eng_path) < 100000:
        import urllib.request
        url = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata"
        try:
            print(f"Downloading OCR model from {url} to {eng_path}...")
            urllib.request.urlretrieve(url, eng_path)
        except Exception as e:
            print(f"Warning: Failed to download eng.traineddata: {e}")
    return tess_dir


def is_page_two_column(page: fitz.Page) -> bool:
    """Heuristic to detect 2-column scanned pages (common in entrance test papers)."""
    try:
        import numpy as np
        pix = page.get_pixmap(dpi=72)
        samples = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        gray = samples[:, :, 0] if pix.n in (3, 4) else samples
        y_start, y_end = int(pix.height * 0.20), int(pix.height * 0.85)
        vert_proj = (gray[y_start:y_end, :] < 150).sum(axis=0)
        mid_start = int(pix.width * 0.46)
        mid_end = int(pix.width * 0.54)
        gutter_min = vert_proj[mid_start:mid_end].min()
        left_density = vert_proj[int(pix.width * 0.15):mid_start].mean()
        right_density = vert_proj[mid_end:int(pix.width * 0.85)].mean()
        return bool(left_density > 25 and right_density > 25 and gutter_min < 20)
    except Exception:
        return False


def ocr_page_layout(page: fitz.Page, tess_dir: str) -> list[dict]:
    """Runs high-resolution OCR with column awareness and returns parsed blocks."""
    w, h = page.rect.width, page.rect.height
    mid_x = w / 2.0
    is_2col = is_page_two_column(page)

    parsed_blocks = []

    def _extract_clip_blocks(clip_rect, offset_x=0.0, offset_y=0.0):
        try:
            pix = page.get_pixmap(dpi=150, clip=clip_rect)
            ocr_pdf = fitz.open("pdf", pix.pdfocr_tobytes(language="eng", tessdata=tess_dir))
            d = ocr_pdf[0].get_text("dict")
            for b in d.get("blocks", []):
                if b.get("type") == 0:
                    lines_data = []
                    b_bbox = [
                        round(b["bbox"][0] + offset_x, 2),
                        round(b["bbox"][1] + offset_y, 2),
                        round(b["bbox"][2] + offset_x, 2),
                        round(b["bbox"][3] + offset_y, 2)
                    ]
                    for line in b.get("lines", []):
                        l_bbox = [
                            round(line["bbox"][0] + offset_x, 2),
                            round(line["bbox"][1] + offset_y, 2),
                            round(line["bbox"][2] + offset_x, 2),
                            round(line["bbox"][3] + offset_y, 2)
                        ]
                        spans_data = []
                        line_text_parts = []
                        for span in line.get("spans", []):
                            s_text = span.get("text", "")
                            line_text_parts.append(s_text)
                            spans_data.append({
                                "text": s_text,
                                "bbox": [
                                    round(span["bbox"][0] + offset_x, 2),
                                    round(span["bbox"][1] + offset_y, 2),
                                    round(span["bbox"][2] + offset_x, 2),
                                    round(span["bbox"][3] + offset_y, 2)
                                ],
                                "font": span.get("font", ""),
                                "size": round(span.get("size", 10.0), 2),
                                "color": 0,
                                "flags": 0
                            })
                        full_line_text = spans_to_math_text(line.get("spans", []))
                        lines_data.append({
                            "bbox": l_bbox,
                            "text": full_line_text,
                            "spans": spans_data
                        })
                    parsed_blocks.append({
                        "block_id": len(parsed_blocks),
                        "type": "text",
                        "bbox": b_bbox,
                        "lines": lines_data
                    })
        except Exception as e:
            print(f"Warning: OCR clip extraction error on page {page.number+1}: {e}")

    if is_2col:
        # Left column (from y=30 to h-30)
        rect_l = fitz.Rect(15, 30, mid_x + 5, h - 30)
        _extract_clip_blocks(rect_l, rect_l.x0, rect_l.y0)
        # Right column (from y=30 to h-30)
        rect_r = fitz.Rect(mid_x - 5, 30, w - 15, h - 30)
        _extract_clip_blocks(rect_r, rect_r.x0, rect_r.y0)
    else:
        # Full page
        _extract_clip_blocks(page.rect, 0.0, 0.0)

    return parsed_blocks


def parse_pdf_layout(pdf_path: str) -> dict:
    """
    Parses PDF layout and text using PyMuPDF (fitz).
    Returns a structured dict with page dimensions, text blocks, lines, and bounding boxes.
    Automatically applies OCR when digital text is absent or insufficient (scanned PDFs).
    """

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found at {pdf_path}")

    doc = fitz.open(pdf_path)
    pages_data = []

    try:
        tess_dir = None
        for page_idx, page in enumerate(doc):

            raw_dict = page.get_text("dict")

            page_width = raw_dict.get(
                "width",
                page.rect.width
            )

            page_height = raw_dict.get(
                "height",
                page.rect.height
            )

            total_native_chars = sum(
                len(span.get("text", "").strip())
                for block in raw_dict.get("blocks", [])
                if block.get("type") == 0
                for line in block.get("lines", [])
                for span in line.get("spans", [])
            )

            # Check if this page is a scanned image without sufficient digital text layer
            if total_native_chars < 80:
                if tess_dir is None:
                    tess_dir = get_or_download_tessdata()
                parsed_blocks = ocr_page_layout(page, tess_dir)
            else:
                parsed_blocks = []
                for block_idx, block in enumerate(
                    raw_dict.get("blocks", [])
                ):

                    # block type 0 = text, 1 = image
                    b_type = (
                        "text"
                        if block.get("type") == 0
                        else "image"
                    )

                    b_bbox = list(
                        block.get(
                            "bbox",
                            [0, 0, 0, 0]
                        )
                    )

                    lines_data = []

                    if b_type == "text":

                        for line in block.get("lines", []):
                            l_bbox = list(line.get("bbox", [0, 0, 0, 0]))
                            spans_data = []
                            line_text_parts = []
                            for span in line.get("spans", []):
                                s_text = span.get("text", "")
                                line_text_parts.append(s_text)
                                spans_data.append({
                                    "text": s_text,
                                    "bbox": list(span.get("bbox", [0, 0, 0, 0])),
                                    "font": span.get("font", ""),
                                    "size": round(span.get("size", 0.0), 2),
                                    "color": span.get("color", 0),
                                    "flags": span.get("flags", 0)
                                })
                            lines_data.append({
                                "bbox": l_bbox,
                                "text": spans_to_math_text(line.get("spans", [])),
                                "spans": spans_data
                            })

                    parsed_blocks.append({
                        "block_id": block_idx,
                        "type": b_type,
                        "bbox": _round_bbox(b_bbox),
                        "lines": lines_data
                    })

            pages_data.append({
                "page_num": page_idx + 1,
                "width": round(page_width, 2),
                "height": round(page_height, 2),
                "blocks": parsed_blocks
            })

    finally:
        doc.close()

    return {
        "total_pages": len(pages_data),
        "pages": pages_data
    }

def parse_paper(paper_id: str, root_dir: str = PROJECT_ROOT) -> str:
    """
    Reads context.json to locate paper_id, runs layout parsing,
    saves pages.json into data/parsed/<class>/<subject>/<year>/<paper_id>/,
    and updates context.json status.
    """
    context_path = CONTEXT_PATH if root_dir == PROJECT_ROOT else os.path.join(root_dir, ".agent", "context.json")
    with open(context_path, 'r', encoding='utf-8') as f:

        ctx = json.load(f)

    if paper_id not in ctx["papers"]:
        raise KeyError(f"Paper ID {paper_id} not found in context.json")

    p_info = ctx["papers"][paper_id]
    cls = p_info["class"]
    subject = p_info["subject"]
    year = p_info["year"]
    pdf_rel_path = p_info["relative_path"]
    abs_pdf_path = os.path.join(root_dir, pdf_rel_path)

    parsed_dir = os.path.join(root_dir, "data", "parsed", cls, subject, year, paper_id)
    os.makedirs(parsed_dir, exist_ok=True)

    parsed_dict = parse_pdf_layout(abs_pdf_path)

    # --- English-only guard ---
    # Collect all text from the PDF to check language dominance.
    # Bilingual papers commonly contain an Indic private-font version followed
    # by an English version. Accept the paper when at least one page is usable;
    # Phase 3 selects only those English-dominant pages.
    has_english_page = any(
        is_english_dominant(" ".join(
            line["text"]
            for block in page["blocks"]
            for line in block.get("lines", [])
        ))
        for page in parsed_dict["pages"]
    )
    if not has_english_page:
        print(f"SKIPPED (non-English PDF): {paper_id} ({p_info['filename']})")
        p_info["phase_status"]["parse"] = "skipped_non_english"
        p_info["updated_at"] = datetime.now(timezone.utc).isoformat()
        ctx["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(context_path, 'w', encoding='utf-8') as f:
            json.dump(ctx, f, indent=2)
        return ""
    # --- End language guard ---

    parsed_dict["paper_id"] = paper_id
    parsed_dict["class"] = cls
    parsed_dict["subject"] = subject
    parsed_dict["year"] = year

    pages_json_path = os.path.join(parsed_dir, "pages.json")
    with open(pages_json_path, 'w', encoding='utf-8') as f:
        json.dump(parsed_dict, f, indent=2)

    # Update context.json status
    p_info["phase_status"]["parse"] = "done"
    p_info["updated_at"] = datetime.now(timezone.utc).isoformat()
    ctx["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(context_path, 'w', encoding='utf-8') as f:
        json.dump(ctx, f, indent=2)

    print(f"Parsed paper {paper_id} ({p_info['filename']}) -> {pages_json_path}")
    return pages_json_path
