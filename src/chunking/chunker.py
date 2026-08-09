"""
Phase 5 Chunker: Question-Level Chunking & Metadata Tagging.
Creates standardized question chunks where 1 chunk = 1 question (text + options + linked images)
tagged with class/subject/year/paper_id/question_id metadata.
Outputs chunks.json under data/parsed/<class>/<subject>/<year>/<paper_id>/.
"""

import os
import json
from datetime import datetime, timezone

from src.config import PROJECT_ROOT, CONTEXT_PATH


def create_question_chunks(questions_dict: dict) -> dict:
    """
    Transforms segmented questions into standardized RAG chunks with classification metadata.
    Enforces rule: 1 chunk = 1 question.
    """
    paper_id = questions_dict["paper_id"]
    cls = questions_dict.get("class")
    subject = questions_dict.get("subject")
    year = questions_dict.get("year")

    chunks = []
    for q in questions_dict.get("questions", []):


        q_id = q["question_id"]
        q_num = q["question_number"]
        sec = q.get("section", "GENERAL")
        raw_txt = q.get("raw_text", "")
        options = q.get("options", [])
        images = q.get("images", [])

        # Format full chunk content (question text + formatted options)
        formatted_parts = [raw_txt]
        if options and not any(opt in raw_txt for opt in options):
            formatted_parts.append("\nOptions:\n" + "\n".join(options))

        full_content = "\n\n".join(formatted_parts)

        # Map linked image relative paths
        linked_image_paths = [img["relative_path"] for img in images] if images else []

        # Simple Bloom's taxonomy difficulty heuristic based on question type
        difficulty = "easy" if len(options) > 0 else ("hard" if len(raw_txt) > 300 or q.get("has_subparts") else "medium")

        chunk_obj = {
            "chunk_id": f"{paper_id}_{q_id}",
            "paper_id": paper_id,
            "question_id": q_id,
            "question_number": q_num,
            "class": cls,
            "subject": subject,
            "year": year,
            "section": sec,
            "page_num": q.get("page_num"),
            "content": full_content,
            "raw_text": raw_txt,
            "options": options,
            "has_subparts": q.get("has_subparts", False),
            "subparts": q.get("subparts", []),
            "has_images": len(linked_image_paths) > 0,
            "linked_images": linked_image_paths,
            "bounding_box": q.get("bounding_box"),
            "difficulty": difficulty
        }
        chunks.append(chunk_obj)

    return {
        "paper_id": paper_id,
        "class": cls,
        "subject": subject,
        "year": year,
        "total_chunks": len(chunks),
        "chunks": chunks
    }


def chunk_paper(paper_id: str, root_dir: str = PROJECT_ROOT) -> str:
    """
    Reads questions.json for paper_id, generates question chunks, outputs chunks.json,
    and updates .agent/context.json phase_status.
    """
    context_path = CONTEXT_PATH if root_dir == PROJECT_ROOT else os.path.join(root_dir, ".agent", "context.json")
    with open(context_path, 'r', encoding='utf-8') as f:

        ctx = json.load(f)

    if paper_id not in ctx["papers"]:
        raise KeyError(f"Paper ID {paper_id} not found in context.json")

    p_info = ctx["papers"][paper_id]
    cls = p_info["class"]
    subject = p_info["subject"]
    year = p_info["year"]

    parsed_dir = os.path.join(root_dir, "data", "parsed", cls, subject, year, paper_id)
    questions_json_path = os.path.join(parsed_dir, "questions.json")

    if not os.path.exists(questions_json_path):
        raise FileNotFoundError(f"questions.json missing at {questions_json_path}. Run Phase 3 segment first.")

    with open(questions_json_path, 'r', encoding='utf-8') as f:
        questions_dict = json.load(f)

    chunks_dict = create_question_chunks(questions_dict)
    chunks_json_path = os.path.join(parsed_dir, "chunks.json")

    with open(chunks_json_path, 'w', encoding='utf-8') as f:
        json.dump(chunks_dict, f, indent=2)

    # Update context.json
    p_info["phase_status"]["chunk"] = "done"
    p_info["updated_at"] = datetime.now(timezone.utc).isoformat()
    ctx["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(context_path, 'w', encoding='utf-8') as f:
        json.dump(ctx, f, indent=2)

    print(f"Chunked paper {paper_id} ({chunks_dict['total_chunks']} chunks) -> {chunks_json_path}")
    return chunks_json_path
