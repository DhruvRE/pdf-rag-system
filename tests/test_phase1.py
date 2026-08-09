import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
import pytest
from src.scraper.sanity import validate_pdf

from src.config import PROJECT_ROOT, CONTEXT_PATH



def test_context_json_exists():
    """Verify that .agent/context.json exists and is valid JSON."""
    assert os.path.exists(CONTEXT_PATH), f"Context file missing at {CONTEXT_PATH}"
    with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert "schema_version" in data
    assert "papers" in data
    assert len(data["papers"]) >= 10, f"Expected at least 10 papers in context, found {len(data['papers'])}"


def test_phase1_pdf_storage_and_sanity():
    """Verify all scraped PDFs exist in data/raw_pdfs/, pass sanity checks, and context is correctly marked."""
    with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    papers = data["papers"]

    valid_classes = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"}
    valid_subjects = {"physics", "chemistry", "mathematics", "science", "biology"}
    year_regex = re.compile(r"^\d{4}-\d{4}$")

    image_heavy_count = 0

    for paper_id, p_info in papers.items():
        # Check metadata schema
        assert p_info["class"] in valid_classes, f"Invalid class {p_info['class']} for paper {paper_id}"
        assert p_info["subject"] in valid_subjects, f"Invalid subject {p_info['subject']} for paper {paper_id}"
        assert year_regex.match(p_info["year"]), f"Invalid year format {p_info['year']} for paper {paper_id}"
        assert p_info["phase_status"]["scrape"] == "done", f"Paper {paper_id} scrape status is not 'done'"

        # Verify physical file existence in data/raw_pdfs/<class>/<subject>/<year>/
        abs_path = os.path.join(PROJECT_ROOT, p_info["relative_path"])
        assert os.path.exists(abs_path), f"Raw PDF missing at {abs_path}"

        expected_dir = os.path.join(PROJECT_ROOT, "data", "raw_pdfs", p_info["class"], p_info["subject"], p_info["year"])
        assert os.path.dirname(abs_path) == expected_dir, f"PDF stored in wrong folder: {abs_path} vs {expected_dir}"

        # Run programmatic sanity check (open, check page count > 0, unencrypted)
        is_valid, err_msg, page_count = validate_pdf(abs_path)
        assert is_valid, f"PDF sanity check failed for {abs_path}: {err_msg}"
        assert page_count > 0, f"PDF {abs_path} has page_count <= 0"

        if p_info.get("has_images"):
            image_heavy_count += 1

    # Require at least 1 image-heavy paper fixture
    assert image_heavy_count >= 1, "Expected at least 1 image-heavy PDF paper fixture"


if __name__ == "__main__":
    test_context_json_exists()
    test_phase1_pdf_storage_and_sanity()
    print("All Phase 1 tests passed successfully!")
