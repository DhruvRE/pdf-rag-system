"""
Phase 4 Test Suite.
Verifies diagram image extraction, tiny glyph filtering, and spatial question linking.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from src.parsing.parser import parse_paper
from src.segmentation.segmenter import segment_paper
from src.image_linking.extractor import extract_and_link_images

from src.config import PROJECT_ROOT, CONTEXT_PATH



def test_phase4_image_linking():
    """Extracts images for image-heavy physics paper and verifies filtering and linking."""
    assert os.path.exists(CONTEXT_PATH), "Context file missing"

    with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
        ctx = json.load(f)

    target_pid = None
    for pid, p_info in ctx["papers"].items():
        if p_info["filename"] == "class12_physics_2024_2025_sqp.pdf":
            target_pid = pid
            break

    assert target_pid is not None, "Class 12 Physics paper not found in context"

    parse_paper(target_pid)
    segment_paper(target_pid)
    q_data = extract_and_link_images(target_pid)

    # Check questions with linked images
    qs_with_images = [q for q in q_data["questions"] if "images" in q and len(q["images"]) > 0]
    assert len(qs_with_images) > 0, "Expected at least 1 question with linked diagram images"

    p_info = ctx["papers"][target_pid]
    cls = p_info["class"]
    subject = p_info["subject"]
    year = p_info["year"]
    parsed_dir = os.path.join(PROJECT_ROOT, "data", "parsed", cls, subject, year, target_pid)

    for q in qs_with_images:
        for img_info in q["images"]:
            rel_path = img_info["relative_path"]
            abs_path = os.path.join(parsed_dir, rel_path)
            assert os.path.exists(abs_path), f"Linked image file missing at {abs_path}"

            # Verify size filtering (no tiny < 35px glyphs)
            w = img_info["width"]
            h = img_info["height"]
            assert w >= 35.0, f"Linked image {abs_path} width {w} < 35.0px"
            assert h >= 35.0, f"Linked image {abs_path} height {h} < 35.0px"

    # Context status check
    with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
        updated_ctx = json.load(f)

    assert updated_ctx["papers"][target_pid]["phase_status"]["image_link"] == "done"


if __name__ == "__main__":
    test_phase4_image_linking()
    print("All Phase 4 image linking tests passed successfully!")
