# PDF Question-Paper RAG & Embedder System

An end-to-end question-paper processing, segmentation, image-linking, chunking, embedding, deduplication, and RAG retrieval system.

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

### Step 5: Initialize & Run Pipeline
To run the full processing pipeline on question papers:
```bash
# Phase 1: Scrape & validate sample papers
python3 scripts/run_phase.py --phase 1

# Process Phase 2 to 8 for a paper or all papers
python3 scripts/run_phase.py --phase 2
python3 scripts/run_phase.py --phase 3
python3 scripts/run_phase.py --phase 4
python3 scripts/run_phase.py --phase 5
python3 scripts/run_phase.py --phase 6
python3 scripts/run_phase.py --phase 7
```

To add and embed a custom question paper PDF:
```bash
python3 scripts/add_pdf.py --pdf /path/to/paper.pdf --class 10 --subject physics --year 2024-2025
```

### Step 6: Start FastAPI Backend Server
```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser at `http://localhost:8000` to interact with the LaTeX RAG Web UI.

### Step 7: Run Test Suite
Verify that all 8 phase tests pass cleanly:
```bash
pytest
```

---

## 🛠 Project Architecture
- **Scraper & Sanity Validator**: Automatic ingestion & sanity validation of question paper PDFs.
- **Layout Parser**: PyMuPDF-based text, bounding box, font, and line structure extraction.
- **Question Segmenter**: Boundary detection across Formats A/B/C, Section MCQ isolation, and LaTeX normalization.
- **Image Linker**: Spatial diagram linking with tiny label glyph filtering.
- **Standardized Chunker**: 1-to-1 question-to-chunk tagging with taxonomy classification metadata.
- **Vector Store & Embedder**: SQLite + NumPy dense vector engine for semantic similarity search.
- **Deduplication Engine**: Pairwise cosine similarity detection for duplicate/near-duplicate questions across papers.
- **FastAPI & RAG Retriever**: REST API and Web UI for semantic retrieval and prompt formatting.
- **Local & Cloud LLM Support**: Dynamic model execution via Ollama (Local), Google Gemini (Cloud), or Mistral AI (Cloud).
