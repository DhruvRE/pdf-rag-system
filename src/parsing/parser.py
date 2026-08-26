"""
Phase 2 Parser: Raw Parsing Bench (text + layout data).
Extracts text along with bounding boxes, font metadata, and line structures per page,
writing pages.json under data/parsed/<class>/<subject>/<year>/<paper_id>/.
"""

import os
import json
import fitz
import re
from datetime import datetime, timezone
from src.segmentation.segmenter import is_english_dominant

from src.config import PROJECT_ROOT, CONTEXT_PATH


def _round_bbox(bbox: list[float]) -> list[float]:
    return [round(float(c), 2) for c in bbox]


def _union_bbox(bboxes: list[list[float]]) -> list[float]:
    return [
        min(b[0] for b in bboxes),
        min(b[1] for b in bboxes),
        max(b[2] for b in bboxes),
        max(b[3] for b in bboxes),
    ]


def _same_visual_row(group_bbox: list[float], line_bbox: list[float]) -> bool:
    group_height = max(1.0, group_bbox[3] - group_bbox[1])
    line_height = max(1.0, line_bbox[3] - line_bbox[1])
    group_mid = (group_bbox[1] + group_bbox[3]) / 2.0
    line_mid = (line_bbox[1] + line_bbox[3]) / 2.0
    overlap = max(0.0, min(group_bbox[3], line_bbox[3]) - max(group_bbox[1], line_bbox[1]))
    overlap_ratio = overlap / min(group_height, line_height)
    center_tol = max(3.0, min(group_height, line_height) * 0.35)
    return abs(group_mid - line_mid) <= center_tol or overlap_ratio >= 0.65


def _line_text_from_spans(spans: list[dict]) -> str:
    """Rebuilds a visual line left-to-right while preserving PDF math fragments."""
    ordered = sorted(spans, key=lambda s: (s["bbox"][0], s["bbox"][1]))
    text = ""
    prev_x1 = None
    for span in ordered:
        span_text = span.get("text", "")
        if not span_text:
            continue
        x0, _, x1, _ = span["bbox"]
        size = max(float(span.get("size") or 0.0), 1.0)
        if (
            prev_x1 is not None
            and x0 - prev_x1 > max(1.8, size * 0.25)
            and text
            and not text.endswith(" ")
            and not span_text.startswith((" ", ".", ",", ")", "]", "}", ":", ";"))
        ):
            text += " "
        text += span_text
        prev_x1 = max(prev_x1 if prev_x1 is not None else x1, x1)
    return re.sub(r"[ \t]+", " ", text).strip()


def _merge_visual_lines(raw_lines: list[dict]) -> list[dict]:
    """
    PyMuPDF often emits same-row math/text as separate logical lines. Merge only
    consecutive stream items that share a visual row, preserving the PDF stream
    order so raised matrix rows do not jump before their question number.
    """
    merged_lines = []
    current_group: list[dict] = []
    current_bbox: list[float] | None = None

    def flush_current() -> None:
        nonlocal current_group, current_bbox
        if not current_group:
            return
        spans = [span for entry in current_group for span in entry["spans"]]
        bboxes = [entry["bbox"] for entry in current_group]
        union = _union_bbox(bboxes)
        merged_lines.append({
            "bbox": _round_bbox(union),
            "text": _line_text_from_spans(spans),
            "spans": spans,
        })
        current_group = []
        current_bbox = None

    for line in raw_lines:
        if not line.get("text", "").strip():
            continue
        bbox = line["bbox"]
        if current_group and current_bbox and _same_visual_row(current_bbox, bbox):
            current_group.append(line)
            current_bbox = _union_bbox([current_bbox, bbox])
        else:
            flush_current()
            current_group = [line]
            current_bbox = bbox

    flush_current()
    return merged_lines


def _span_to_dict(span: dict) -> dict:
    chars = span.get("chars", [])

    # rawdict may not provide "text" directly.
    # Reconstruct it from individual character records.
    text = span.get("text", "")

    if not text and chars:
        text = "".join(
            str(char.get("c", ""))
            for char in chars
        )

    return {
        "text": text,

        "bbox": _round_bbox(
            list(span.get("bbox", [0, 0, 0, 0]))
        ),

        "font": span.get("font", ""),

        "size": round(
            span.get("size", 0.0),
            2
        ),

        "color": span.get("color", 0),

        "flags": span.get("flags", 0),

        # IMPORTANT:
        # Preserve individual PDF character/glyph information.
        "chars": [
            {
                "c": char.get("c", ""),
                "bbox": _round_bbox(
                    list(char.get("bbox", [0, 0, 0, 0]))
                ),
                "origin": char.get("origin"),
            }
            for char in chars
        ]
    }

def _line_to_entry(line: dict) -> dict:
    spans_data = [_span_to_dict(span) for span in line.get("spans", [])]
    return {
        "bbox": _round_bbox(list(line.get("bbox", [0, 0, 0, 0]))),
        "text": _line_text_from_spans(spans_data),
        "spans": spans_data
    }


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
            page_width = raw_dict.get("width", page.rect.width)
            page_height = raw_dict.get("height", page.rect.height)

            parsed_blocks = []
            for block_idx, block in enumerate(raw_dict.get("blocks", [])):
                # block type 0 = text, 1 = image
                b_type = "text" if block.get("type") == 0 else "image"
                b_bbox = list(block.get("bbox", [0, 0, 0, 0]))

                raw_lines_data = []
                if b_type == "text":
                    for line in block.get("lines", []):
                        raw_lines_data.append(_line_to_entry(line))

                lines_data = _merge_visual_lines(raw_lines_data) if b_type == "text" else []

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
    all_text = " ".join(
        line["text"]
        for page in parsed_dict["pages"]
        for block in page["blocks"]
        for line in block.get("lines", [])
    )
    if not is_english_dominant(all_text):
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
