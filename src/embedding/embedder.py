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
import re
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
            try:
                self.conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS vectors_fts USING fts5(
                        id UNINDEXED,
                        document
                    )
                """)
            except Exception:
                pass
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS school_info (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS solutions (
                    solution_id TEXT PRIMARY KEY,
                    chunk_id TEXT NOT NULL,
                    question_hash TEXT NOT NULL,
                    solution_text TEXT NOT NULL,
                    model_name TEXT,
                    prompt_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(chunk_id, question_hash, prompt_version)
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_profiles (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_name TEXT NOT NULL,
                    class_level TEXT,
                    subject TEXT,
                    blueprint_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS generated_papers (
                    paper_id TEXT PRIMARY KEY,
                    pattern_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    class_level TEXT,
                    subject TEXT,
                    paper_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def set_school_meta(self, key: str, value: str):
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO school_info (key, value) VALUES (?, ?)",
                (key, value)
            )

    def get_school_meta(self, key: str, default: str = None) -> str | None:
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT value FROM school_info WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default
        except Exception:
            return default

    def get_all_pattern_profiles(self) -> list[dict]:
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT pattern_id, pattern_name, class_level, subject, blueprint_json, created_at, updated_at
                FROM pattern_profiles
                ORDER BY updated_at DESC
            """)
            rows = cursor.fetchall()
            profiles = []
            for r in rows:
                profiles.append({
                    "pattern_id": r[0],
                    "pattern_name": r[1],
                    "class_level": r[2],
                    "subject": r[3],
                    "blueprint": json.loads(r[4]),
                    "created_at": r[5],
                    "updated_at": r[6]
                })
            return profiles
        except Exception:
            return []

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

                try:
                    self.conn.execute("""
                        INSERT OR REPLACE INTO vectors_fts (id, document)
                        VALUES (?, ?)
                    """, (qid, doc))
                except Exception:
                    pass

    def query_fts(self, query_text: str, limit: int = 20) -> list[str]:
        """Queries FTS5 virtual table for keyword BM25 matches."""
        try:
            cursor = self.conn.cursor()
            # Clean query for FTS syntax
            clean_q = ' OR '.join(re.findall(r'\w+', query_text))
            if not clean_q:
                return []
            cursor.execute("SELECT id FROM vectors_fts WHERE vectors_fts MATCH ? LIMIT ?", (clean_q, limit))
            return [row[0] for row in cursor.fetchall()]
        except Exception:
            return []

    def query(self, query_text: str = "", n_results: int = 5, where: dict = None, random_order: bool = False) -> list[dict]:
        has_query = bool(query_text and query_text.strip())
        if has_query:
            q_emb = self._embed_text(query_text.strip())

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

            if has_query:
                emb = np.frombuffer(emb_blob, dtype=np.float32)
                sim = float(np.dot(q_emb, emb))
            else:
                sim = 1.0

            results.append({
                "chunk_id": qid,
                "document": doc,
                "metadata": meta,
                "similarity": round(sim, 4),
                "distance": round(1.0 - sim, 4)
            })

        if has_query:
            # --- Reciprocal Rank Fusion (RRF) with FTS5 Keyword Ranks ---
            fts_ids = self.query_fts(query_text, limit=30)
            fts_rank = {qid: idx + 1 for idx, qid in enumerate(fts_ids)}

            results.sort(key=lambda x: x["similarity"], reverse=True)
            for dense_idx, item in enumerate(results):
                r_dense = dense_idx + 1
                r_fts = fts_rank.get(item["chunk_id"], 100)
                # Reciprocal Rank Fusion formula: 1 / (60 + r)
                rrf_score = (1.0 / (60.0 + r_dense)) + (1.0 / (60.0 + r_fts))
                item["rrf_score"] = round(rrf_score, 6)

            # Sort by fused RRF score for maximum precision
            results.sort(key=lambda x: (x.get("rrf_score", 0), x["similarity"]), reverse=True)

        elif random_order:
            import random
            random.shuffle(results)
        else:
            results.sort(key=lambda x: (
                int(x["metadata"].get("class", 0)) if str(x["metadata"].get("class", "0")).isdigit() else 0,
                x["metadata"].get("subject", ""),
                x["metadata"].get("question_id", "")
            ))

        if n_results is not None and n_results > 0:
            return results[:n_results]
        return results

    def count(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vectors")
        return cursor.fetchone()[0]

    def get_solution(self, chunk_id: str, question_hash: str, prompt_version: str) -> dict | None:
        """Returns a previously generated solution for the exact question payload."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT solution_id, chunk_id, question_hash, solution_text, model_name,
                   prompt_version, status, created_at, updated_at
            FROM solutions
            WHERE chunk_id = ? AND question_hash = ? AND prompt_version = ? AND status = 'completed'
        """, (chunk_id, question_hash, prompt_version))
        row = cursor.fetchone()
        if not row:
            return None

        fields = [
            "solution_id", "chunk_id", "question_hash", "solution_text", "model_name",
            "prompt_version", "status", "created_at", "updated_at"
        ]
        return dict(zip(fields, row))

    def save_solution(
        self,
        chunk_id: str,
        question_hash: str,
        solution_text: str,
        model_name: str,
        prompt_version: str
    ) -> dict:
        """Upserts a completed solution for an exact question/prompt version."""
        now = datetime.now(timezone.utc).isoformat()
        solution_id = hashlib.sha256(
            f"{chunk_id}:{question_hash}:{prompt_version}".encode("utf-8")
        ).hexdigest()
        with self.conn:
            self.conn.execute("""
                INSERT INTO solutions (
                    solution_id, chunk_id, question_hash, solution_text, model_name,
                    prompt_version, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'completed', ?, ?)
                ON CONFLICT(chunk_id, question_hash, prompt_version) DO UPDATE SET
                    solution_id = excluded.solution_id,
                    solution_text = excluded.solution_text,
                    model_name = excluded.model_name,
                    status = excluded.status,
                    updated_at = excluded.updated_at
            """, (
                solution_id, chunk_id, question_hash, solution_text, model_name,
                prompt_version, now, now
            ))

        return self.get_solution(chunk_id, question_hash, prompt_version)

    def save_pattern_profile(self, pattern_id: str, pattern_name: str, class_level: str, subject: str, blueprint: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT INTO pattern_profiles (
                    pattern_id, pattern_name, class_level, subject, blueprint_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pattern_id) DO UPDATE SET
                    pattern_name = excluded.pattern_name,
                    class_level = excluded.class_level,
                    subject = excluded.subject,
                    blueprint_json = excluded.blueprint_json,
                    updated_at = excluded.updated_at
            """, (
                pattern_id, pattern_name, class_level, subject,
                json.dumps(blueprint, ensure_ascii=True), now, now
            ))
        return self.get_pattern_profile(pattern_id)

    def get_pattern_profile(self, pattern_id: str) -> dict | None:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT pattern_id, pattern_name, class_level, subject, blueprint_json, created_at, updated_at
            FROM pattern_profiles WHERE pattern_id = ?
        """, (pattern_id,))
        row = cursor.fetchone()
        if not row:
            return None
        blueprint = json.loads(row[4])
        return {
            "pattern_id": row[0],
            "pattern_name": row[1],
            "class_level": row[2],
            "subject": row[3],
            "blueprint": blueprint,
            "created_at": row[5],
            "updated_at": row[6]
        }

    def save_generated_paper(self, paper_id: str, pattern_id: str, title: str, class_level: str, subject: str, paper: dict) -> dict:
        created_at = datetime.now(timezone.utc).isoformat()
        with self.conn:
            self.conn.execute("""
                INSERT OR REPLACE INTO generated_papers (
                    paper_id, pattern_id, title, class_level, subject, paper_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_id, pattern_id, title, class_level, subject,
                json.dumps(paper, ensure_ascii=True), created_at
            ))
        return {
            "paper_id": paper_id,
            "pattern_id": pattern_id,
            "title": title,
            "class_level": class_level,
            "subject": subject,
            "paper": paper,
            "created_at": created_at
        }

    def get_generated_paper(self, paper_id: str) -> dict | None:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT paper_id, pattern_id, title, class_level, subject, paper_json, created_at
            FROM generated_papers WHERE paper_id = ?
        """, (paper_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "paper_id": row[0],
            "pattern_id": row[1],
            "title": row[2],
            "class_level": row[3],
            "subject": row[4],
            "paper": json.loads(row[5]),
            "created_at": row[6]
        }

    def clear(self):
        with self.conn:
            self.conn.execute("DELETE FROM vectors")
            try:
                self.conn.execute("DELETE FROM vectors_fts")
            except Exception:
                pass


# Global vector store instance and school instances cache
_VECTOR_STORE_INSTANCE = None
_SCHOOL_VECTOR_STORES: dict[str, LocalVectorStore] = {}


def slugify_school(name: str | None) -> str:
    """Normalizes school or institution name into a clean, filesystem-safe slug."""
    if not name:
        return "general"
    s = str(name).strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "_", s)
    return s.strip("_") or "general"


