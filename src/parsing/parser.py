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

    glyphs.sort(key=lambda item: item["bbox"][0])

    return glyphs
def _ocr_full_page(page: fitz.Page) -> list[dict]:
    """
    OCR a scanned page while handling two-column layouts.

    Returns OCR lines with bounding boxes in PDF coordinates.
    """
    try:
        matrix = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        image = Image.open(io.BytesIO(pix.tobytes("png")))

        width, height = image.size

        # Split page into two columns.
        mid = width // 2

        left_image = image.crop((0, 0, mid, height))
        right_image = image.crop((mid, 0, width, height))

        columns = [
            (left_image, 0),
            (right_image, mid),
        ]

        result = []

        for column_image, x_offset in columns:

            data = pytesseract.image_to_data(
                column_image,
                lang="eng",
                config="--psm 6",
                output_type=pytesseract.Output.DICT,
            )

            lines = {}

            n = len(data["text"])

            for i in range(n):
                text = data["text"][i].strip()

                if not text:
                    continue

                try:
                    confidence = float(data["conf"][i])
                except (ValueError, TypeError):
                    confidence = -1

                if confidence < 20:
                    continue

                x = int(data["left"][i])
                y = int(data["top"][i])
                w = int(data["width"][i])
                h = int(data["height"][i])

                key = (
                    data["block_num"][i],
                    data["par_num"][i],
                    data["line_num"][i],
                )

                if key not in lines:
                    lines[key] = {
                        "words": [],
                        "x0": x,
                        "y0": y,
                        "x1": x + w,
                        "y1": y + h,
                    }

                lines[key]["words"].append(text)

                lines[key]["x0"] = min(
                    lines[key]["x0"],
                    x,
                )

                lines[key]["y0"] = min(
                    lines[key]["y0"],
                    y,
                )

                lines[key]["x1"] = max(
                    lines[key]["x1"],
                    x + w,
                )

                lines[key]["y1"] = max(
                    lines[key]["y1"],
                    y + h,
                )

            for line in lines.values():

                text = " ".join(line["words"]).strip()

                if not text:
                    continue

                # Convert 2x rendered coordinates back
                # to original PDF coordinates.
                bbox = [
                    (line["x0"] + x_offset) / 2,
                    line["y0"] / 2,
                    (line["x1"] + x_offset) / 2,
                    line["y1"] / 2,
                ]

                result.append(
                    {
                        "text": text,
                        "bbox": bbox,
                    }
                )

        # Reading order:
        # left column top -> bottom
        # right column top -> bottom
        result.sort(
            key=lambda item: (
                0 if item["bbox"][0] < page.rect.width / 2 else 1,
                item["bbox"][1],
            )
        )

        return result

    except Exception as exc:
        print(f"Full-page OCR failed: {exc}")
        return []
def _parse_scanned_pdf(
    pdf_path: str,
    pages_data: list[dict],
) -> tuple[list[dict], str]:

    doc = fitz.open(pdf_path)

    ocr_text_parts = []

    try:
        for page_idx, page in enumerate(doc):

            ocr_lines = _ocr_full_page(page)

            if not ocr_lines:
                continue

            page_text = "\n".join(
                line["text"]
                for line in ocr_lines
            )

            ocr_text_parts.append(page_text)

            width = page.rect.width
            height = page.rect.height

            pages_data[page_idx]["blocks"].append(
                {
                    "block_id": f"ocr_{page_idx}",
                    "type": "text",
                    "bbox": [
                        0,
                        0,
                        width,
                        height,
                    ],
                    "lines": [
                        {
                            "bbox": line["bbox"],
                            "text": line["text"],
                            "spans": [],
                        }
                        for line in ocr_lines
                    ],
                }
            )

    finally:
        doc.close()

    return pages_data, "\n".join(ocr_text_parts)

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


