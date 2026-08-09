# PDF Question-Paper RAG System — AI & Human Developer Guide

> **Target Audience**: Human Developers & AI Coding Agents (Antigravity, Gemini, GPT, Claude).  
> **Repository**: `DhruvRE/pdf-rag-system`  
> **Last Updated**: August 2026

---

## 📌 Executive Summary

The **PDF Question-Paper RAG & Embedder System** ingests multi-format educational examination paper PDFs (Classes 1–12, multiple subjects/years), parses complex two-column PDF layouts, isolates question boundaries, extracts and links diagram images spatially, standardizes questions into 1-to-1 RAG chunks, indexes dense vector embeddings, deduplicates question pairs, and provides a FastAPI REST backend with a LaTeX-rendered Web UI.

---

## 🏗 System Architecture & Phase Breakdown

The system is built in **8 modular phases**, strictly enforcing separation of concerns:

```
               +----------------------------------+
               | Phase 1: PDF Scraper & Storage   |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               | Phase 2: PDF Layout Parser       |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               | Phase 3: Question Segmenter      |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               | Phase 4: Spatial Diagram Linker  |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               | Phase 5: Question Chunker        |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               | Phase 6: Vector Store & Embedder |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               | Phase 7: Duplicate Detector      |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               | Phase 8: RAG Retrieval & Web API |
               +----------------------------------+
```

### Phase Summary Table

| Phase | Purpose | Main Engine Module | Primary Input | Primary Output |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | PDF Ingestion & Sanity Check | `src/scraper/` | Official CBSE URLs / Uploads | `data/raw_pdfs/<class>/<subject>/<year>/<paper_id>.pdf` |
| **Phase 2** | Raw Layout & Text Extraction | `src/parsing/parser.py` | Raw PDF file | `data/parsed/.../<paper_id>/pages.json` |
| **Phase 3** | Question Boundary Detection | `src/segmentation/segmenter.py` | `pages.json` | `data/parsed/.../<paper_id>/questions.json` |
| **Phase 4** | Image Extraction & Linking | `src/image_linking/extractor.py` | PDF + `questions.json` | `data/parsed/.../<paper_id>/images/q<id>_<n>.png` |
| **Phase 5** | Question-Level Chunking | `src/chunking/chunker.py` | `questions.json` | `data/parsed/.../<paper_id>/chunks.json` |
| **Phase 6** | Dense Vector Store Indexing | `src/embedding/embedder.py` | `chunks.json` | `data/vector_store/vector_index.db` (SQLite + NumPy) |
| **Phase 7** | Duplicate Question Detection | `src/dedup/deduplicator.py` | Vector Index DB | Duplicate Pair Report / `context.json` update |
| **Phase 8** | Semantic RAG Search & API | `src/retrieval/`, `src/api/` | User Query | FastAPI JSON / RAG Prompt / Web UI |

---

## 📂 Folder Structure Rules

```
pdf-rag-system/
├── .env                          # Local environment variables & secret keys (GIT IGNORED)
├── .env.example                  # Environment configuration template
├── .gitignore                    # Git rules excluding .env & generated vector store data
├── AGENTS.md                     # Agent & Multi-worker operational rules
├── README.md                     # General setup guide
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
│   │   ├── chunks.json
│   │   └── images/q<question_id>_<n>.png
│   └── vector_store/
│       └── vector_index.db       # SQLite + NumPy dense vector storage
├── src/
│   ├── config.py                 # Centralized configuration loader (loads .env)
│   ├── api/app.py                # FastAPI REST endpoints & Web UI server
│   ├── chunking/chunker.py       # Phase 5 chunking engine
│   ├── dedup/deduplicator.py     # Phase 7 deduplication engine
│   ├── embedding/embedder.py     # Phase 6 vector store & embedding engine
│   ├── image_linking/extractor.py# Phase 4 image extraction & spatial linker
│   ├── parsing/
│   │   ├── parser.py             # Phase 2 layout parser
│   │   └── ai_normalizer.py      # Hybrid Rule + Local/Cloud LLM LaTeX normalizer
│   ├── retrieval/retriever.py    # Phase 8 RAG retrieval engine
│   ├── scraper/                  # Phase 1 downloader, generator & sanity checkers
│   └── segmentation/segmenter.py # Phase 3 question boundary detector
├── scripts/
│   ├── run_phase.py              # Single-phase CLI runner
│   └── add_pdf.py                # CLI tool to ingest & process custom PDFs
├── tests/                        # Pytest suite (Phases 1–8)
│   ├── fixtures/                 # Sample benchmark test PDFs
│   ├── labeled/ground_truth.json # Ground-truth boundaries for segmentation benchmarks
│   └── test_phase[1-8].py        # Automated phase test suites
└── web/                          # Web UI static assets (HTML/CSS/JS with MathJax)
```