def get_school_db_path(school: str, root_dir: str = PROJECT_ROOT) -> str:
    """Returns absolute path to the dedicated SQLite vector database for a school."""
    slug = slugify_school(school)
    schools_dir = os.path.join(root_dir, "data", "vector_store", "schools")
    os.makedirs(schools_dir, exist_ok=True)
    return os.path.join(schools_dir, f"{slug}.db")


def get_vector_store(school: str | None = None) -> LocalVectorStore:
    """
    Returns the vector store instance. If school is provided, returns or creates
    a dedicated school database instance (e.g. data/vector_store/schools/navodaya.db).
    Otherwise returns the global vector store.
    """
    global _VECTOR_STORE_INSTANCE, _SCHOOL_VECTOR_STORES
    if not school or str(school).strip().lower() in ("general", "none", "all", "global"):
        if _VECTOR_STORE_INSTANCE is None:
            _VECTOR_STORE_INSTANCE = LocalVectorStore()
        return _VECTOR_STORE_INSTANCE

    slug = slugify_school(school)
    if slug not in _SCHOOL_VECTOR_STORES:
        db_path = get_school_db_path(slug)
        store = LocalVectorStore(db_path=db_path)
        display_name = str(school).strip()
        store.set_school_meta("name", display_name)
        store.set_school_meta("slug", slug)
        _SCHOOL_VECTOR_STORES[slug] = store
    return _SCHOOL_VECTOR_STORES[slug]


