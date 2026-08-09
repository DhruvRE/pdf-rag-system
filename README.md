# PDF Question-Paper RAG & Embedder System

An end-to-end question-paper processing, segmentation, image-linking, chunking, embedding, deduplication, and RAG retrieval system.

## Features
- **Scraper & Sanity Validator**: Automatic ingestion & sanity validation of question paper PDFs.
- **Layout Parser**: PyMuPDF-based text, bounding box, font, and line structure extraction.
- **Question Segmenter**: Boundary detection across Formats A/B/C, Section MCQ isolation, and LaTeX normalization.
- **Image Linker**: Spatial diagram linking with tiny label glyph filtering.
- **Standardized Chunker**: 1-to-1 question-to-chunk tagging with taxonomy classification metadata.
- **Vector Store & Embedder**: SQLite + NumPy dense vector engine for semantic similarity search.
- **Deduplication Engine**: Pairwise cosine similarity detection for duplicate/near-duplicate questions across papers.
- **FastAPI & RAG Retriever**: REST API and Web UI for semantic retrieval and prompt formatting.
- **Local & Cloud LLM Support**: Dynamic model execution via Ollama (Local), Google Gemini (Cloud), or Mistral AI (Cloud).

## Quick Start

### 1. Environment Configuration
Copy the template configuration file and customize your settings in `.env`:
```bash
cp .env.example .env
```

### 2. Run Pipeline Phases
Run individual pipeline phases via CLI:
```bash
# Phase 1: Scrape & validate PDFs
python3 scripts/run_phase.py --phase 1

# Add and process a single custom PDF
python3 scripts/add_pdf.py --pdf /path/to/paper.pdf --class 10 --subject physics --year 2024-2025
```

### 3. Run Test Suite
```bash
pytest
```
