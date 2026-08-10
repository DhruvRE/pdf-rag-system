# PDF Question-Paper RAG & Embedder System

An end-to-end question-paper processing, segmentation, image-linking, chunking, hybrid vector embedding, deduplication, and RAG retrieval system.

---

## 🚀 Key System Features & Latest Upgrades

- **Pass B-0 General-Purpose Source Reconciliation**: Preserves `raw_source_span` for every question to reconcile JSON structure directly against raw source text, fixing OCR spacing glitches (e.g. `(c )`), line-split options, and unattached image placeholders.
- **Pass B-1 & B-2 Question Type Classifier & Validator**: Classifies questions into 11 primary types (`single_choice_mcq`, `assertion_reason`, `diagram_based`, etc.) and secondary flags (`requires_image`, `missing_image_reference`), enforcing type-specific structural rules.
- **Cross-Page Diagram & Code Block Linking**: Links top-of-page code snippets ($y_0 < 150$) across page boundaries to questions at the bottom of preceding pages.
- **Stage 7 RRF Hybrid Search (BM25 FTS5 + Dense Vectors)**: Combines exact keyword matches via SQLite FTS5 with 384-dimensional dense vector embeddings using **Reciprocal Rank Fusion (RRF)**:
  $$\text{RRF Score} = \frac{1}{60 + r_{\text{dense}}} + \frac{1}{60 + r_{\text{sparse}}}$$
- **Dedicated Extraction Quality Benchmark (`tests/test_extraction_quality.py`)**: Granular structural evaluation measuring MCQ option splitting (100%), stem purity (99.75%), PUA font cleanliness (99.88%), option/subpart exclusivity (100%), and diagram attachment accuracy (72.5%).
- **Local Ollama AI Solutions (`/api/explain`)**: Integrates local Ollama (`qwen3.5:latest`) to stream step-by-step LaTeX answers rendered via MathJax.
- **Deduplication Engine & Interactive Web UI (`http://localhost:8000`)**: Features `🔍 Question Search`, `📋 Drafts Review Queue`, and `🔄 Duplicate Detection` tabs with one-click deletion (`/api/dedup/remove`).

---

## 🚀 Setup Guide for New PC

Follow these steps when cloning or pulling this project onto a new PC:

### Step 1: Clone the Repository
```bash
git clone https://github.com/DhruvRE/pdf-rag-system.git
cd pdf-rag-system
```

### Step 2: Set Up Python Virtual Environment (Recommended)
```bash
python3 -m venv venv
source venv/bin/activate
```
*(On Windows PowerShell, use `venv\Scripts\Activate.ps1`)*

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Environment Configuration
Create your local `.env` file from the provided template:
```bash
cp .env.example .env
```
Open `.env` and configure your settings:
- **`PROJECT_ROOT`**: Set your local project path or leave empty for auto-detection.
- **`LLM_PROVIDER`**: Choose `local` (Ollama) or `cloud` (Google Gemini / Mistral).
- **`GOOGLE_API_KEY` / `MISTRAL_API_KEY`**: Set your API key if using cloud models.
- **`OLLAMA_API_URL`**: Ensure Ollama is running if using local model (`http://localhost:11434/api/generate`).

### Step 5: Pipeline Execution & Corpus Setup
To process the complete 25-PDF examination paper dataset:
```bash
# Phase 1: Scrape & validate sample papers
python3 scripts/run_phase.py --phase 1

# Phase 2–7: Run full 8-Stage Architecture Pipeline
python3 scripts/run_phase.py --phase 2
python3 scripts/run_phase.py --phase 3
python3 scripts/run_phase.py --phase 4
python3 scripts/run_phase.py --phase 5
python3 scripts/reembed_stage_pipeline.py
python3 scripts/run_phase.py --phase 7
```

To add and embed a custom question paper PDF:
```bash
python3 scripts/add_pdf.py --pdf /path/to/paper.pdf --class 10 --subject physics --year 2024-2025
```

### Step 6: Start FastAPI Backend Server & Web UI
```bash
python3 -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```
Open your browser at **`http://localhost:8000`** to interact with the LaTeX RAG Web UI.

To stop the running server:
```bash
kill $(lsof -t -i:8000) 2>/dev/null
```

### Step 7: Run Evaluation Test Suite & Quality Benchmarks
```bash
# Unit & Stage Pipeline Tests
python3 tests/test_stage_pipeline.py

# RAG Vector Retrieval Benchmark
python3 tests/test_phase8.py

# Granular Structural Extraction Quality Benchmark
python3 tests/test_extraction_quality.py
```

---

## 🛠 Project Architecture Overview

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
