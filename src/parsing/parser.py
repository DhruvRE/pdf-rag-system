"""
Phase 2 Parser: Raw Parsing Bench (text + layout data).
Extracts text along with bounding boxes, font metadata, and line structures per page,
writing pages.json under data/parsed/<class>/<subject>/<year>/<paper_id>/.
"""

import os
import json
import fitz
from datetime import datetime, timezone
from src.segmentation.segmenter import is_english_dominant

from src.config import PROJECT_ROOT, CONTEXT_PATH



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
            raw_dict = page.get_text("dict")
            page_width = raw_dict.get("width", page.rect.width)
            page_height = raw_dict.get("height", page.rect.height)

            parsed_blocks = []
            for block_idx, block in enumerate(raw_dict.get("blocks", [])):
                # block type 0 = text, 1 = image
                b_type = "text" if block.get("type") == 0 else "image"
                b_bbox = list(block.get("bbox", [0, 0, 0, 0]))

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
                            "text": "".join(line_text_parts),
                            "spans": spans_data
                        })

                parsed_blocks.append({
                    "block_id": block_idx,
                    "type": b_type,
                    "bbox": b_bbox,
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
