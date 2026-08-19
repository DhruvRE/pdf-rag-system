"""
debug_parser_chunker.py — Diagnostic script to test Pass A extraction, subpart parsing,
and chunk generation logic for multi-part questions (like Q1 in Class 6 Math).
"""

import os
import sys
import json
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parsing.detector import generate_unified_markdown
from src.segmentation.structured_parser import parse_markdown_pass_a
from src.chunking.chunker import convert_structured_draft_to_questions_dict, create_question_chunks

pdf_path = "data/raw_pdfs/6/mathematics/2024-2025/question-2464759.pdf"

print("--- 1. Unified Markdown Output (Page 1) ---")
md_data = generate_unified_markdown(pdf_path)
lines = md_data["markdown"].split("\n")
print("\n".join(lines[:60]))

print("\n--- 2. Pass A Structuring Output for Q1 ---")
pass_a = parse_markdown_pass_a(md_data["markdown"], {}, "mathematics", "6", "2024-2025", "question-2464759.pdf")
sec_a = pass_a["sections"][0]
q1 = sec_a["questions"][0]

print(f"Q1 Number: {q1.get('question_number')}")
print(f"Q1 Primary Type: {q1.get('question_type')}")
print(f"Q1 Stem: {repr(q1.get('stem_text'))}")

subpart_containers = q1.get("subparts", [])
print(f"\nSubpart Containers Count: {len(subpart_containers)}")

for idx, container in enumerate(subpart_containers):
    print(f"\n[Container {idx+1}]")
    print("  Text:", repr(container.get("text")[:100]))
    print("  Container Options:", container.get("options"))
    nested_subs = container.get("subparts", [])
    print(f"  Nested Subparts ({len(nested_subs)} items):")
    for n_sub in nested_subs:
        print("    Label:", n_sub.get("label"), "| Text:", repr(n_sub.get("text")), "| Options:", n_sub.get("options"))

print("\n--- 3. Chunker Output for Q1 ---")
q_dict = convert_structured_draft_to_questions_dict(pass_a, "051a5cd17465", "6", "mathematics", "2024-2025")
chunks_res = create_question_chunks(q_dict)
q1_chunk = chunks_res["chunks"][0]

print("Chunk ID:", q1_chunk.get("chunk_id"))
print("Chunk Options Count:", len(q1_chunk.get("options", [])))
print("Chunk Options List:", q1_chunk.get("options"))
