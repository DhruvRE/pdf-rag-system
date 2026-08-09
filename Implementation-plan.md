# PDF Question-Paper RAG/Embedder — Updated Implementation Plan v2

> **Status after audit (2026-08-08):** 372 questions across 10 PDFs embedded.
> MRR@5 = 0.90, Precision@5 = 90%. Specific failure modes documented below.

---

## Current Quality Audit Results (Live Corpus)

| Issue | Count | % of corpus |
|---|---|---|
| Questions with **both** options AND subparts (mutual exclusivity failure) | 47 | 12.6% |
| Stems with leftover junk (`Options:`, `Select the most appropriate...`) | 2 | 0.5% |
| PUA / Odia / Telugu font glyphs not converted to LaTeX | 12 | 3.2% |
| Section header bleed into stem (e.g. `SECTION – B` appended to Q20 stem) | 2 | 0.5% |
| MCQ questions with wrong option count (not exactly 4) | 10 | 2.7% |
| Very short chunks (<50 chars — likely parsing failure) | 34 | 9.1% |
| Chunks with zero image links (images exist but not connected) | 362 | 100% |

**Root Causes Identified:**
1. Option extractor runs on subparts — regex hits `(a)`, `(b)`, `(c)` inside a descriptive answer and mistakes them for MCQ choices
2. PUA font glyph map is incomplete — covers `\u0b39`, `\u0b36` but misses Telugu (`\u0c00-\u0c7f`) and other scripts
3. Section headers parsed as part of final question in a section — last Q before a new section absorbs the header line
4. Image paths not propagated from `questions.json` → `chunks.json` → vector store — `image_paths` field is always empty in embeddings
5. Option detection not gated properly on question type — Assertion-Reason, passage-based, and descriptive questions all get attempted option parsing

---

## Architecture Principles (non-negotiable)

1. **One chunk = one question** — never page-level or fixed-size chunking
2. **Options XOR Subparts** — a question is EITHER MCQ OR descriptive, never both
3. **Permanent fixes live in `src/segmentation/`** — never rely on render-time cleanup for correctness
4. **Enrich at index time, not query time** — metadata (section, class, subject, year, difficulty) baked into chunk at Phase 5

---

## Phase 1 — Scraper + Storage ✅ DONE
- PDFs scraped and stored under `data/raw_pdfs/<class>/<subject>/<year>/`
- **Test:** PASS — 10 papers verified, no corrupt downloads

**Remaining gap:** Only 10 PDFs in corpus. Need 100+ before Phase 9 dedup testing is meaningful.

---

## Phase 2 — Raw Parsing (text + layout) ✅ DONE

**Current state:** PyMuPDF `page.get_text("blocks")` with bounding box data → `pages.json`

**Known issues to fix (Phase 2-B):**

### 2-B-1: Incomplete PUA Font Glyph Map
`segmenter.py` only maps a handful of Odia codepoints. Fix: extend `PUA_FONT_MAP` to cover full Telugu (`\u0c00-\u0c7f`), Kannada, Bengali unicode blocks. Also switch to `page.get_text("rawdict")` to get glyph-level font names, enabling per-font PUA range detection rather than a global guess.

### 2-B-2: Multi-Column MCQ Layout
Some CBSE papers use 2-column MCQ layout. PyMuPDF's default block ordering merges unrelated lines across columns. Fix: detect 2-column pages (x-midpoint clustering), then sort blocks by `(column, top_y)` before joining text.

### 2-B-3: OCR Fallback for Scanned PDFs
Some older papers (pre-2015) are image-only. These currently produce near-empty `pages.json`. Fix: detect page text length < 100 chars → trigger `page.get_textpage_ocr()` fallback using Tesseract via PyMuPDF's built-in OCR bridge.

**Definition of done (Phase 2-B):** Zero PUA glyphs remaining in any `pages.json`. Multi-column MCQ blocks read in correct left→right order.

---

## Phase 3 — Question Segmentation ✅ DONE (with known bugs)

**Current state:** Regex-based boundary detection on `"Q1."`, `"1."`, section headers.