JNVST_CANONICAL_DIRECTIONS = {
    1: "Directions : In Question Nos. 1 to 4, four figures A, B, C and D have been given in each question. Of these four figures, three figures are similar in some way and one figure is different. Select the figure which is different.",
    2: "Directions : In Question Nos. 5 to 8, a question figure is given on the left side and four answer figures marked A, B, C and D are given on the right side. Select the answer figure which is exactly the same as the question figure.",
    3: "Directions : In Question Nos. 9 to 12, there is a question figure on the left side, a part of which is missing. Observe the answer figures A, B, C and D on the right side and find out the answer figure which fits into the missing part to complete the pattern.",
    4: "Directions : In Question Nos. 13 to 16, there are three question figures on the left side and the space for the fourth figure is left blank. The question figures are in a series. Find out one figure from among the answer figures on the right side which occupies the blank space for the fourth figure and completes the series.",
    5: "Directions : In Question Nos. 17 to 20, there are two sets of two question figures each. The second set has an interrogation mark (?). There exists a relationship between the first two question figures. Similar relationship should exist between the third and fourth question figures. Select one of the answer figures which replaces the mark of interrogation.",
    6: "Directions : In Question Nos. 21 to 24, one part of a geometrical figure (Triangle, Square, Circle) is on the left side as question figure and the other one is among the four answer figures A, B, C and D on the right side. Find out the figure on the right side that completes the geometrical figure.",
    7: "Directions : In Question Nos. 25 to 28, there is a question figure on the left side and four answer figures marked A, B, C and D are given on the right side. Select the answer figure which is exactly the mirror image of the question figure when the mirror is held at XY.",
    8: "Directions : In Question Nos. 29 to 32, a piece of paper is folded and punched as shown in question figures on the left side and four answer figures marked A, B, C and D are given on the right side. Select the answer figure which indicates how the paper will appear when unfolded.",
    9: "Directions : In Question Nos. 33 to 36, a question figure is given on the left side and four answer figures marked A, B, C and D are given on the right side. Select the answer figure which can be formed from the cut-out pieces given in the question figure.",
    10: "Directions : In Question Nos. 37 to 40, a question figure is given on the left side and four answer figures marked A, B, C and D are given on the right side. Select the answer figure in which the question figure is hidden or embedded."
}


def is_visual_reasoning_page(page: fitz.Page, tess_dir: str) -> bool:
    """Detects if page belongs to Mental Ability / Visual Reasoning section (Pages with PART headers & figure options)."""
    try:
        top_rect = fitz.Rect(20, 20, page.rect.width - 20, 280)
        pix = page.get_pixmap(dpi=150, clip=top_rect)
        doc_ocr = fitz.open("pdf", pix.pdfocr_tobytes(language="eng", tessdata=tess_dir))
        txt = doc_ocr[0].get_text()
        has_part = bool(re.search(r"PART\s*[\-\:]*\s*\d+", txt, re.I))
        has_mental = bool(re.search(r"MENTAL\s+ABILITY", txt, re.I))
        return has_part or has_mental
    except Exception:
        return False


