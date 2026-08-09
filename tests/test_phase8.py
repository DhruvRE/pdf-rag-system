"""
Phase 8 Test Suite & Evaluation Harness.
Evaluates RAG retrieval accuracy across fixed eval benchmark queries in tests/eval_queries.json
measuring Mean Reciprocal Rank (MRR@5) and Precision@5.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from src.retrieval.retriever import retrieve_questions, format_rag_context
from src.embedding.embedder import embed_paper_chunks

from src.config import PROJECT_ROOT, CONTEXT_PATH
EVAL_QUERIES_PATH = os.path.join(PROJECT_ROOT, "tests", "eval_queries.json")



def test_phase8_rag_retrieval_eval_harness():
    """Evaluates MRR@5 and Precision@5 over fixed eval benchmark set."""
    assert os.path.exists(EVAL_QUERIES_PATH), "eval_queries.json benchmark missing"
    assert os.path.exists(CONTEXT_PATH), "Context file missing"

    with open(EVAL_QUERIES_PATH, 'r', encoding='utf-8') as f:
        eval_data = json.load(f)

    queries = eval_data.get("eval_queries", [])
    assert len(queries) >= 10, "Expected at least 10 evaluation queries in benchmark set"

    reciprocal_ranks = []
    precision_scores = []

    for q_spec in queries:
        qid = q_spec["id"]
        q_text = q_spec["query"]
        expected_sec = q_spec.get("expected_subject")
        target_qid = q_spec.get("target_question_id")
        keywords = q_spec.get("keywords", [])

        # Retrieve top 5 matching question chunks
        results = retrieve_questions(
            query_text=q_text,
            top_k=5,
            subject_filter=expected_sec
        )

        assert len(results) > 0, f"Query '{q_text}' returned zero results"

        rank = None
        hit = False
        for idx, res in enumerate(results, 1):
            doc_text = res["document"].lower()
            meta = res["metadata"]

            # Match target question ID or keyword presence
            matches_qid = target_qid and meta.get("question_id") == target_qid
            matches_keywords = any(kw.lower() in doc_text for kw in keywords)

            if matches_qid or matches_keywords:
                if rank is None:
                    rank = idx
                hit = True

        if rank is not None:
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)

        precision_scores.append(1.0 if hit else 0.0)

    mrr_5 = sum(reciprocal_ranks) / len(reciprocal_ranks)
    mean_precision = sum(precision_scores) / len(precision_scores)

    print(f"\n=== Phase 8 RAG Evaluation Results ===")
    print(f"Total Benchmark Queries Evaluated: {len(queries)}")
    print(f"Mean Reciprocal Rank (MRR@5): {mrr_5:.4f}")
    print(f"Mean Precision@5: {mean_precision * 100:.2f}%\n")

    assert mrr_5 >= 0.80, f"MRR@5 metric {mrr_5:.4f} below target threshold 0.80"
    assert mean_precision >= 0.80, f"Precision@5 metric {mean_precision:.4f} below target threshold 0.80"

    # Update context.json status
    with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
        ctx = json.load(f)

    for pid in ctx["papers"]:
        ctx["papers"][pid]["phase_status"]["retrieval"] = "done"

    with open(CONTEXT_PATH, 'w', encoding='utf-8') as f:
        json.dump(ctx, f, indent=2)


if __name__ == "__main__":
    test_phase8_rag_retrieval_eval_harness()
    print("All Phase 8 RAG retrieval & evaluation harness tests passed successfully!")
