"""
Phase 8: RAG Retrieval & Prompt Context Engine.
Performs semantic hybrid search over vectorized question chunks with metadata filtering
and formats retrieved results into structured prompt context for LLM question answering.
"""

import os
import json
from src.embedding.embedder import query_vector_store, get_vector_store

from src.config import PROJECT_ROOT, DEFAULT_SEARCH_TOP_K


def retrieve_questions(
    query_text: str,
    top_k: int = DEFAULT_SEARCH_TOP_K,
    subject_filter: str = None,
    class_filter: str = None
) -> list[dict]:

    """
    Retrieves top-k relevant question chunks matching query_text from LocalVectorStore DB.
    """
    results = query_vector_store(
        query_text=query_text,
        n_results=top_k,
        subject_filter=subject_filter,
        class_filter=class_filter
    )
    return results


def format_rag_context(retrieved_results: list[dict]) -> str:
    """
    Formats retrieved search results into a clean, structured RAG prompt context.
    """
    if not retrieved_results:
        return "No matching questions found in vector store database."

    formatted_blocks = []
    for idx, res in enumerate(retrieved_results, 1):
        meta = res.get("metadata", {})
        pid = res.get("paper_id") or meta.get("paper_id")
        cls = res.get("class") or meta.get("class")
        subj = res.get("subject") or meta.get("subject")
        yr = res.get("year") or meta.get("year")
        qn = res.get("question_number") or meta.get("question_number")
        doc = res.get("stem_text") or res.get("content") or res.get("document", "")
        sim = res.get("similarity", 1.0)

        header = f"--- [Result {idx}] Paper: {pid} | Class {cls} {subj} ({yr}) | Question: {qn} | Similarity: {sim:.4f} ---"
        
        block_parts = [header, doc]
        
        opts = res.get("options")
        if opts:
            if isinstance(opts, list):
                opts_formatted = []
                for o in opts:
                    if isinstance(o, dict):
                        opts_formatted.append(f"({o.get('label')}) {o.get('text')}")
                    else:
                        opts_formatted.append(str(o))
                block_parts.append("Options:\n" + "\n".join(opts_formatted))
            elif isinstance(opts, str) and opts != "[]":
                block_parts.append(f"Options: {opts}")

        formatted_blocks.append("\n".join(block_parts))

    return "\n\n".join(formatted_blocks)
