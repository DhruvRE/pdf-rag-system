"""
Phase 7 Test Suite.
Verifies pairwise vector duplicate & near-duplicate question detection across board papers.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from src.parsing.parser import parse_paper
from src.segmentation.segmenter import segment_paper
from src.image_linking.extractor import extract_and_link_images
from src.chunking.chunker import chunk_paper
from src.embedding.embedder import embed_paper_chunks, get_vector_store
from src.dedup.deduplicator import run_deduplication, find_duplicate_questions

from src.config import PROJECT_ROOT, CONTEXT_PATH



def test_phase7_duplicate_detection():
    """Seeds a known duplicate chunk, runs deduplication scan, and asserts detection."""
    assert os.path.exists(CONTEXT_PATH), "Context file missing"

    with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
        ctx = json.load(f)

    # Ensure all papers are embedded
    for paper_id in ctx["papers"]:
        parse_paper(paper_id)
        segment_paper(paper_id)
        extract_and_link_images(paper_id)
        chunk_paper(paper_id)
        embed_paper_chunks(paper_id)

    vs = get_vector_store()

    # Seed known duplicate questions across two different paper IDs
    duplicate_doc = "Which of the following gives the middle most observation of the data? A) Median B) Mean C) Range D) Mode"
    vs.upsert(
        ids=["seed_paper1_q16", "seed_paper2_q16"],
        documents=[duplicate_doc, duplicate_doc],
        metadatas=[
            {"paper_id": "seed_paper1", "class": "10", "subject": "mathematics", "year": "2024-2025", "question_id": "q16"},
            {"paper_id": "seed_paper2", "class": "10", "subject": "mathematics", "year": "2023-2024", "question_id": "q16"}
        ]
    )

    dedup_results = run_deduplication(similarity_threshold=0.85)

    assert dedup_results["total_duplicates_found"] > 0, "Deduplication algorithm failed to find seeded duplicate pair"

    # Find the seeded duplicate pair
    found_seeded = False
    for pair in dedup_results["duplicate_pairs"]:
        c1 = pair["chunk1"]["chunk_id"]
        c2 = pair["chunk2"]["chunk_id"]
        if (c1 == "seed_paper1_q16" and c2 == "seed_paper2_q16") or (c1 == "seed_paper2_q16" and c2 == "seed_paper1_q16"):
            found_seeded = True
            assert pair["similarity"] >= 0.99, f"Seeded duplicate similarity {pair['similarity']} < 0.99"
            break

    assert found_seeded, "Seeded duplicate pair was not found in deduplication output"

    # Clean up synthetic seeded test vectors from vector store DB
    with vs.conn:
        vs.conn.execute("DELETE FROM vectors WHERE id LIKE 'seed_%'")

    # Check context phase_status
    with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
        updated_ctx = json.load(f)

    for pid in ctx["papers"]:
        assert updated_ctx["papers"][pid]["phase_status"]["dedup"] == "done"


if __name__ == "__main__":
    test_phase7_duplicate_detection()
    print("All Phase 7 duplicate detection tests passed successfully!")
