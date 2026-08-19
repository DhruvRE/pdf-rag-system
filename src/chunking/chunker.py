"""
Phase 5 Chunker: Question-Level Chunking & Metadata Tagging.
Creates standardized question chunks where 1 chunk = 1 question (text + options + linked images)
tagged with class/subject/year/paper_id/question_id metadata.
Outputs chunks.json under data/parsed/<class>/<subject>/<year>/<paper_id>/.
"""

import os
import json
import re
from datetime import datetime, timezone

from src.config import PROJECT_ROOT, CONTEXT_PATH
from src.parsing.ai_normalizer import is_instruction_header_ai, extract_options_and_stem

INSTRUCTION_HEADER_RE = re.compile(
    r"^\s*(?:"
    r"Answer\s+the\s+following\s+questions?\:?|"
    r"Answer\s+any\s+(?:ONE|TWO|THREE|FOUR|FIVE|\d+)\s+(?:of\s+the\s+following\s+)?questions?\:?|"
    r"Attempt\s+any\s+(?:ONE|TWO|THREE|FOUR|FIVE|\d+)\s+(?:of\s+the\s+following\s+)?questions?\:?|"
    r"Fill\s+in\s+the\s+blanks?\s+with[^\n]*|"
    r"State\s+whether\s+each\s+of\s+the\s+following[^\n]*|"
    r"Read\s+the\s+following\s+passage[^\n]*|"
    r"Choose\s+the\s+correct\s+option[^\n]*|"
    r"General\s+Instructions?\:?|"
    r"All\s+questions?\s+are\s+compulsory\.?"
    r")\s*$",
    re.IGNORECASE
)


def clean_instruction_headers(text: str) -> str:
    """Strips generic section instruction titles from question stem text using hybrid AI NLP + regex rules."""
    if not text:
        return ""
    lines = text.splitlines()
    cleaned = []
    for l in lines:
        l_str = l.strip()
        if not l_str:
            continue
        if INSTRUCTION_HEADER_RE.match(l_str) or is_instruction_header_ai(l_str):
            continue
        cleaned.append(l)
    return "\n".join(cleaned).strip()


def build_metadata_chunk_text(cls: str, subject: str, year: str, sec: str, q_num: str, text: str, options: list = None) -> str:
    """Builds a metadata-enriched embedding text block for high-precision vector retrieval."""
    header = f"[Class: {cls} | Subject: {subject.title()} | Year: {year} | Section: {sec} | {q_num}]"
    parts = [header, text.strip()]
    if options:
        opt_str = "\n".join(options) if isinstance(options[0], str) else "\n".join(f"({o.get('label', '')}) {o.get('text', '')}" for o in options)
        parts.append(f"Options:\n{opt_str}")
    return "\n\n".join(parts)


def create_question_chunks(questions_dict: dict) -> dict:
    """
    Transforms segmented questions into standardized RAG chunks with classification metadata.
    Enforces rule: 1 chunk = 1 question / subpart with metadata enrichment.
    """
    paper_id = questions_dict["paper_id"]
    cls = questions_dict.get("class")
    subject = questions_dict.get("subject")
    year = questions_dict.get("year")

    chunks = []
    for q in questions_dict.get("questions", []):
        if not q.get("is_valid", True):
            continue

        q_id = q["question_id"]
        q_num = q["question_number"]
        sec = q.get("section", "GENERAL")
        raw_txt = clean_instruction_headers(q.get("raw_text", ""))
        options = q.get("options", [])
        images = q.get("images", [])
        subparts = q.get("subparts", [])

        # Skip chunks that have no actual question content, options, subparts, or images
        if not raw_txt and not options and not subparts and not images:
            continue

        # Format full chunk content (question text + formatted options)
        formatted_parts = [raw_txt] if raw_txt else []
        if options and not any(opt in raw_txt for opt in (options if isinstance(options[0], str) else [o.get("text", "") for o in options])):
            opt_str = "\n".join(options) if isinstance(options[0], str) else "\n".join(f"({o.get('label', '')}) {o.get('text', '')}" for o in options)
            formatted_parts.append("\nOptions:\n" + opt_str)

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
            "question_type": q.get("question_type", "short_answer"),
            "class": cls,
            "subject": subject,
            "year": year,
            "section": sec,
            "page_num": q.get("page_num"),
            "content": full_content,
            "raw_text": raw_txt,
            "options": options,
            "has_subparts": q.get("has_subparts", False) or len(subparts) > 0,
            "subparts": subparts,
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


