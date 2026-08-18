"""
process_single_class6.py — Processes ONLY the Class 6th PDF:
data/raw_pdfs/6/mathematics/2024-2025/question-2464759.pdf

1. Clears existing Vector DB index & previous parsed files.
2. Runs complete 8-Stage Architecture Pipeline for Class 6 Mathematics paper.
3. Embeds Class 6 chunks into LocalVectorStore DB.
"""

import os
import sys
import json
import shutil
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import PROJECT_ROOT, CONTEXT_PATH
DATA_PARSED_DIR = os.path.join(PROJECT_ROOT, "data", "parsed")
from src.parsing.detector import detect_pdf_type, generate_unified_markdown
from src.image_linking.mapper import crop_and_map_images
from src.segmentation.structured_parser import (
    parse_markdown_pass_a,
    audit_extraction_pass_b,
    evaluate_confidence_and_flags,
    ai_arrange_and_validate_questions,
    create_empty_exam_schema
)
from src.chunking.chunker import chunk_paper
from src.embedding.embedder import embed_paper_chunks, get_vector_store


def main():
    print("=== Processing ONLY Class 6 Mathematics PDF ===")
    
    # 1. Clear existing Vector Store database
    vs = get_vector_store()
    vs.clear()
    print("Cleared existing LocalVectorStore database index.")

    # 2. Clear old parsed output directory
    if os.path.exists(DATA_PARSED_DIR):
        print(f"Cleaning old parsed directory at {DATA_PARSED_DIR}...")
        for item in os.listdir(DATA_PARSED_DIR):
            p = os.path.join(DATA_PARSED_DIR, item)
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)

    # 3. Target Paper ID & info for Class 6 Mathematics PDF
    target_pid = "051a5cd17465"
    p_info = {
        "paper_id": target_pid,
        "filename": "question-2464759.pdf",
        "relative_path": "data/raw_pdfs/6/mathematics/2024-2025/question-2464759.pdf",
        "class": "6",
        "subject": "mathematics",
        "year": "2024-2025",
        "phase_status": {}
    }

    cls = p_info["class"]
    subject = p_info["subject"]
    year = p_info["year"]
    abs_pdf_path = os.path.join(PROJECT_ROOT, p_info["relative_path"])

    print(f"\n[Processing Class 6 Paper {target_pid}] {p_info['filename']} ({abs_pdf_path})...")

    parsed_dir = os.path.join(DATA_PARSED_DIR, cls, subject, year, target_pid)
    os.makedirs(parsed_dir, exist_ok=True)

    # --- Stage 0 & 1: PDF Type Detection & Unified Markdown ---
    pdf_type = detect_pdf_type(abs_pdf_path)
    md_dict = generate_unified_markdown(abs_pdf_path)
    markdown_path = os.path.join(parsed_dir, "markdown.md")
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(md_dict["markdown"])

    # --- Stage 2 & 3: Image Cropping & Placeholder Mapping ---
    manifest = crop_and_map_images(abs_pdf_path, parsed_dir)
    manifest_path = os.path.join(parsed_dir, "image_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # --- Stage 4 & 5: Two-Pass Structuring & Validation ---
    pass_a_json = parse_markdown_pass_a(
        markdown_text=md_dict["markdown"],
        image_manifest=manifest,
        subject=subject,
        class_level=cls,
        year=year,
        source_file=p_info["filename"]
    )
    issues = audit_extraction_pass_b(pass_a_json, md_dict["markdown"], manifest)
    structured_draft = evaluate_confidence_and_flags(pass_a_json, issues)

    # Stage 5B: AI Pipeline Chunk Validator & Auto-Arranger (bypassed for deterministic fast processing)
    # structured_draft = ai_arrange_and_validate_questions(structured_draft, max_questions=2)

    draft_path = os.path.join(parsed_dir, "structured_draft.json")
    with open(draft_path, "w", encoding="utf-8") as f:
        json.dump(structured_draft, f, indent=2)

    # --- Stage 6: Update context.json phase status ---
    p_info["phase_status"]["parse"] = "done"
    p_info["phase_status"]["segment"] = "done"
    p_info["phase_status"]["image_link"] = "done"
    p_info["phase_status"]["structured_draft"] = "done"

    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        ctx = json.load(f)
    ctx.setdefault("papers", {})[target_pid] = p_info
    ctx["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(CONTEXT_PATH, "w", encoding="utf-8") as f:
        json.dump(ctx, f, indent=2)

    # --- Stage 7: Chunking & Embeddings ---
    chunk_paper(target_pid)
    embed_res = embed_paper_chunks(target_pid)

    p_info["phase_status"]["chunk"] = "done"
    p_info["phase_status"]["embed"] = "done"
    p_info["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        ctx = json.load(f)
    ctx.setdefault("papers", {})[target_pid] = p_info
    ctx["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(CONTEXT_PATH, "w", encoding="utf-8") as f:
        json.dump(ctx, f, indent=2)

    print(f"\n=======================================================")
    print(f"Class 6 Single Paper Processing Complete!")
    print(f"Paper: {p_info['filename']} ({cls}/{subject}/{year})")
    print(f"PDF Type: {pdf_type} | Images Cropped: {len(manifest)}")
    print(f"Embedded Vector DB Chunks: {embed_res['total_embedded']}")
    print(f"=======================================================\n")


if __name__ == "__main__":
    main()
