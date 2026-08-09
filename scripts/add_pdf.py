"""
add_pdf.py — Register a new PDF and embed it into the vector store.

Usage:
    python3 scripts/add_pdf.py \
        --pdf /path/to/your/paper.pdf \
        --class 10 \
        --subject mathematics \
        --year 2024-2025
"""

import os
import sys
import json
import shutil
import hashlib
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parsing.parser import parse_paper
from src.segmentation.segmenter import segment_paper
from src.image_linking.extractor import extract_and_link_images
from src.chunking.chunker import chunk_paper
from src.embedding.embedder import embed_paper_chunks

from src.config import PROJECT_ROOT, CONTEXT_PATH


VALID_SUBJECTS = {
    "mathematics", "physics", "chemistry", "biology",
    "science", "english", "history", "geography",
    "economics", "political_science", "computer_science"
}


def make_paper_id(cls, subject, year, filename):
    key = f"{cls}|{subject}|{year}|{filename}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def register_pdf(pdf_path, cls, subject, year):
    if not os.path.isfile(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    filename = os.path.basename(pdf_path)
    paper_id = make_paper_id(cls, subject, year, filename)

    dest_dir = os.path.join(PROJECT_ROOT, "data", "raw_pdfs", cls, subject, year)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)

    if os.path.abspath(pdf_path) != os.path.abspath(dest_path):
        shutil.copy2(pdf_path, dest_path)
        print(f"Copied -> {dest_path}")

    relative_path = os.path.relpath(dest_path, PROJECT_ROOT)

    with open(CONTEXT_PATH, "r") as f:
        ctx = json.load(f)

    if paper_id in ctx["papers"]:
        status = ctx["papers"][paper_id].get("phase_status", {}).get("embed", "")
        if status == "done":
            print(f"Paper {paper_id} already embedded. Nothing to do.")
            print("To force re-embed: delete data/parsed/<class>/<subject>/<year>/<paper_id>/ and re-run.")
            sys.exit(0)
        print(f"Paper {paper_id} found but embed={status}. Re-running pipeline.")
    else:
        ctx["papers"][paper_id] = {
            "paper_id": paper_id,
            "class": cls, "subject": subject, "year": year,
            "filename": filename, "url": None,
            "relative_path": relative_path, "fixture_path": None,
            "page_count": None, "has_images": None,
            "phase_status": {
                "scrape": "done", "parse": "pending", "segment": "pending",
                "image_link": "pending", "chunk": "pending", "embed": "pending",
                "dedup": "pending", "retrieval": "pending"
            },
            "worker": None, "needs_review": False, "error_reason": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        ctx["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(CONTEXT_PATH, "w") as f:
            json.dump(ctx, f, indent=2)
        print(f"Registered: {paper_id}")

    return paper_id


def run_pipeline(paper_id):
    print("\n[1/5] Parsing PDF...")
    result = parse_paper(paper_id)
    if result == "":
        print("STOPPED: Non-English PDF detected. Only English PDFs are supported.")
        sys.exit(1)

    print("\n[2/5] Segmenting questions...")
    segment_paper(paper_id)

    print("\n[3/5] Linking images...")
    extract_and_link_images(paper_id)

    print("\n[4/5] Chunking...")
    chunk_paper(paper_id)

    print("\n[5/5] Embedding into vector store...")
    res = embed_paper_chunks(paper_id)
    print(f"Embedded {res['total_embedded']} question chunks.")

    print(f"\nDone! Paper {paper_id} is now searchable at http://localhost:8000")


def main():
    parser = argparse.ArgumentParser(description="Add a PDF to the RAG system.")
    parser.add_argument("--pdf",     required=True, help="Path to PDF file")
    parser.add_argument("--class",   required=True, dest="cls", help="Class (e.g. 10, 12)")
    parser.add_argument("--subject", required=True, help="Subject (e.g. mathematics, physics)")
    parser.add_argument("--year",    required=True, help="Year (e.g. 2024-2025)")
    args = parser.parse_args()

    subject = args.subject.lower().replace(" ", "_")
    if subject not in VALID_SUBJECTS:
        print(f"WARNING: '{subject}' is not a standard subject.")
        if input("Continue anyway? [y/N]: ").strip().lower() != "y":
            sys.exit(1)

    if len(args.year) != 9 or args.year[4] != "-":
        print(f"ERROR: Year must be YYYY-YYYY format, got: {args.year}")
        sys.exit(1)

    print(f"\nAdding: {args.pdf}")
    print(f"  Class: {args.cls}  Subject: {subject}  Year: {args.year}\n")

    paper_id = register_pdf(args.pdf, args.cls, subject, args.year)
    run_pipeline(paper_id)


if __name__ == "__main__":
    main()
