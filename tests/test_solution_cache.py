import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.embedding.embedder import LocalVectorStore


def test_solution_cache_round_trip(tmp_path):
    store = LocalVectorStore(str(tmp_path / "solutions.db"))

    assert store.get_solution("paper_q1", "hash-1", "v1") is None

    saved = store.save_solution(
        chunk_id="paper_q1",
        question_hash="hash-1",
        solution_text="**Correct Answer:** (B)",
        model_name="test-model",
        prompt_version="v1"
    )

    assert saved["chunk_id"] == "paper_q1"
    assert saved["solution_text"] == "**Correct Answer:** (B)"
    assert saved["model_name"] == "test-model"

    cached = store.get_solution("paper_q1", "hash-1", "v1")
    assert cached["solution_id"] == saved["solution_id"]

    # A changed question payload must not reuse the old solution.
    assert store.get_solution("paper_q1", "hash-2", "v1") is None


def test_solution_cache_is_prompt_versioned(tmp_path):
    store = LocalVectorStore(str(tmp_path / "solutions.db"))
    store.save_solution("paper_q1", "hash-1", "old", "test-model", "v1")

    assert store.get_solution("paper_q1", "hash-1", "v1")["solution_text"] == "old"
    assert store.get_solution("paper_q1", "hash-1", "v2") is None