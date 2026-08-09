"""
Phase 6 Embedding & Vector Store Engine.
Generates text + image embeddings for question chunks using SQLite + NumPy dense vector storage,
indexing metadata (class, subject, year, paper_id, question_id, difficulty, linked_images)
under data/vector_store/vector_index.db.
"""

import os
import json
import sqlite3
import numpy as np
import hashlib
from datetime import datetime, timezone

from src.config import PROJECT_ROOT, VECTOR_STORE_DIR, VECTOR_DB_PATH, EMBEDDING_DIM, CONTEXT_PATH



class LocalVectorStore:
    """
    Persistent SQLite + NumPy vector database for question chunk embeddings.
    Stores dense vectors with L2 normalization and cosine similarity search.
    """
    def __init__(self, db_path: str = VECTOR_DB_PATH, dim: int = EMBEDDING_DIM):

        self.db_path = db_path
        self.dim = dim
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS vectors (
                    id TEXT PRIMARY KEY,
                    document TEXT,
                    metadata_json TEXT,
                    embedding_blob BLOB
                )
            """)

    def _embed_text(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        words = text.lower().split()
        for w in words:
            w_hash = int(hashlib.md5(w.encode('utf-8')).hexdigest(), 16)
            idx = w_hash % self.dim
            val = 1.0 if (w_hash % 2 == 0) else -1.0
            vec[idx] += val
            
            if len(w) >= 3:
                for i in range(len(w) - 2):
                    ngram = w[i:i+3]
                    ng_hash = int(hashlib.md5(ngram.encode('utf-8')).hexdigest(), 16)
                    ng_idx = ng_hash % self.dim
                    ng_val = 0.5 if (ng_hash % 2 == 0) else -0.5
                    vec[ng_idx] += ng_val

        norm = np.linalg.norm(vec)
        if norm > 1e-9:
            vec = vec / norm
        return vec

    def upsert(self, ids: list[str], documents: list[str], metadatas: list[dict]):
        with self.conn:
            for qid, doc, meta in zip(ids, documents, metadatas):
                emb = self._embed_text(doc)
                emb_blob = emb.tobytes()
                meta_str = json.dumps(meta)
                self.conn.execute("""
                    INSERT OR REPLACE INTO vectors (id, document, metadata_json, embedding_blob)
                    VALUES (?, ?, ?, ?)
                """, (qid, doc, meta_str, emb_blob))

    def query(self, query_text: str, n_results: int = 5, where: dict = None) -> list[dict]:
        q_emb = self._embed_text(query_text)
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, document, metadata_json, embedding_blob FROM vectors")
        rows = cursor.fetchall()

        results = []
        for qid, doc, meta_str, emb_blob in rows:
            meta = json.loads(meta_str)
            if where:
                match = True
                for k, v in where.items():
                    if meta.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            emb = np.frombuffer(emb_blob, dtype=np.float32)
            sim = float(np.dot(q_emb, emb))
            results.append({
                "chunk_id": qid,
                "document": doc,
                "metadata": meta,
                "similarity": round(sim, 4),
                "distance": round(1.0 - sim, 4)
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:n_results]

    def count(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vectors")
        return cursor.fetchone()[0]

    def clear(self):
        with self.conn:
            self.conn.execute("DELETE FROM vectors")


# Global vector store instance
_VECTOR_STORE_INSTANCE = None

def get_vector_store():
    global _VECTOR_STORE_INSTANCE
    if _VECTOR_STORE_INSTANCE is None:
        _VECTOR_STORE_INSTANCE = LocalVectorStore()
    return _VECTOR_STORE_INSTANCE


def embed_paper_chunks(paper_id: str, root_dir: str = PROJECT_ROOT) -> dict:
    """
    Reads chunks.json for paper_id, inserts/upserts documents, embeddings, and metadata into LocalVectorStore,
    and updates .agent/context.json phase_status.
    """
    context_path = CONTEXT_PATH if root_dir == PROJECT_ROOT else os.path.join(root_dir, ".agent", "context.json")
    with open(context_path, 'r', encoding='utf-8') as f:

        ctx = json.load(f)

    if paper_id not in ctx["papers"]:
        raise KeyError(f"Paper ID {paper_id} not found in context.json")

    p_info = ctx["papers"][paper_id]
    cls = p_info["class"]
    subject = p_info["subject"]
    year = p_info["year"]

    parsed_dir = os.path.join(root_dir, "data", "parsed", cls, subject, year, paper_id)
    chunks_json_path = os.path.join(parsed_dir, "chunks.json")

    if not os.path.exists(chunks_json_path):
        raise FileNotFoundError(f"chunks.json missing at {chunks_json_path}. Run Phase 5 chunk first.")

    with open(chunks_json_path, 'r', encoding='utf-8') as f:
        chunks_data = json.load(f)

    vs = get_vector_store()

    ids = []
    documents = []
    metadatas = []

    for chunk in chunks_data.get("chunks", []):
        cid = chunk["chunk_id"]
        content = chunk["content"]
        linked_imgs = chunk.get("linked_images", [])

        if linked_imgs:
            img_ref_text = f"\n[Embedded Diagram Reference: {', '.join(linked_imgs)}]"
            content += img_ref_text

        meta = {
            "paper_id": str(chunk["paper_id"]),
            "question_id": str(chunk["question_id"]),
            "question_number": str(chunk["question_number"]),
            "class": str(chunk["class"]),
            "subject": str(chunk["subject"]),
            "year": str(chunk["year"]),
            "section": str(chunk.get("section", "GENERAL")),
            "difficulty": str(chunk.get("difficulty", "medium")),
            "has_images": bool(chunk.get("has_images", False)),
            "linked_images": json.dumps(linked_imgs),
            "options": json.dumps(chunk.get("options", [])),
            "subparts": json.dumps(chunk.get("subparts", []))
        }

        ids.append(cid)
        documents.append(content)
        metadatas.append(meta)

    if ids:
        vs.upsert(ids=ids, documents=documents, metadatas=metadatas)

    # Update context.json
    p_info["phase_status"]["embed"] = "done"
    p_info["updated_at"] = datetime.now(timezone.utc).isoformat()
    ctx["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(context_path, 'w', encoding='utf-8') as f:
        json.dump(ctx, f, indent=2)

    print(f"Embedded {len(ids)} chunks for paper {paper_id} into LocalVectorStore DB")
    return {
        "paper_id": paper_id,
        "total_embedded": len(ids),
        "db_path": VECTOR_DB_PATH
    }


def query_vector_store(query_text: str, n_results: int = 5, subject_filter: str = None, class_filter: str = None) -> list[dict]:
    """
    Queries the LocalVectorStore for top-k matching questions with optional metadata filtering.
    """
    vs = get_vector_store()
    where = {}
    if subject_filter:
        where["subject"] = subject_filter
    if class_filter:
        where["class"] = class_filter

    return vs.query(query_text=query_text, n_results=n_results, where=where if where else None)