def list_all_school_stores(root_dir: str = PROJECT_ROOT) -> list[dict]:
    """
    Discovers all school databases in data/vector_store/schools/ and combines with
    schools recorded in .agent/context.json.
    """
    schools_dir = os.path.join(root_dir, "data", "vector_store", "schools")
    context_path = os.path.join(root_dir, ".agent", "context.json")

    school_dict: dict[str, dict] = {}

    # Seed known institutions so UI dropdown starts with helpful presets
    preset_schools = [
        ("navodaya", "Navodaya Vidyalaya"),
        ("kendriya_vidyalaya", "Kendriya Vidyalaya (KV)"),
        ("delhi_public_school", "Delhi Public School (DPS)"),
        ("cbse", "CBSE Central Board"),
    ]
    for slug, name in preset_schools:
        db_file = f"{slug}.db"
        db_path = os.path.join(schools_dir, db_file)
        has_db = os.path.exists(db_path)
        school_dict[slug] = {
            "id": slug,
            "name": name,
            "slug": slug,
            "paper_count": 0,
            "question_count": 0,
            "has_db": has_db,
            "db_file": db_file,
            "classes": [],
            "subjects": []
        }

    # 1. Scan physical database files in data/vector_store/schools/
    if os.path.exists(schools_dir):
        for fname in os.listdir(schools_dir):
            if fname.endswith(".db"):
                slug = fname[:-3]
                db_path = os.path.join(schools_dir, fname)
                try:
                    conn = sqlite3.connect(db_path)
                    c = conn.cursor()
                    display_name = slug.replace("_", " ").title()
                    try:
                        c.execute("SELECT value FROM school_info WHERE key = 'name'")
                        row = c.fetchone()
                        if row and row[0]:
                            display_name = row[0]
                    except Exception:
                        pass

                    q_count = 0
                    try:
                        c.execute("SELECT COUNT(*) FROM vectors")
                        q_count = c.fetchone()[0]
                    except Exception:
                        pass

                    classes = set()
                    subjects = set()
                    try:
                        c.execute("SELECT metadata_json FROM vectors LIMIT 250")
                        for (m_json,) in c.fetchall():
                            try:
                                m = json.loads(m_json)
                                if m.get("class"):
                                    classes.add(str(m.get("class")))
                                if m.get("subject"):
                                    subjects.add(str(m.get("subject")))
                            except Exception:
                                pass
                    except Exception:
                        pass
                    conn.close()

                    existing = school_dict.get(slug, {})
                    school_dict[slug] = {
                        "id": slug,
                        "name": display_name,
                        "slug": slug,
                        "paper_count": existing.get("paper_count", 0),
                        "question_count": q_count,
                        "has_db": True,
                        "db_file": fname,
                        "classes": sorted(list(classes)),
                        "subjects": sorted(list(subjects))
                    }
                except Exception:
                    pass

    # 2. Reconcile with papers recorded in context.json
    if os.path.exists(context_path):
        try:
            with open(context_path, "r", encoding="utf-8") as f:
                ctx = json.load(f)
            for pid, pdata in ctx.get("papers", {}).items():
                raw_school = pdata.get("school")
                if raw_school:
                    slug = slugify_school(raw_school)
                    if slug not in school_dict:
                        school_dict[slug] = {
                            "id": slug,
                            "name": str(raw_school).strip(),
                            "slug": slug,
                            "paper_count": 0,
                            "question_count": 0,
                            "has_db": os.path.exists(os.path.join(schools_dir, f"{slug}.db")),
                            "db_file": f"{slug}.db",
                            "classes": [],
                            "subjects": []
                        }
                    school_dict[slug]["paper_count"] += 1
                    cls = str(pdata.get("class", ""))
                    subj = str(pdata.get("subject", ""))
                    if cls and cls not in school_dict[slug]["classes"]:
                        school_dict[slug]["classes"].append(cls)
                    if subj and subj not in school_dict[slug]["subjects"]:
                        school_dict[slug]["subjects"].append(subj)
        except Exception:
            pass

    schools = list(school_dict.values())
    schools.sort(key=lambda s: (-s["question_count"], -s["paper_count"], s["name"]))
    return schools