---

## ⚙️ Configuration System (`src/config.py`)

All paths, model names, URLs, API keys, and parameters are centrally loaded from `.env` via `src/config.py`. **No module hardcodes paths or model names.**

### Configuration Parameters Summary

| Environment Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PROJECT_ROOT` | Auto-detected repository root | Base project root directory |
| `LLM_PROVIDER` | `local` | LLM execution provider: `local` (Ollama) or `cloud` (Google / Mistral) |
| `CLOUD_PROVIDER` | `google` | Cloud provider selection: `google` or `mistral` |
| `OLLAMA_API_URL` | `http://localhost:11434/api/generate` | Local Ollama REST endpoint |
| `OLLAMA_MODEL_NAME` | `qwen3.5:latest` | Local Ollama model identifier |
| `GOOGLE_API_KEY` | `""` | Google Gemini REST API Key |
| `GEMINI_MODEL_NAME` | `gemini-1.5-flash` | Google Gemini model identifier |
| `MISTRAL_API_KEY` | `""` | Mistral AI REST API Key |
| `MISTRAL_MODEL_NAME` | `mistral-small-latest` | Mistral AI model identifier |
| `EMBEDDING_DIM` | `384` | Dense vector dimension size |
| `DEDUP_SIMILARITY_THRESHOLD`| `0.85` | Cosine similarity threshold for duplicate detection |
| `API_HOST` | `0.0.0.0` | FastAPI server host |
| `API_PORT` | `8000` | FastAPI server port |

---

## 🤖 Multi-Worker Shared Context (`.agent/context.json`)

To enable multi-agent and multi-worker parallel execution without collision, state is tracked in `.agent/context.json`:

```json
{
  "schema_version": "1.0",
  "papers": {
    "799613079bee": {
      "paper_id": "799613079bee",
      "class": "12",
      "subject": "physics",
      "year": "2024-2025",
      "filename": "class12_physics_2024_2025_sqp.pdf",
      "relative_path": "data/raw_pdfs/12/physics/2024-2025/class12_physics_2024_2025_sqp.pdf",
      "phase_status": {
        "scrape": "done",
        "parse": "done",
        "segment": "done",
        "extract_images": "done",
        "chunk": "done",
        "embed": "done",
        "dedup": "done"
      }
    }
  }
}
```

### Protocol Rules for Workers:
1. **Always read `.agent/context.json` first** before starting work.
2. Claim papers by setting `"in-progress"` and your worker timestamp.
3. Update phase status to `"done"` or `"failed"` upon completion.
4. Only edit entries you have claimed.

---

## 🧠 Hybrid LLM Engine (Local vs. Cloud)

`src/parsing/ai_normalizer.py` provides semantic question structuring with support for local and cloud models:

```python
from src.parsing.ai_normalizer import enhance_question_with_ai

# Enhances raw extracted text into LaTeX stem, options, and subparts
structured_q = enhance_question_with_ai(raw_text="In delta circuit...", use_ollama=True)
```

- **Local Provider (`LLM_PROVIDER=local`)**: Sends standard HTTP payload to Ollama (`qwen3.5:latest`).
- **Cloud Provider (`LLM_PROVIDER=cloud`)**: 
  - If `CLOUD_PROVIDER=google`: Uses Google Gemini API (`gemini-1.5-flash`).
  - If `CLOUD_PROVIDER=mistral`: Uses Mistral AI API (`mistral-small-latest`).

---

## 🧪 Testing & Verification

All automated tests use `pytest`:
```bash
pytest
```
- Every phase includes an isolated test file in `tests/test_phase[1-8].py`.
- Benchmark evaluation queries exist in `tests/eval_queries.json` measuring **MRR@5** and **Precision@5**.

---

## 🛠 Extension Checklist for AI Agents

When implementing a new feature or phase modification:
1. Touch only your assigned phase module inside `src/<phase>/`.
2. Do not write outputs outside of `data/`.
3. Import configuration parameters exclusively from `src.config`.
4. Run `pytest` to confirm 100% test suite pass before marking tasks complete.
