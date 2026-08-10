"""
Phase 5 Test Suite.
Verifies 1-to-1 question chunking, metadata completeness, and chunk boundary isolation across all papers.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
import pytest
from src.parsing.parser import parse_paper
from src.segmentation.segmenter import segment_paper
from src.image_linking.extractor import extract_and_link_images
from src.chunking.chunker import chunk_paper

from src.config import PROJECT_ROOT, CONTEXT_PATH


Q_NUM_EXTRACTOR = re.compile(r"^\s*(?:<b>)?\s*(?:Q\.?\s*(\d{1,3})[\.\:]|Question\s+(\d{1,3})[\.\:])", re.IGNORECASE)


def test_phase5_question_chunking():
    """Generates chunks across all papers and verifies 1-to-1 question mapping and metadata."""
    assert os.path.exists(CONTEXT_PATH), "Context file missing"

    with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
        ctx = json.load(f)

    for paper_id, p_info in ctx["papers"].items():
        parse_paper(paper_id)
        segment_paper(paper_id)
        extract_and_link_images(paper_id)
        chunks_json_path = chunk_paper(paper_id)

        assert os.path.exists(chunks_json_path), f"chunks.json missing at {chunks_json_path}"

        with open(chunks_json_path, 'r', encoding='utf-8') as f:
            c_data = json.load(f)

        cls = p_info["class"]
        subject = p_info["subject"]
        year = p_info["year"]
        parsed_dir = os.path.join(PROJECT_ROOT, "data", "parsed", cls, subject, year, paper_id)
        q_path = os.path.join(parsed_dir, "questions.json")

        with open(q_path, 'r', encoding='utf-8') as f:
            q_data = json.load(f)

        chunks = c_data["chunks"]
        questions = [q for q in q_data["questions"] if q.get("is_valid", True)]

        # Enforce 1 chunk = 1 question rule
        assert len(chunks) == len(questions), (
            f"Chunk count mismatch for paper {paper_id}: got {len(chunks)} chunks, expected {len(questions)} valid questions"
        )

        for idx, chunk in enumerate(chunks):
            expected_q = questions[idx]
            assert chunk["question_id"] == expected_q["question_id"]
            assert chunk["paper_id"] == paper_id
            assert chunk["class"] == cls
            assert chunk["subject"] == subject
            assert chunk["year"] == year
            assert "difficulty" in chunk
            assert len(chunk["content"]) > 0

            # Verify chunk does not contain a DIFFERENT question's header
            lines = chunk["raw_text"].split("\n")
            q_nums_in_chunk = set()
            for line in lines:
                m = Q_NUM_EXTRACTOR.search(line)
                if m:
                    num_str = [g for g in m.groups() if g is not None][0]
                    q_nums_in_chunk.add(int(num_str))

            assert len(q_nums_in_chunk) <= 1, (
                f"Chunk {chunk['chunk_id']} contains headers from multiple different questions: {q_nums_in_chunk}"
            )

        # Check context phase_status
        with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
            updated_ctx = json.load(f)

        assert updated_ctx["papers"][paper_id]["phase_status"]["chunk"] == "done"


if __name__ == "__main__":
    test_phase5_question_chunking()
    print("All Phase 5 chunking tests passed successfully across all papers!")