def convert_structured_draft_to_questions_dict(draft_json: dict, paper_id: str, cls: str, subject: str, year: str) -> dict:
    """Converts a Stage 4/5 structured_draft.json object into a standardized questions_dict with granular sub-question isolation."""
    questions = []
    for sec in draft_json.get("sections", []):
        sec_id = sec.get("section_id", "GENERAL")
        for q in sec.get("questions", []):
            q_num = q.get("question_number", "Q1")
            parent_stem = q.get("stem_text", "")

            # Check if this question has multi-part sub-questions (e.g. Q1(a), Q1(b), Q1(c)...)
            has_explicit_subquestions = False
            for container in q.get("subparts", []):
                nested_subs = container.get("subparts", [])
                if nested_subs and len(nested_subs) >= 2:
                    has_explicit_subquestions = True
                    first_line = parent_stem.splitlines()[0] if parent_stem else ""
                    if INSTRUCTION_HEADER_RE.match(first_line.strip()):
                        first_line = ""
                    for sub_item in nested_subs:
                        sub_lbl = sub_item.get("label", "").strip()
                        sub_txt = sub_item.get("text", "").strip()
                        sub_txt = clean_instruction_headers(sub_txt)
                        sub_opts = []
                        if sub_item.get("options"):
                            for opt in sub_item["options"]:
                                sub_opts.append(f"({opt.get('label', '')}) {opt.get('text', '')}")
                        
                        clean_lbl = sub_lbl.replace("(", "").replace(")", "").strip().lower()
                        sub_id = f"{q_num.lower()}_{clean_lbl}" if clean_lbl else q_num.lower()
                        sub_num = f"{q_num}{sub_lbl}" if sub_lbl else q_num
                        
                        full_sub_stem = sub_txt
                        if first_line and not sub_txt.startswith(first_line):
                            full_sub_stem = f"{first_line}\n{sub_txt}".strip()
                        
                        full_sub_stem = clean_instruction_headers(full_sub_stem)
                        is_valid = bool(full_sub_stem or sub_opts or sub_item.get("images"))
                        
                        questions.append({
                            "question_id": sub_id,
                            "question_number": sub_num,
                            "section": sec_id,
                            "question_type": sub_item.get("question_type", q.get("question_type", "short_answer")),
                            "raw_text": full_sub_stem,
                            "options": sub_opts,
                            "subparts": [],
                            "has_subparts": False,
                            "images": [],
                            "is_valid": is_valid
                        })

            if not has_explicit_subquestions:
                opts = []
                subs = []
                imgs = []
                for sub in q.get("subparts", []):
                    if sub.get("text"):
                        clean_sub_text = clean_instruction_headers(sub["text"])
                        if clean_sub_text:
                            subs.append(clean_sub_text)
                    if sub.get("options"):
                        for opt in sub["options"]:
                            if isinstance(opt, dict):
                                opts.append(f"({opt.get('label', '')}) {opt.get('text', '')}")
                            else:
                                opts.append(str(opt))
                    if sub.get("image_placeholders"):
                        imgs.extend(sub["image_placeholders"])

                cleaned_parent_stem = clean_instruction_headers(parent_stem)
                
                # If opts is empty, check if parent stem contains inline horizontal options
                q_type = q.get("question_type", "short_answer")
                if not opts and cleaned_parent_stem:
                    clean_stem, extracted_opts = extract_options_and_stem(cleaned_parent_stem)
                    if len(extracted_opts) >= 2:
                        cleaned_parent_stem = clean_stem
                        opts = [f"({o['label']}) {o['text']}" for o in extracted_opts]
                        q_type = "single_choice_mcq"

                is_valid = bool(cleaned_parent_stem or opts or subs or imgs)

                questions.append({
                    "question_id": q_num.lower(),
                    "question_number": q_num,
                    "section": sec_id,
                    "question_type": q_type,
                    "raw_text": cleaned_parent_stem,
                    "options": opts,
                    "subparts": subs,
                    "has_subparts": len(subs) > 0,
                    "images": [{"relative_path": img} for img in imgs],
                    "is_valid": is_valid
                })

    return {
        "paper_id": paper_id,
        "class": cls,
        "subject": subject,
        "year": year,
        "total_questions": len(questions),
        "questions": questions
    }


def chunk_paper(paper_id: str, root_dir: str = PROJECT_ROOT) -> str:
    """
    Reads structured_draft.json (or questions.json) for paper_id, generates question chunks,
    outputs chunks.json, and updates .agent/context.json phase_status.
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
    draft_json_path = os.path.join(parsed_dir, "structured_draft.json")
    questions_json_path = os.path.join(parsed_dir, "questions.json")

    if os.path.exists(questions_json_path):
        with open(questions_json_path, 'r', encoding='utf-8') as f:
            questions_dict = json.load(f)
    elif os.path.exists(draft_json_path):
        with open(draft_json_path, 'r', encoding='utf-8') as f:
            draft_json = json.load(f)
        questions_dict = convert_structured_draft_to_questions_dict(draft_json, paper_id, cls, subject, year)
    else:
        raise FileNotFoundError(f"Neither questions.json nor structured_draft.json found at {parsed_dir}")

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
