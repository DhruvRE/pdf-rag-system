"""
Phase 3 Test Suite.
Verifies question-boundary detection and segmentation accuracy across benchmark papers
with strict uniqueness and exact question count assertions.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from src.parsing.parser import parse_paper
from src.segmentation.segmenter import segment_paper

from src.config import PROJECT_ROOT, CONTEXT_PATH
GROUND_TRUTH_PATH = os.path.join(PROJECT_ROOT, "tests", "labeled", "ground_truth.json")



def test_phase3_multi_subject_segmentation():
    """Segments benchmark papers and asserts exact count, uniqueness, and bounding box validity."""
    assert os.path.exists(CONTEXT_PATH), "Context file missing"
    assert os.path.exists(GROUND_TRUTH_PATH), "Ground truth file missing"

    with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
        ctx = json.load(f)

    with open(GROUND_TRUTH_PATH, 'r', encoding='utf-8') as f:
        gt_data = json.load(f)

    for bench in gt_data["benchmark_papers"]:
        fname = bench["filename"]
        exp_total = bench["expected_total_questions"]
        exp_unique = bench["expected_unique_question_ids"]
        forbid_dups = bench.get("forbid_duplicate_ids", True)

        target_pid = None
        for pid, p_info in ctx["papers"].items():
            if p_info["filename"] == fname:
                target_pid = pid
                break

        assert target_pid is not None, f"Paper {fname} not found in context"

        # Execute Phase 2 -> Phase 3 pipeline for target paper
        parse_paper(target_pid)
        questions_json_path = segment_paper(target_pid)

        assert os.path.exists(questions_json_path), f"questions.json missing at {questions_json_path}"

        with open(questions_json_path, 'r', encoding='utf-8') as f:
            seg_data = json.load(f)

        questions = seg_data["questions"]
        detected_ids = [q["question_id"] for q in questions]
        unique_ids = set(detected_ids)

        # 1. Hard Uniqueness Assertion
        if forbid_dups:
            duplicates = [q_id for q_id in set(detected_ids) if detected_ids.count(q_id) > 1]
            assert len(detected_ids) == len(unique_ids), (
                f"Duplicate question_ids found in {fname}: {duplicates}"
            )

        # 2. Total Count Sanity Check against paper instructions
        assert len(questions) == exp_total, (
            f"Question count mismatch for {fname}: got {len(questions)}, expected {exp_total}"
        )

        # 3. Unique ID Count Check
        assert len(unique_ids) == exp_unique, (
            f"Unique ID count mismatch for {fname}: got {len(unique_ids)}, expected {exp_unique}"
        )

        # 4. Bounding box validity check
        for q in questions:
            bbox = q["bounding_box"]
            assert len(bbox) == 4
            assert bbox[0] < bbox[2], f"Invalid x-coords in bbox {bbox} for question {q['question_id']}"
            assert bbox[1] < bbox[3], f"Invalid y-coords in bbox {bbox} for question {q['question_id']}"

        # 5. Context state check
        with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
            updated_ctx = json.load(f)
        assert updated_ctx["papers"][target_pid]["phase_status"]["segment"] == "done"


if __name__ == "__main__":
    test_phase3_multi_subject_segmentation()
    print("All Phase 3 tests passed with ZERO duplicate IDs and 100% exact count matching!")
