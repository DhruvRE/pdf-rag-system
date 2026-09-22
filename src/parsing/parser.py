"""
Phase 2 Parser: Raw Parsing Bench (text + layout data).
Extracts text along with bounding boxes, font metadata, and line structures per page,
writing pages.json under data/parsed/<class>/<subject>/<year>/<paper_id>/.
"""

import os
import json
import re
import fitz
import re
import io
import pytesseract
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

def parse_pdf_layout(pdf_path: str) -> dict:
    """
    Parses PDF layout and text using PyMuPDF (fitz).
    Returns a structured dict with page dimensions, text blocks, lines, and bounding boxes.
    """

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found at {pdf_path}")

    doc = fitz.open(pdf_path)
    pages_data = []

    try:
        for page_idx, page in enumerate(doc):

            raw_dict = page.get_text("rawdict")

            page_width = raw_dict.get(
                "width",
                page.rect.width
            )

            page_height = raw_dict.get(
                "height",
                page.rect.height
            )

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

                raw_lines_data = []

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