def embed_paper_chunks(paper_id: str, root_dir: str = PROJECT_ROOT) -> dict:
    """
    Reads chunks.json for paper_id, inserts/upserts documents, embeddings, and metadata into LocalVectorStore.
    If the paper is associated with a school, creates and routes questions into that school's dedicated DB
    (e.g. data/vector_store/schools/navodaya.db) while also maintaining the master vector store.
    Updates .agent/context.json phase_status.
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
    raw_school = p_info.get("school")
    school_slug = slugify_school(raw_school) if raw_school else None

    parsed_dir = os.path.join(root_dir, "data", "parsed", cls, subject, year, paper_id)
    chunks_json_path = os.path.join(parsed_dir, "chunks.json")

    if not os.path.exists(chunks_json_path):
        raise FileNotFoundError(f"chunks.json missing at {chunks_json_path}. Run Phase 5 chunk first.")

    with open(chunks_json_path, 'r', encoding='utf-8') as f:
        chunks_data = json.load(f)

    vs = get_vector_store()
    school_vs = get_vector_store(school=school_slug) if school_slug else None

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
            "question_type": str(chunk.get("question_type", "short_answer")),
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
        if raw_school:
            meta["school"] = str(raw_school)
            meta["school_slug"] = school_slug

        ids.append(cid)
        documents.append(content)
        metadatas.append(meta)

    target_db_path = vs.db_path
    if ids:
        # Upsert into global/main index
        vs.upsert(ids=ids, documents=documents, metadatas=metadatas)

        # Upsert into dedicated school database
        if school_vs:
            school_vs.set_school_meta("name", str(raw_school))
            school_vs.set_school_meta("slug", school_slug)
            school_vs.upsert(ids=ids, documents=documents, metadatas=metadatas)
            target_db_path = school_vs.db_path

    # Update context.json
    p_info["phase_status"]["embed"] = "done"
    p_info["updated_at"] = datetime.now(timezone.utc).isoformat()
    ctx["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(context_path, 'w', encoding='utf-8') as f:
        json.dump(ctx, f, indent=2)

    school_label = f" (school: {raw_school} -> {target_db_path})" if raw_school else ""
    print(f"Embedded {len(ids)} chunks for paper {paper_id} into LocalVectorStore DB{school_label}")
    return {
        "paper_id": paper_id,
        "total_embedded": len(ids),
        "db_path": target_db_path,
        "school": raw_school,
        "school_slug": school_slug
    }


def query_vector_store(query_text: str = "", n_results: int = None, subject_filter: str = None, class_filter: str = None, school_filter: str = None, random_order: bool = False) -> list[dict]:
    """
    Queries the LocalVectorStore for top-k matching questions with optional metadata filtering and random ordering.
    If school_filter is specified, searches directly in that school's database.
    """
    vs = get_vector_store(school=school_filter) if school_filter else get_vector_store()
    where = {}
    if subject_filter:
        where["subject"] = subject_filter
    if class_filter:
        where["class"] = class_filter
    if school_filter and not vs.db_path.endswith(f"{slugify_school(school_filter)}.db"):
        where["school_slug"] = slugify_school(school_filter)

    return vs.query(query_text=query_text, n_results=n_results, where=where if where else None, random_order=random_order)

