"""
reembed_stage_pipeline.py — Runs the complete 8-Stage Architecture Pipeline across all papers in context.json.

Stages executed per paper:
1. Stage 0 & 1: PDF Type Detection (native vs scanned) & Unified Markdown Extraction
2. Stage 2 & 3: Image Cropping, Spatial BBox & Caption Placeholder Mapping
3. Stage 4 & 5: Pass A Unified CBSE Schema Extraction, Pass B Self-Audit, and Confidence Evaluation
4. Stage 6: Saves structured_draft.json and updates context.json
5. Stage 7: Subpart/Question Chunking and LocalVectorStore Embeddings
"""

import os
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import PROJECT_ROOT, CONTEXT_PATH
from src.parsing.detector import detect_pdf_type, generate_unified_markdown
from src.image_linking.mapper import crop_and_map_images
from src.segmentation.structured_parser import (
    parse_markdown_pass_a,
    audit_extraction_pass_b,
    evaluate_confidence_and_flags,
    create_empty_exam_schema
)
from src.chunking.chunker import chunk_paper
from src.embedding.embedder import embed_paper_chunks, get_vector_store


def process_paper_through_8stage_pipeline(paper_id: str, p_info: dict) -> dict:
    """Executes Stages 0 through 7 for a single paper."""
    cls = p_info["class"]
    subject = p_info["subject"]
    year = p_info["year"]
    rel_pdf = p_info["relative_path"]
    abs_pdf_path = os.path.join(PROJECT_ROOT, rel_pdf)

    if not os.path.exists(abs_pdf_path):
        print(f"Skipping {paper_id}: PDF file not found at {abs_pdf_path}")
        return {"paper_id": paper_id, "status": "failed", "reason": "file_not_found"}

    parsed_dir = os.path.join(PROJECT_ROOT, "data", "parsed", cls, subject, year, paper_id)
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

    draft_path = os.path.join(parsed_dir, "structured_draft.json")
    with open(draft_path, "w", encoding="utf-8") as f:
        json.dump(structured_draft, f, indent=2)

    # --- Stage 6: Update context.json phase status ---
    p_info["phase_status"]["parse"] = "done"
    p_info["phase_status"]["segment"] = "done"
    p_info["phase_status"]["image_link"] = "done"
    p_info["phase_status"]["structured_draft"] = "done"

    # --- Stage 7: Chunking & Embeddings ---
    chunk_paper(paper_id)
    embed_res = embed_paper_chunks(paper_id)

    p_info["phase_status"]["chunk"] = "done"
    p_info["phase_status"]["embed"] = "done"
    p_info["updated_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "paper_id": paper_id,
        "status": "success",
        "pdf_type": pdf_type,
        "total_images": len(manifest),
        "embedded_chunks": embed_res["total_embedded"],
        "flagged_issues": len(issues)
    }


def main():
    print("=== Running Complete 8-Stage Architecture Pipeline Re-Embed ===")
    
    # 1. Clear existing Vector Store index
    vs = get_vector_store()
    vs.clear()
    print("Cleared existing LocalVectorStore database index.")

    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        ctx = json.load(f)

    total_embedded = 0
    success_count = 0

    for pid, p_info in ctx.get("papers", {}).items():
        print(f"\n[Processing {pid}] {p_info['filename']} ({p_info['class']}/{p_info['subject']}/{p_info['year']})...")
        res = process_paper_through_8stage_pipeline(pid, p_info)
        if res["status"] == "success":
            success_count += 1
            total_embedded += res["embedded_chunks"]
            print(f" -> OK: {res['embedded_chunks']} chunks embedded ({res['pdf_type']} PDF, {res['total_images']} images mapped, {res['flagged_issues']} audit flags).")

    ctx["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(CONTEXT_PATH, "w", encoding="utf-8") as f:
        json.dump(ctx, f, indent=2)

    print(f"\n=======================================================")
    print(f"8-Stage Pipeline Re-Embed Complete!")
    print(f"Processed: {success_count}/{len(ctx.get('papers', {}))} papers successfully.")
    print(f"Total Vector DB Chunks Embedded: {total_embedded}")
    print(f"=======================================================\n")


if __name__ == "__main__":
    main()
