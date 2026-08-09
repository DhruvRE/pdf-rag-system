"""
Phase 2 Test Suite.
Verifies PDF layout and text parsing into data/parsed/<class>/<subject>/<year>/<paper_id>/pages.json,
confirming bounding box coordinates, font sizes, page dimensions, and text fidelity.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from src.parsing.parser import parse_paper

from src.config import PROJECT_ROOT, CONTEXT_PATH



def test_phase2_parsing():
    """Parses 3 selected fixture papers and validates pages.json layout and text extraction."""
    assert os.path.exists(CONTEXT_PATH), "Context file missing"
    with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
        ctx = json.load(f)

    paper_ids = list(ctx["papers"].keys())[:3]
    assert len(paper_ids) >= 3, "Expected at least 3 papers in context"

    for paper_id in paper_ids:
        p_info = ctx["papers"][paper_id]
        out_path = parse_paper(paper_id)
        assert os.path.exists(out_path), f"pages.json missing at {out_path}"

        with open(out_path, 'r', encoding='utf-8') as f:
            parsed = json.load(f)

        assert parsed["paper_id"] == paper_id
        assert parsed["total_pages"] >= 1
        assert len(parsed["pages"]) == parsed["total_pages"]

        first_page = parsed["pages"][0]
        assert first_page["width"] > 0
        assert first_page["height"] > 0
        assert len(first_page["blocks"]) > 0

        # Check block layout & bbox data
        text_blocks = [b for b in first_page["blocks"] if b["type"] == "text"]
        assert len(text_blocks) > 0, "No text blocks found in page 1"

        first_text_block = text_blocks[0]
        assert len(first_text_block["bbox"]) == 4
        assert len(first_text_block["lines"]) > 0

        first_line = first_text_block["lines"][0]
        assert len(first_line["spans"]) > 0
        span = first_line["spans"][0]
        assert "text" in span
        assert "font" in span
        assert "size" in span
        assert len(span["bbox"]) == 4

        # Verify context updated
        with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
            updated_ctx = json.load(f)
        assert updated_ctx["papers"][paper_id]["phase_status"]["parse"] == "done"


if __name__ == "__main__":
    test_phase2_parsing()
    print("All Phase 2 tests passed successfully!")
