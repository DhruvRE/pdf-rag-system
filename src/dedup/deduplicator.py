"""
Phase 7: Duplicate & Near-Duplicate Question Detection.
Compares question chunk vector embeddings across papers, subjects, and years using cosine similarity
to flag identical or near-duplicate questions across examination papers.
"""

import os
import json
import sqlite3
import numpy as np
from datetime import datetime, timezone
from src.config import PROJECT_ROOT, VECTOR_DB_PATH, DEDUP_SIMILARITY_THRESHOLD, CONTEXT_PATH
from src.embedding.embedder import get_vector_store


def find_duplicate_questions(similarity_threshold: float = DEDUP_SIMILARITY_THRESHOLD, db_path: str = VECTOR_DB_PATH) -> list[dict]:

    """
    Computes pairwise vector similarity across all question chunks in the vector store
    and returns detected duplicate or near-duplicate question pairs.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, document, metadata_json, embedding_blob FROM vectors")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    chunk_ids = []
    documents = []
    metadatas = []
    embeddings = []

    for qid, doc, meta_str, emb_blob in rows:
        chunk_ids.append(qid)
        documents.append(doc)
        metadatas.append(json.loads(meta_str))
        embeddings.append(np.frombuffer(emb_blob, dtype=np.float32))

    emb_matrix = np.vstack(embeddings) # Shape: (N, 384)
    
    # Pairwise cosine similarity matrix
    sim_matrix = np.dot(emb_matrix, emb_matrix.T)

    duplicate_pairs = []
    n = len(chunk_ids)

    for i in range(n):
        for j in range(i + 1, n):
            sim = float(sim_matrix[i, j])
            if sim >= similarity_threshold:
                meta_i = metadatas[i]
                meta_j = metadatas[j]
                
                # Check if from different papers or different questions
                if meta_i["paper_id"] != meta_j["paper_id"] or meta_i["question_id"] != meta_j["question_id"]:
                    duplicate_pairs.append({
                        "similarity": round(sim, 4),
                        "chunk1": {
                            "chunk_id": chunk_ids[i],
                            "paper_id": meta_i["paper_id"],
                            "class": meta_i["class"],
                            "subject": meta_i["subject"],
                            "year": meta_i["year"],
                            "question_id": meta_i["question_id"],
                            "document_snippet": documents[i][:150]
                        },
                        "chunk2": {
                            "chunk_id": chunk_ids[j],
                            "paper_id": meta_j["paper_id"],
                            "class": meta_j["class"],
                            "subject": meta_j["subject"],
                            "year": meta_j["year"],
                            "question_id": meta_j["question_id"],
                            "document_snippet": documents[j][:150]
                        }
                    })

    duplicate_pairs.sort(key=lambda x: x["similarity"], reverse=True)
    return duplicate_pairs


def run_deduplication(similarity_threshold: float = DEDUP_SIMILARITY_THRESHOLD, root_dir: str = PROJECT_ROOT) -> dict:
    """
    Executes duplicate detection, updates .agent/context.json phase_status, and returns report.
    """
    context_path = CONTEXT_PATH if root_dir == PROJECT_ROOT else os.path.join(root_dir, ".agent", "context.json")
    with open(context_path, 'r', encoding='utf-8') as f:

        ctx = json.load(f)

    duplicate_pairs = find_duplicate_questions(similarity_threshold=similarity_threshold)

    # Update context.json status
    for pid in ctx["papers"]:
        ctx["papers"][pid]["phase_status"]["dedup"] = "done"
    
    ctx["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(context_path, 'w', encoding='utf-8') as f:
        json.dump(ctx, f, indent=2)

    print(f"Deduplication scan complete: found {len(duplicate_pairs)} duplicate/near-duplicate pairs (threshold={similarity_threshold})")
    return {
        "similarity_threshold": similarity_threshold,
        "total_duplicates_found": len(duplicate_pairs),
        "duplicate_pairs": duplicate_pairs
    }