**Known issues to fix (Phase 3-B):**

### 3-B-1: Section Header Bleed
The last question before a new section header absorbs the header text into its stem.

**Fix:** In `finalize_question()`, strip any line matching `SECTION\s*[–-]\s*[A-E]` from the bottom of raw text:
```python
SECTION_HDR_RE = re.compile(
    r'\n\s*(?:SECTION\s*[–\-—]\s*[A-E]|Q\.?\s*(?:No\.?)?\s*\d+\s*to\s*\d+)[^\n]*$',
    re.IGNORECASE
)
raw_text = SECTION_HDR_RE.sub('', raw_text).strip()
```

### 3-B-2: MCQ/Subpart Mutual Exclusivity (47 failing — 12.6%)
Root cause: `extract_options()` regex matches `(a)`, `(b)` inside descriptive subparts.

**Fix — Strict MCQ detection rules.** A question has MCQ options if and only if:
- Section = SECTION A (Q1–Q20), AND
- Exactly 4 options exist, AND
- No option is longer than 80 characters, AND
- No option starts with an instruction verb (`Calculate`, `Define`, `State`, `Find`, `Write`, `Explain`)

```python
INSTRUCTION_VERBS = re.compile(
    r'^(?:calculate|define|state|find|write|explain|identify|draw|name|give|derive)\b',
    re.IGNORECASE
)

def is_valid_mcq_options(opts: list[str]) -> bool:
    if len(opts) != 4:
        return False
    if any(len(o) > 80 for o in opts):
        return False
    if any(INSTRUCTION_VERBS.match(o.strip()) for o in opts):
        return False
    return True
```

### 3-B-3: Assertion-Reason Auto-Injection
Detect A-R questions by stem content. Inject standard CBSE 4 choices automatically instead of parsing from PDF (which often places them in a separate layout block that confuses the segmenter).

### 3-B-4: Short Chunk Filter (34 chunks < 50 chars)
These are phantom boundaries — the segmenter created a chunk for a section header or page number.

**Fix:** In `finalize_question()`, if `len(raw_text.strip()) < 40`, mark `is_valid=False` and exclude from `questions.json`. Log to `.agent/context.json` under `"parse_warnings"`.

---

## Phase 4 — Image Linking ✅ DONE (broken downstream)

**Current state:** Images extracted per page, linked to questions by bbox overlap → `images/q<id>_<n>.png`. But `image_paths` is **never propagated** to chunks or vector store.

**Fix (Phase 4-B):** In `src/chunking/chunker.py`, when building a chunk dict, resolve image paths from the `images/` folder:
```python
def get_image_paths_for_question(paper_dir: str, question_id: str) -> list[str]:
    pattern = os.path.join(paper_dir, "images", f"q{question_id}_*.png")
    return sorted(glob.glob(pattern))
```
Store paths in vector store metadata as JSON list. In `/api/search`, decode and include in response. In `app.js`, render `<img>` tags for each path under the question card.

---

## Phase 5 — Chunking ✅ DONE (enrichment needed)

**Current state:** One chunk per question, text is just `raw_text`.

**Improvements (Phase 5-B):**

### 5-B-1: Metadata-Enriched Chunk Text
Prepend a structured metadata header to the chunk text used for embedding:
```
[Class 10 | Mathematics | 2024-2025 | Section A | Q3 | MCQ | L3-Apply]
In ΔABC, DE ∥ AB. If AB = a, DE = x, BE = b and EC = c. Then x expressed in terms...
```
This means a student query like *"class 10 triangle proportionality theorem"* will match even if the question text doesn't use those exact words.

### 5-B-2: Subpart Sub-Chunks (Phase 5-C)
For long descriptive questions (5+ subparts), also create sub-chunks per subpart with `parent_chunk_id`. Enables targeted retrieval of specific subparts.

---

## Phase 6 — Embedding ✅ DONE (model upgrade needed)

**Current state:** `all-MiniLM-L6-v2` (384-dim, English-only), SQLite vector store