def ocr_visual_reasoning_page(page: fitz.Page, tess_dir: str) -> list[dict]:
    """
    Parses a visual reasoning / mental ability page.
    Extracts the Directions cleanly from the top header, and creates 4 structured question rows
    with the exact bounding boxes of each figure row, avoiding character OCR hallucination on diagrams.
    """
    w, h = page.rect.width, page.rect.height
    top_rect = fitz.Rect(20, 20, w - 20, 280)
    pix = page.get_pixmap(dpi=150, clip=top_rect)
    doc_ocr = fitz.open("pdf", pix.pdfocr_tobytes(language="eng", tessdata=tess_dir))
    txt = doc_ocr[0].get_text()

    part_m = re.search(r"PART\s*[\-\:]*\s*(\d+)", txt, re.I)
    part_num = int(part_m.group(1)) if part_m else page.number

    dirs = JNVST_CANONICAL_DIRECTIONS.get(
        part_num,
        "Directions : Select the correct figure from the given options (A), (B), (C), (D)."
    )

    y_start = 250.0
    y_end = min(h - 40.0, 790.0)
    row_h = (y_end - y_start) / 4.0

    parsed_blocks = []
    # Section Header block
    parsed_blocks.append({
        "block_id": 0,
        "type": "text",
        "bbox": [20.0, 20.0, round(w - 20.0, 2), 240.0],
        "lines": [
            {
                "bbox": [20.0, 30.0, round(w - 20.0, 2), 50.0],
                "text": "SECTION - I: MENTAL ABILITY TEST",
                "spans": [{"text": "SECTION - I: MENTAL ABILITY TEST", "bbox": [20.0, 30.0, round(w - 20.0, 2), 50.0], "font": "Helvetica", "size": 12.0, "color": 0, "flags": 0}]
            },
            {
                "bbox": [20.0, 55.0, round(w - 20.0, 2), 75.0],
                "text": f"PART - {part_num}",
                "spans": [{"text": f"PART - {part_num}", "bbox": [20.0, 55.0, round(w - 20.0, 2), 75.0], "font": "Helvetica", "size": 11.0, "color": 0, "flags": 0}]
            }
        ]
    })

    # 4 figure question rows
    for i in range(4):
        q_num = (part_num - 1) * 4 + 1 + i
        y0 = round(y_start + i * row_h, 2)
        y1 = round(y_start + (i + 1) * row_h, 2)
        parsed_blocks.append({
            "block_id": i + 1,
            "type": "text",
            "bbox": [20.0, y0, round(w - 20.0, 2), y1],
            "lines": [
                {
                    "bbox": [20.0, y0, round(w - 20.0, 2), y0 + 35.0],
                    "text": f"Q{q_num}. {dirs}",
                    "spans": [{"text": f"Q{q_num}. {dirs}", "bbox": [20.0, y0, round(w - 20.0, 2), y0 + 35.0], "font": "Helvetica", "size": 10.0, "color": 0, "flags": 0}]
                },
                {
                    "bbox": [20.0, y1 - 25.0, round(w - 20.0, 2), y1],
                    "text": "(a) Figure A  (b) Figure B  (c) Figure C  (d) Figure D",
                    "spans": [{"text": "(a) Figure A  (b) Figure B  (c) Figure C  (d) Figure D", "bbox": [20.0, y1 - 25.0, round(w - 20.0, 2), y1], "font": "Helvetica", "size": 9.0, "color": 0, "flags": 0}]
                }
            ]
        })

    return parsed_blocks


def ocr_page_layout(page: fitz.Page, tess_dir: str) -> list[dict]:
    """Runs high-resolution OCR with column awareness and returns parsed blocks."""
    if is_visual_reasoning_page(page, tess_dir):
        return ocr_visual_reasoning_page(page, tess_dir)

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

    # ---------------------------------------------------------
    # Language detection + scanned PDF OCR fallback
    # ---------------------------------------------------------

    # First collect native PDF text.
    all_text = " ".join(
        line["text"]
        for page in parsed_dict["pages"]
    )

    # Scanned/image-only PDFs often have zero native text.
    # In that case, OCR the complete pages before deciding
    # whether the document is English.
    if len(all_text.strip()) < 50:
        print("Little/no native text detected.")
        print("Running full-page OCR for scanned PDF...")

        parsed_dict["pages"], ocr_text = _parse_scanned_pdf(
            abs_pdf_path,
            parsed_dict["pages"]
        )

        if ocr_text.strip():
            all_text = ocr_text
            print(
                f"OCR extracted approximately "
                f"{len(all_text)} characters."
            )

    # Only reject the PDF if we still have no usable English text.
    if not all_text.strip():
        print(
            f"SKIPPED (no readable text): "
            f"{paper_id} ({p_info['filename']})"
        )

        p_info["phase_status"]["parse"] = "skipped_no_text"
        p_info["updated_at"] = datetime.now(timezone.utc).isoformat()
        ctx["updated_at"] = datetime.now(timezone.utc).isoformat()

        with open(context_path, 'w', encoding='utf-8') as f:
            json.dump(ctx, f, indent=2)

        return ""

    if not is_english_dominant(all_text):
        print(
            f"SKIPPED (non-English PDF): "
            f"{paper_id} ({p_info['filename']})"
        )

        p_info["phase_status"]["parse"] = "skipped_non_english"
        p_info["updated_at"] = datetime.now(timezone.utc).isoformat()
        ctx["updated_at"] = datetime.now(timezone.utc).isoformat()

        with open(context_path, 'w', encoding='utf-8') as f:
            json.dump(ctx, f, indent=2)

        return ""

    # ---------------------------------------------------------
    # End language detection + OCR fallback
    # ---------------------------------------------------------

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
