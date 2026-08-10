# PDF Question-Paper RAG System — AI & Human Developer Guide

> **Target Audience**: Human Developers & AI Coding Agents (Antigravity, Gemini, GPT, Claude).  
> **Repository**: `DhruvRE/pdf-rag-system`  
> **Last Updated**: August 2026

---

## 📌 Executive Summary

The **PDF Question-Paper RAG & Embedder System** ingests multi-format educational examination paper PDFs (Classes 1–12, multiple subjects/years), parses complex two-column PDF layouts, isolates question boundaries, extracts and links diagram images spatially across page boundaries, reconciles JSON structures against raw source spans, classifies questions into an 11-type taxonomy, indexes hybrid BM25 + dense vector embeddings, deduplicates question pairs, and provides a FastAPI REST backend with a LaTeX-rendered Web UI and local Ollama AI solution generation.

---

## 🏗 System Architecture & Stage Breakdown

```
                        PDF Input
                           │
             Stage 0: Type Detection (native vs scanned)
                           │
             Stage 1: Unified Markdown + Image Manifest
                           │
             Stage 2/3: Image Cropping & BBox Placeholder Mapping
                           │
             Stage 4: Multi-Pass Structuring & Reconciliation
             ├─ Pass A: CBSE JSON Extraction + raw_source_span Attachment
             ├─ Pass B-0: Source Reconciliation (compares extraction vs source)
             ├─ Pass B-1: Question Type Classifier (11 primary types)
             └─ Pass B-2: Type-Aware Validator (runs type-specific checks)
                           │
             Stage 5: Self-Validation & Selective VLM Escalation
                           │
             Stage 6: Drafts Review Queue & Quality Gate
                           │
             Stage 7: Subpart Chunking & Hybrid Vector Embeddings
             (BM25 FTS5 + Dense Vector RRF Fusion)
                           │
             Stage 8: RAG Retrieval, Local Ollama AI, & Web UI
```

### Modular Phase Table

| Phase | Purpose | Main Engine Module | Primary Input | Primary Output |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | PDF Ingestion & Sanity Check | `src/scraper/` | Official CBSE URLs / Uploads | `data/raw_pdfs/<class>/<subject>/<year>/<paper_id>.pdf` |
| **Phase 2** | Raw Layout & Text Extraction | `src/parsing/parser.py` | Raw PDF file | `data/parsed/.../<paper_id>/pages.json` |
| **Phase 3** | Boundary Detection & Pass B-0 | `src/segmentation/structured_parser.py` | `pages.json` | `data/parsed/.../<paper_id>/questions.json` |
| **Phase 4** | Image & Cross-Page Diagram Linker | `src/image_linking/extractor.py` | PDF + `questions.json` | `data/parsed/.../<paper_id>/images/q<id>_<n>.png` |
| **Phase 5** | Question-Level Chunking | `src/chunking/chunker.py` | `questions.json` | `data/parsed/.../<paper_id>/chunks.json` |
| **Phase 6** | Hybrid Vector Store Indexing | `src/embedding/embedder.py` | `chunks.json` | `data/vector_store/vector_index.db` (SQLite + FTS5 + NumPy) |
| **Phase 7** | Duplicate Question Detection | `src/dedup/deduplicator.py` | Vector Index DB | Pairwise Match Report / `context.json` update |
| **Phase 8** | RAG Search, Ollama AI, & Web API | `src/retrieval/`, `src/api/` | User Query | FastAPI JSON / RAG Prompt / Web UI |

---

## 🔬 Core System Enhancements & Pipeline Details

### 1. Pass B-0 General-Purpose Source Reconciliation
Instead of relying solely on pattern-matching regexes, Pass A attaches `raw_source_span` to every question object. **Pass B-0 (`reconcile_question_against_source`)** compares extracted JSON directly against original verbatim source text:
- **Option Marker Repair**: Reconciles option count when raw source span contains distinct markers (`(a)`, `b)`, `(c )`, `( d )`) that regex missed due to spacing or OCR glitches.
- **Placeholder Alignment**: Re-attaches unassigned `[IMAGE_PLACEHOLDER_N]` tokens directly from `raw_source_span`.
- **Truncation Flagging**: Detects cases where `raw_source_span` exists but extracted stem text is truncated/corrupted.

### 2. Pass B-1 Type Classifier & Pass B-2 Type-Aware Validator
- **Taxonomy**: 11 closed primary question types (`single_choice_mcq`, `assertion_reason`, `diagram_based`, `case_study_passage`, `fill_in_the_blank`, `true_false`, `match_the_following`, `multiple_choice_multi`, `short_answer`, `long_answer`, `numeric_answer`).
- **Boolean Flags**: `requires_image`, `requires_table_data`, `has_or_alternative`, `missing_image_reference`.
- **Validation Rules**:
  - `assertion_reason`: Requires exactly 4 standard options and `"Assertion"` stem text.
  - `requires_image` / `missing_image_reference`: Catches questions referencing figures without attached image placeholders.
  - `single_choice_mcq`: Enforces option alignment ($2 \le \text{options} \le 4$).