**Issues:**
- `all-MiniLM-L6-v2` is English-only — CBSE papers contain Hindi, Devanagari, and Tamil terms. These embed poorly into an English-only vector space.
- No FTS keyword fallback — pure vector-only retrieval misses exact searches like *"Q23 Class 12 Chemistry"*

**Improvements (Phase 6-B):**

### 6-B-1: Upgrade Embedding Model
Switch to `paraphrase-multilingual-MiniLM-L12-v2` (multilingual, same 384-dim, handles Hindi/Tamil/Telugu). Or use `nomic-embed-text` via Ollama (768-dim, higher quality, GPU-backed).

### 6-B-2: Add SQLite FTS5 Keyword Index
Add a BM25-capable FTS5 virtual table alongside the vector table:
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_id, text, question_number, subject, class,
    content='chunks', content_rowid='rowid'
);
```
This enables exact keyword matches for question numbers, chemical formulas, specific terms.

---

## Phase 7 — Deduplication ✅ DONE (needs year-aware upgrade)

**Current state:** Near-duplicate detection using cosine similarity threshold.

**Improvements (Phase 7-B):**
- Questions with same `class + subject + question_number` across different years are **recurring pattern questions** (intentional), not duplicates. Tag as `"recurring_pattern": true` and surface the set together in search results.
- Use locality-sensitive hashing (LSH) for scalable dedup when corpus grows to 10,000+ questions.

---

## Phase 8 — Retrieval ✅ DONE (hybrid upgrade critical)

**Current state:** Pure vector similarity, top-5 results, MRR@5 = 0.90

**Critical improvement (Phase 8-B): Hybrid Search with RRF**

Replace pure vector search with BM25 FTS5 + vector search fused by Reciprocal Rank Fusion (RRF):

```sql
WITH vec_matches AS (
    SELECT chunk_id,
           ROW_NUMBER() OVER (ORDER BY distance) AS rank_vec
    FROM chunks_vec
    WHERE embedding MATCH :query_vec AND k = 20
),
fts_matches AS (
    SELECT chunk_id,
           ROW_NUMBER() OVER (ORDER BY rank) AS rank_fts
    FROM chunks_fts
    WHERE text MATCH :query_text LIMIT 20
)
SELECT COALESCE(v.chunk_id, f.chunk_id) AS chunk_id,
       COALESCE(1.0/(60+f.rank_fts), 0.0)*0.4 +
       COALESCE(1.0/(60+v.rank_vec), 0.0)*0.6 AS rrf_score
FROM fts_matches f
FULL OUTER JOIN vec_matches v USING(chunk_id)
ORDER BY rrf_score DESC LIMIT :top_k;
```

**Why this matters:** Student queries are a mix of exact keyword searches (*"Q3 class 10 maths"*) and semantic searches (*"triangle proportionality theorem"*). FTS5 nails the former, vector search nails the latter. RRF fusion = best of both worlds.

**Target after Phase 8-B:** MRR@5 ≥ 0.95, Precision@5 ≥ 95%

---

## Phase 9 — AI Explanation Endpoint (NEW) 🔴 NOT STARTED

**Goal:** `/api/explain` — takes a question, returns step-by-step solution from local Ollama.

**Implementation:**
- `POST /api/explain` body: `{"chunk_id": "...", "question": "...", "subject": "...", "class": "..."}`
- CBSE-aware system prompt with LaTeX formatting
- Model routing: text-only → `qwen3.5:latest`; questions with images → `qwen3-vl:8b`
- Stream response via Server-Sent Events (SSE) for real-time display

**UI:** Glowing "✨ Explain with AI" button under each question card. Response streams inline in a glassmorphic panel with copy button and MathJax rendering.

---

## Phase 10 — Cross-Encoder Reranking (NEW) 🔴 NOT STARTED

**Goal:** Re-rank hybrid search top-20 using a cross-encoder before returning top-5.

```python
from sentence_transformers import CrossEncoder
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank(query: str, candidates: list[dict]) -> list[dict]:
    pairs = [(query, c["text"]) for c in candidates]
    scores = reranker.predict(pairs)
    return [c for _, c in sorted(zip(scores, candidates), key=lambda x: -x[0])]
