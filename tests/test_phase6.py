"""
Phase 6 Test Suite.
Verifies LocalVectorStore indexing under data/vector_store/vector_index.db
and evaluates top-k semantic retrieval relevance across 10+ domain queries.
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
from src.embedding.embedder import (
    embed_paper_chunks,
    query_vector_store,
    get_vector_store,
    VECTOR_DB_PATH
)

from src.config import PROJECT_ROOT, CONTEXT_PATH


TEST_RETRIEVAL_QUERIES = [
    {"query": "electric current SI unit Ampere", "expected_subject": "physics", "min_results": 1},
    {"query": "Ohm law resistance formula", "expected_subject": "physics", "min_results": 1},
    {"query": "photosynthesis process chemical equation", "expected_subject": "science", "min_results": 1},
    {"query": "convex lens ray diagram magnification", "expected_subject": "physics", "min_results": 1},
    {"query": "hydrochloric acid zinc granules hydrogen gas", "expected_subject": "science", "min_results": 1},
    {"query": "tangent drawn from external point to circle", "expected_subject": "mathematics", "min_results": 1},
    {"query": "rate constant first order reaction half life", "expected_subject": "chemistry", "min_results": 1},
    {"query": "quadratic polynomial zeroes", "expected_subject": "mathematics", "min_results": 1},
    {"query": "plant cell vacuole cell wall nucleus", "expected_subject": "science", "min_results": 1},
    {"query": "capacitance parallel plate capacitor", "expected_subject": "physics", "min_results": 1}
]


def test_phase6_embedding_and_vector_store():
    """Embeds all papers into LocalVectorStore DB and evaluates vector store indexing and query retrieval."""
    assert os.path.exists(CONTEXT_PATH), "Context file missing"

    vs = get_vector_store()
    vs.clear()

    with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
        ctx = json.load(f)

    total_embedded = 0
    for paper_id, p_info in ctx["papers"].items():
        parse_paper(paper_id)
        segment_paper(paper_id)
        extract_and_link_images(paper_id)
        chunk_paper(paper_id)
        res = embed_paper_chunks(paper_id)
        total_embedded += res["total_embedded"]

    assert total_embedded >= 300, f"Expected at least 300 chunks embedded across 10 papers, got {total_embedded}"
    assert os.path.exists(VECTOR_DB_PATH), f"Vector DB missing at {VECTOR_DB_PATH}"

    vs = get_vector_store()
    assert vs.count() == total_embedded, f"DB count {vs.count()} mismatch with embedded total {total_embedded}"

    # Evaluate semantic query retrieval accuracy across known domain queries
    for q_spec in TEST_RETRIEVAL_QUERIES:
        q_text = q_spec["query"]
        results = query_vector_store(q_text, n_results=5)

        assert len(results) >= q_spec["min_results"], f"Query '{q_text}' returned zero results"
        top_result = results[0]

        assert "chunk_id" in top_result
        assert "document" in top_result
        assert "metadata" in top_result
        assert "similarity" in top_result
        assert top_result["similarity"] > 0.0, f"Similarity for query '{q_text}' was {top_result['similarity']}"

        # Check metadata attributes present
        meta = top_result["metadata"]
        assert "class" in meta
        assert "subject" in meta
        assert "year" in meta
        assert "question_id" in meta
        assert "paper_id" in meta

    # Verify context phase_status
    with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
        updated_ctx = json.load(f)

    for pid in ctx["papers"]:
        assert updated_ctx["papers"][pid]["phase_status"]["embed"] == "done"


if __name__ == "__main__":
    test_phase6_embedding_and_vector_store()
    print("All Phase 6 embedding & vector store retrieval tests passed successfully!")