### 3. Cross-Page Image Diagram & Code Snippet Linker
In examination PDFs, code blocks or diagram figures often spill over from the bottom of Page $N-1$ to the top of Page $N$. `extractor.py` handles cross-page linking:
- When an image is located at the top of Page $N$ ($y_0 < 150$) and the last question on Page $N-1$ ended near the bottom ($y_0 > 500$) referencing a diagram or code snippet, the image is linked directly across the page boundary.

### 4. Stage 7 RRF Hybrid Search (BM25 FTS5 + Dense Vectors)
Implements **Reciprocal Rank Fusion (RRF)** in `LocalVectorStore`:
$$\text{RRF Score} = \frac{1}{60 + r_{\text{dense}}} + \frac{1}{60 + r_{\text{sparse}}}$$
Fuses exact keyword lookups (chemical formulas, unit terms, question IDs) from SQLite FTS5 with 384-dimensional subword dense vector similarity for maximum retrieval precision.

### 5. Granular Extraction Quality Benchmark (`tests/test_extraction_quality.py`)
Separated from vector retrieval metrics, this harness evaluates internal JSON structural accuracy across all extracted papers:
- **MCQ 4-Option Splitting Accuracy**: `100.0%`
- **Stem Text Purity**: `99.75%`
- **PUA Font Cleanliness**: `99.88%`
- **Options XOR Subparts Exclusivity**: `100.0%`
- **Diagram Figure Attachment Accuracy**: `72.5%`

---

## 🌐 Web REST API Endpoints (`src/api/app.py`)

- `POST /api/search` — Runs RRF Hybrid Search across indexed question chunks.
- `GET /api/stats` — Returns dataset statistics (paper counts, total questions, extracted diagrams).
- `POST /api/explain` — Streams step-by-step LaTeX solution for a question using local Ollama model (`qwen3.5:latest`).
- `GET /api/drafts` — Lists in-progress paper drafts and audit flags for the Drafts Review Queue UI.
- `POST /api/drafts/approve` — Marks a paper draft approved for indexing.
- `GET /api/dedup` — Returns cross-paper duplicate question pairs ($\ge 92\%$ cosine similarity).
- `POST /api/dedup/remove` — Deletes a redundant duplicate question chunk from the vector store database.

---

## 📂 Folder Structure Rules

```
pdf-rag-system/
├── .env                          # Local environment variables & secret keys (GIT IGNORED)
├── .env.example                  # Environment configuration template
├── .gitignore                    # Git rules excluding .env & generated vector store data
├── AGENTS.md                     # Agent & Multi-worker operational rules
├── README.md                     # Setup & architecture guide
├── Implementation-plan.md        # 8-Stage Architecture plan
├── requirements.txt              # Python package dependencies
├── .agent/
│   └── context.json              # SHARED MULTI-WORKER STATE (Read/Write Single Source of Truth)
├── docs/
│   └── system-knowledge-guide.md # THIS DOCUMENT
├── data/                         # ALL GENERATED OUTPUT LIVES HERE
│   ├── raw_pdfs/<class>/<subject>/<year>/*.pdf
│   ├── parsed/<class>/<subject>/<year>/<paper_id>/
│   │   ├── pages.json
│   │   ├── questions.json
│   │   ├── structured_draft.json
│   │   ├── chunks.json
│   │   └── images/q<question_id>_<n>.png
│   └── vector_store/
│       └── vector_index.db       # SQLite FTS5 + NumPy dense vector database
├── src/
│   ├── config.py                 # Centralized configuration loader
│   ├── api/app.py                # FastAPI REST endpoints & Web UI server
│   ├── chunking/chunker.py       # Subpart chunking engine
│   ├── dedup/deduplicator.py     # Pairwise duplicate question detector
│   ├── embedding/embedder.py     # LocalVectorStore with RRF Hybrid Search
│   ├── image_linking/extractor.py# Spatial & Cross-Page Diagram Linker
│   ├── parsing/parser.py         # PyMuPDF layout block parser
│   ├── retrieval/retriever.py    # Query formatting & RAG prompt builder
│   ├── scraper/downloader.py     # PDF scraper & sanity validator
│   └── segmentation/structured_parser.py # Boundary detector, Pass B-0 & Classifier
├── tests/
│   ├── test_stage_pipeline.py    # Stages 0–7 integration test
│   ├── test_phase8.py            # Phase 8 RAG Vector Retrieval benchmark
│   └── test_extraction_quality.py# Granular Structural Extraction Quality benchmark
└── web/                          # Frontend Web UI
    ├── index.html                # HTML structure with Search, Drafts Queue, and Dedup tabs
    ├── app.js                    # UI logic, MathJax rendering, & Ollama AI solution streaming
    └── style.css                 # CSS design system with glassmorphism & badges
```