```

**Expected impact:** MRR@5 improvement from 0.95 → ~0.97+ based on literature benchmarks.

---

## Phase 11 — Structured Filtering & Faceted Search (NEW) 🔴 NOT STARTED

**Goal:** Let users filter results by class, subject, year, section, difficulty.

**UI filters:**
- Class: `[6] [7] [8] [9] [10] [11] [12]`
- Subject: `[Mathematics] [Physics] [Chemistry] [Biology] [Science]`
- Year: `[2020-2021] ... [2024-2025]`
- Section: `[MCQ] [Short Answer] [Long Answer] [Case Study]`
- Difficulty: `[L1] [L2] [L3] [L4] [L5]`

---

## Phase 12 — Bloom's Taxonomy Difficulty Tagging (NEW) 🔴 NOT STARTED

| Level | Keyword signals | CBSE marks |
|---|---|---|
| L1 — Remember | Define, State, Name, Write | 1–2 marks |
| L2 — Understand | Explain, Describe, Identify | 2–3 marks |
| L3 — Apply | Calculate, Find, Solve, Derive | 3–5 marks |
| L4 — Analyze | Compare, Distinguish, Analyze | 4–5 marks |
| L5 — Evaluate | Justify, Evaluate, Prove | 5 marks |

Implementation: keyword-based tagger first; LLM-based (`qwen3.5:latest`) for ambiguous cases.

---

## Phase 13 — RAGAS Evaluation Framework (NEW) 🔴 NOT STARTED

Automated evaluation using RAGAS metrics: Faithfulness, Answer Relevance, Context Precision, Context Recall.

Golden dataset: expand `tests/eval_queries.json` from 10 → 100+ queries covering all subjects, classes, question types.

---

## Phase 14 — UI Polish & Production Readiness (NEW) 🔴 NOT STARTED

Outstanding rendering issues:
1. MathJax multi-line block equations sometimes break
2. Question images not shown (blocked by Phase 4-B)
3. OR divider needs better styling for long questions
4. Layout breaks on mobile (<768px)
5. Question type badges: `[MCQ]` `[A-R]` `[Descriptive]` `[Case Study]` `[5 Marks]`
6. Difficulty chip (after Phase 12)
7. Copy to clipboard — one-click clean text copy

---

## Execution Priority Order

```
IMMEDIATE — fix data quality before adding features
├── Phase 2-B: PUA glyph map extension + multi-column layout + OCR fallback
├── Phase 3-B: Section header strip + MCQ gate hardening + short chunk filter
└── Phase 4-B: Image path propagation to chunks + UI rendering

SHORT TERM — improve retrieval quality
├── Phase 5-B: Metadata-enriched chunk text
├── Phase 6-B: Multilingual embeddings + FTS5 keyword index
└── Phase 8-B: Hybrid BM25+vector RRF fusion

MEDIUM TERM — add AI features
├── Phase 9:  AI explanation endpoint (/api/explain) with Ollama SSE streaming
├── Phase 10: Cross-encoder reranking
└── Phase 11: Faceted filtering UI

LONG TERM — scale + quality assurance
├── Phase 12: Bloom's difficulty tagging
├── Phase 13: RAGAS evaluation pipeline
└── Phase 14: UI polish + mobile responsive
```

---

## Success Metrics Targets

| Metric | Current | After Immediate | After Short-term | Final Target |
|---|---|---|---|---|
| MCQ/Subpart exclusivity | 87.4% | **100%** | 100% | 100% |
| PUA glyphs remaining | 12 | **0** | 0 | 0 |
| Short/empty chunks | 34 | **0** | 0 | 0 |
| Images shown in UI | 0% | **~40%** | 40% | >80% |
| MRR@5 | 0.90 | 0.92 | **0.97** | >0.97 |
| Precision@5 | 90% | 92% | **97%** | >97% |
| Query latency p95 | ~800ms | ~600ms | **<400ms** | <300ms |
