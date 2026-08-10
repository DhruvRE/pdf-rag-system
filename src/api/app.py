"""
FastAPI Backend Server for PDF Question-Paper RAG System.
Provides REST API endpoints with structured question metadata, step timeline info,
and serves extracted diagram images for rich LaTeX Web UI rendering.
"""

import os
import json
import re
import math
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List

from src.embedding.embedder import query_vector_store, get_vector_store
from src.retrieval.retriever import format_rag_context

from src.config import PROJECT_ROOT, PARSED_DIR, WEB_DIR, CONTEXT_PATH, API_HOST, API_PORT

DATA_PARSED_DIR = PARSED_DIR


app = FastAPI(title="PDF Question-Paper RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: Optional[str] = ""
    top_k: Optional[int] = None
    page: int = 1
    page_size: int = 10
    class_filter: Optional[str] = None
    subject_filter: Optional[str] = None
    random_sample: bool = False


@app.get("/api/stats")
def get_stats():
    """Returns dataset summary statistics."""
    if not os.path.exists(CONTEXT_PATH):
        raise HTTPException(status_code=404, detail="context.json not found")

    with open(CONTEXT_PATH, 'r', encoding='utf-8') as f:
        ctx = json.load(f)

    vs = get_vector_store()
    total_chunks = vs.count()

    total_images = 0
    papers_summary = []

    for pid, p_info in ctx.get("papers", {}).items():
        cls = p_info["class"]
        subject = p_info["subject"]
        year = p_info["year"]
        img_dir = os.path.join(DATA_PARSED_DIR, cls, subject, year, pid, "images")
        
        n_imgs = len(os.listdir(img_dir)) if os.path.exists(img_dir) else 0
        total_images += n_imgs

        papers_summary.append({
            "paper_id": pid,
            "filename": p_info["filename"],
            "class": cls,
            "subject": subject,
            "year": year,
            "images_count": n_imgs
        })

    return {
        "total_papers": len(ctx.get("papers", {})),
        "total_questions": total_chunks,
        "total_images": total_images,
        "papers": papers_summary
    }


PUA_FONT_MAP = {
    "\uf020": " ", "\uf022": '"', "\uf023": "#", "\uf028": "(", "\uf029": ")",
    "\uf03c": r"\le ", "\uf03e": r"\ge ", "\uf057": r" \Omega ", "\uf05b": "[", "\uf05d": "]",
    "\uf06c": r"\lambda ", "\uf06d": r"\mu ", "\uf070": r"\pi ", "\uf071": r"\theta ", "\uf07b": "{",
    "\uf07d": "}", "\uf0a5": r"\infty ", "\uf0ae": r" \rightarrow ", "\uf0b3": r"\int ", "\uf0c7": r"\times ",
    "\uf0ce": r" \in ", "\uf0e0": r" \rightarrow ", "\uf0e9": "[", "\uf0ea": " ", "\uf0eb": "]",
    "\uf0f9": "[", "\uf0fa": " ", "\uf0fb": "]",
    "\u0b39": "-", "\u0b36": r"\frac{5}{2}",
    "\u0be8": "-", "\u0bea": r"\frac{5}{2}"
}

MARK_JUNK_RE = re.compile(
    r"^\s*(?:\[\s*\]|\(|\)|\[|\]|\,|\'|\"|\`|\d+\s*Marks?|\[\d+\s*Marks?\]|\(\d+\s*Marks?\)|\[\d+\]|\(\d+\)|\d+\s*[\+\:]\s*\d+)\s*$",
    re.IGNORECASE
)

SUBPART_LABEL_ONLY_RE = re.compile(
    r"^\s*(?:\([a-eA-E]\)|\((?:i|ii|iii|iv|v|I|II|III|IV|V)\)|[a-eA-E]\.|\b(?:i|ii|iii|iv|v|I|II|III|IV|V)\.)\s*$",
    re.IGNORECASE
)

TRAILING_PROMPT_RE = re.compile(
    r"\n\s*(?:Options?\:?|Select the most appropriate answer[^\n]*|Choose the correct[^\n]*|Read the following[^\n]*)\s*$",
    re.IGNORECASE
)


def format_to_latex(text: str) -> str:
    """Converts mathematical & chemical notation, exponents, units, radicals, and Greek symbols to MathJax LaTeX format."""
    if not text:
        return ""
    t = text

    # Replace Odia/Tamil fraction font glyphs
    t = re.sub(r"[\u0b39\u0be8][\s\n]*[\u0b36\u0bea]", r"-\\frac{5}{2}", t)

    for k, v in PUA_FONT_MAP.items():
        t = t.replace(k, v)

    # 1. Delta triangle symbol
    t = t.replace("∆", r"$\Delta$")
    
    # 2. Square roots
    t = re.sub(r"√\s*(\d+|\w+)", lambda m: f"$\\sqrt{{{m.group(1)}}}$", t)
    
    # 3. Scientific notation exponents & units: 10-14 -> $10^{-14}$, 1013 -> $10^{13}$, s-1 -> $\text{s}^{-1}$, cm-1 -> $\text{cm}^{-1}$
    t = re.sub(r"\b10\-(\d+)", r"$10^{-\1}$", t)
    t = re.sub(r"\b10(\d{2,})\b", r"$10^{\1}$", t)
    t = re.sub(r"\b([a-zA-Z]+)\-(\d+)\b", lambda m: f"$\\text{{{m.group(1)}}}^{{-{m.group(2)}}}$", t)
    t = re.sub(r"\b([A-Za-z]+)\s*(\d+[\+\-])\b", lambda m: f"$\\text{{{m.group(1)}}}^{{{m.group(2)}}}$", t)
    
    # 4. Chemical orbital terms with word boundaries
    t = re.sub(r"\bt2g\b", r"$t_{2g}$", t)
    t = re.sub(r"\beg\b", r"$e_g$", t)
    
    # 5. Greek symbols & Angles
    t = t.replace("𝛱", r"$\pi$").replace("π", r"$\pi$")
    t = t.replace("θ", r"$\theta$").replace("𝜃", r"$\theta$")
    t = re.sub(r"(\d+)\s*(?:°|deg|\^o)", lambda m: f"${m.group(1)}^\\circ$", t)
    
    # 6. Trigonometric Functions
    t = re.sub(r"\b(sin|cos|tan|cot|sec|cosec)\b\s*([A-Za-z0-9θ𝜃$\\]+)", lambda m: f"$\\text{{{m.group(1)}}}({m.group(2)})$", t)
    
    return t


def parse_structured_options(options_list: list, doc_text: str = "") -> list:
    """Parses raw option strings into structured choice cards, correctly handling Assertion-Reason questions."""
    # Special handling for Assertion-Reason questions
    if "Assertion" in doc_text and "Reason" in doc_text:
        return [
            {
                "label": "A",
                "text": "Both Assertion (A) and Reason (R) are true and Reason (R) is the correct explanation of Assertion (A).",
                "latex_text": "Both Assertion (A) and Reason (R) are true and Reason (R) is the correct explanation of Assertion (A)."
            },
            {
                "label": "B",
                "text": "Both Assertion (A) and Reason (R) are true but Reason (R) is not the correct explanation of Assertion (A).",
                "latex_text": "Both Assertion (A) and Reason (R) are true but Reason (R) is not the correct explanation of Assertion (A)."
            },
            {
                "label": "C",
                "text": "Assertion (A) is true but Reason (R) is false.",
                "latex_text": "Assertion (A) is true but Reason (R) is false."
            },
            {
                "label": "D",
                "text": "Assertion (A) is false but Reason (R) is true.",
                "latex_text": "Assertion (A) is false but Reason (R) is true."
            }
        ]

    full_opts_str = " ".join(options_list) if options_list else ""
    if not full_opts_str:
        return []

    tokens = re.split(r"(\(?\b[A-Da-d][\)\.]\s*)", full_opts_str)
    structured = []
    
    i = 1
    while i < len(tokens) - 1:
        marker = tokens[i].strip()
        val = tokens[i + 1].strip()
        val_clean = re.split(r"\s{2,}|\n", val)[0].strip()
        label = re.sub(r"[^\w]", "", marker).upper()
        if label in {"A", "B", "C", "D"} and val_clean:
            if not val_clean.startswith(("Both", "Assertion", "Reason")):
                structured.append({
                    "label": label,
                    "text": val_clean,
                    "latex_text": format_to_latex(val_clean)
                })
        i += 2
    return structured


def clean_subpart_text(sub_text: str) -> str:
    """Strips trailing mark allocations like '2Marks', '[1Mark]', orphan brackets '[', ']', and merges label headers."""
    lines = [l.strip() for l in sub_text.split("\n") if l.strip()]
    cleaned = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if MARK_JUNK_RE.match(line):
            idx += 1
            continue
        if line in ("'", '"', '`'):
            idx += 1
            continue
        if SUBPART_LABEL_ONLY_RE.match(line) and idx + 1 < len(lines):
            next_l = lines[idx + 1]
            if next_l and not MARK_JUNK_RE.match(next_l) and next_l not in ("'", '"', '`'):
                cleaned.append(f"{line} {next_l}")
                idx += 2
                continue
        cleaned.append(line)
        idx += 1
    return "\n".join(cleaned).strip()


def parse_question_blocks(doc_text: str, options_list: list[str], raw_subparts: list[str]) -> tuple[str, list[str]]:
    """
    Splits raw question document text into:
    1. main_stem: Paragraph context, tables, and instructions BEFORE any subparts.
    2. subparts_blocks: Clean, mark-stripped subpart cards.
    """
    if not doc_text:
        return "", []

    t = doc_text.strip()
    
    # 1. Truncate 'For Visually Impaired Students / Candidates' alternative sections
    t = re.split(r"(?:[\-\s\_\=]{3,}|\n)\s*For\s+(?:Visual|Visually)\s+Impaired", t, flags=re.IGNORECASE)[0].strip()

    # 2. Strip leading question number prefixes ('16.\n', 'Q.16.', 'Q16.', 'Q.11.', '29.', '23.')
    t = re.sub(r"^\s*(?:Q\.?\s*\d{1,3}[\.\:]?|Question\s+\d{1,3}[\.\:]?|\d{1,3}\.|\d{1,3})[\s\n]*", "", t, flags=re.IGNORECASE)

    subpart_start_re = re.compile(
        r"^\s*(?:\([a-eA-E]\)|\((?:i|ii|iii|iv|v|I|II|III|IV|V)\)|[a-eA-E]\.|\b(?:i|ii|iii|iv|v|I|II|III|IV|V)\.)(?:\s+|\:|\.|\n|$)",
        re.IGNORECASE
    )
    or_re = re.compile(r"^\s*(?:\[or\]|or)\s*$", re.IGNORECASE)

    lines = t.split("\n")
    stem_lines = []
    subparts_blocks = []
    current_subpart_lines = []
    in_subparts = False

    for line in lines:
        l_str = line.strip()
        if not l_str or MARK_JUNK_RE.match(l_str):
            continue

        # Strip running page footers
        if re.search(r"P\s*a\s*g\s*e\s*\d+\s*\|\s*\d+", l_str, re.IGNORECASE):
            continue
        # Strip [Embedded Diagram Reference: ...]
        if l_str.startswith("[Embedded Diagram Reference:"):
            continue
        # Skip options lines
        if any(opt in line for opt in options_list):
            continue

        # Standardize [or] -> OR
        if or_re.match(l_str):
            if current_subpart_lines:
                cb = clean_subpart_text("\n".join(current_subpart_lines))
                if cb:
                    subparts_blocks.append(cb)
                current_subpart_lines = []
            subparts_blocks.append("OR")
            in_subparts = True
            continue
            
        # Collapse multi-space tab padding (5+ spaces)
        l_str = re.sub(r"\s{5,}", " ", l_str)

        # Check if line starts a new subpart
        if subpart_start_re.match(l_str):
            in_subparts = True
            if current_subpart_lines:
                cb = clean_subpart_text("\n".join(current_subpart_lines))
                if cb:
                    subparts_blocks.append(cb)
                current_subpart_lines = []
            current_subpart_lines.append(l_str)
        elif in_subparts:
            current_subpart_lines.append(l_str)
        else:
            stem_lines.append(l_str)

    if current_subpart_lines:
        cb = clean_subpart_text("\n".join(current_subpart_lines))
        if cb:
            subparts_blocks.append(cb)

    # Fallback to raw_subparts if no regex subpart markers were matched
    if not subparts_blocks and raw_subparts:
        subparts_blocks = [clean_subpart_text(s) for s in raw_subparts if clean_subpart_text(s)]

    main_stem = "\n".join(stem_lines).strip()
    # Strip trailing instruction/prompt lines (Options:, Select the most appropriate answer...)
    main_stem = re.sub(r"\n[^\n]*(?:select the most appropriate|select the correct|choose the correct)[^\n]*$", "", main_stem, flags=re.IGNORECASE).strip()
    main_stem = re.sub(r"\n\s*Options?\:?\s*$", "", main_stem, flags=re.IGNORECASE).strip()
    return main_stem, subparts_blocks


@app.post("/api/search")
def search_questions(req: SearchRequest):
    """Performs semantic search or browses questions with pagination and optional random sampling."""
    query_text = (req.query or "").strip()
    is_random = req.random_sample or not query_text

    all_results = query_vector_store(
        query_text=query_text,
        n_results=None,
        subject_filter=req.subject_filter if req.subject_filter and req.subject_filter != "all" else None,
        class_filter=req.class_filter if req.class_filter and req.class_filter != "all" else None,
        random_order=is_random
    )

    total_results = len(all_results)

    # Determine pagination page size
    if req.page_size == -1 or req.page_size >= 1000:
        page_size = total_results if total_results > 0 else 10
    elif req.top_k is not None and req.top_k > 0 and req.page_size == 10:
        page_size = req.top_k
    else:
        page_size = max(1, req.page_size)

    total_pages = math.ceil(total_results / page_size) if total_results > 0 else 1
    current_page = max(1, min(req.page, total_pages))

    start_idx = (current_page - 1) * page_size
    end_idx = start_idx + page_size
    page_items = all_results[start_idx:end_idx]

    formatted_results = []
    for res in page_items:
        meta = res.get("metadata", {})
        doc = res.get("document", "")
        pid = meta.get("paper_id")
        cls = meta.get("class")
        subj = meta.get("subject")
        year = meta.get("year")

        linked_imgs_raw = meta.get("linked_images", "[]")
        try:
            linked_imgs = json.loads(linked_imgs_raw) if isinstance(linked_imgs_raw, str) else linked_imgs_raw
        except Exception:
            linked_imgs = []

        options_raw = meta.get("options", "[]")
        try:
            options_list = json.loads(options_raw) if isinstance(options_raw, str) else options_raw
        except Exception:
            options_list = []

        subparts_raw = meta.get("subparts", "[]")
        try:
            subparts_list = json.loads(subparts_raw) if isinstance(subparts_raw, str) else subparts_raw
        except Exception:
            subparts_list = []

        image_urls = []
        for img_rel in linked_imgs:
            filename = os.path.basename(img_rel)
            url = f"/static/parsed/{cls}/{subj}/{year}/{pid}/images/{filename}"
            image_urls.append(url)

        structured_options = parse_structured_options(options_list, doc)
        clean_stem, aggregated_subparts = parse_question_blocks(doc, options_list, subparts_list)

        # Enforce Option vs Subpart Mutual Exclusivity:
        if structured_options and len(structured_options) > 0:
            aggregated_subparts = []

        latex_stem = format_to_latex(clean_stem)

        formatted_results.append({
            "chunk_id": res["chunk_id"],
            "paper_id": pid,
            "class": cls,
            "subject": subj,
            "year": year,
            "question_number": meta.get("question_number"),
            "section": meta.get("section"),
            "question_type": meta.get("question_type") or ("single_choice_mcq" if structured_options else "short_answer"),
            "requires_image": bool(meta.get("requires_image", False)) or (len(image_urls) > 0),
            "difficulty": meta.get("difficulty"),
            "similarity": res.get("similarity", 1.0),
            "content": doc,
            "stem_text": clean_stem,
            "latex_stem": latex_stem,
            "options": structured_options,
            "subparts": [format_to_latex(s) for s in aggregated_subparts],
            "image_urls": image_urls
        })

    rag_prompt = format_rag_context(page_items)

    return {
        "query": query_text,
        "page": current_page,
        "page_size": page_size,
        "total_results": total_results,
        "total_pages": total_pages,
        "is_random": is_random,
        "results_count": len(formatted_results),
        "results": formatted_results,
        "rag_prompt_context": rag_prompt
    }


@app.get("/api/drafts")
def get_drafts_queue():
    """Returns the list of parsed paper drafts and questions flagged for review."""
    if not os.path.exists(CONTEXT_PATH):
        raise HTTPException(status_code=404, detail="context.json not found")

    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        ctx = json.load(f)

    drafts = []
    total_flagged = 0

    for pid, p_info in ctx.get("papers", {}).items():
        cls = p_info["class"]
        subj = p_info["subject"]
        year = p_info["year"]
        draft_path = os.path.join(DATA_PARSED_DIR, cls, subj, year, pid, "structured_draft.json")
        q_path = os.path.join(DATA_PARSED_DIR, cls, subj, year, pid, "questions.json")

        flagged_qs = []
        confidence_summary = {"high": 0, "medium": 0, "low": 0}

        if os.path.exists(draft_path):
            try:
                with open(draft_path, "r", encoding="utf-8") as df:
                    d_data = json.load(df)
                for sec in d_data.get("sections", []):
                    for q in sec.get("questions", []):
                        conf = q.get("extraction_confidence", "high")
                        confidence_summary[conf] = confidence_summary.get(conf, 0) + 1
                        if q.get("flagged_for_review") or conf in ("low", "medium"):
                            flagged_qs.append({
                                "question_number": q.get("question_number"),
                                "question_type": q.get("question_type"),
                                "stem_text": q.get("stem_text", "")[:120],
                                "confidence": conf,
                                "flag_reason": q.get("flag_reason", "Needs manual inspection")
                            })
            except Exception:
                pass
        elif os.path.exists(q_path):
            try:
                with open(q_path, "r", encoding="utf-8") as qf:
                    q_data = json.load(qf)
                for q in q_data.get("questions", []):
                    if not q.get("is_valid", True):
                        flagged_qs.append({
                            "question_number": q.get("question_number"),
                            "question_type": "unknown",
                            "stem_text": q.get("raw_text", "")[:120],
                            "confidence": "low",
                            "flag_reason": "Phantom stem / missing text"
                        })
            except Exception:
                pass

        total_flagged += len(flagged_qs)

        drafts.append({
            "paper_id": pid,
            "filename": p_info["filename"],
            "class": cls,
            "subject": subj,
            "year": year,
            "parse_status": p_info.get("phase_status", {}).get("parse", "pending"),
            "embed_status": p_info.get("phase_status", {}).get("embed", "pending"),
            "confidence_summary": confidence_summary,
            "flagged_questions_count": len(flagged_qs),
            "flagged_questions": flagged_qs
        })

    return {
        "total_drafts": len(drafts),
        "total_flagged_questions": total_flagged,
        "drafts": drafts
    }


class ApproveDraftRequest(BaseModel):
    paper_id: str
    approved_by: Optional[str] = "admin"


@app.post("/api/drafts/approve")
def approve_draft(req: ApproveDraftRequest):
    """Approves a paper draft and marks it ready for indexing."""
    pid = req.paper_id
    if not os.path.exists(CONTEXT_PATH):
        raise HTTPException(status_code=404, detail="context.json not found")

    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        ctx = json.load(f)

    if pid not in ctx.get("papers", {}):
        raise HTTPException(status_code=404, detail=f"Paper ID {pid} not found")

    p_info = ctx["papers"][pid]
    p_info["phase_status"]["review"] = "approved"
    p_info["needs_review"] = False

    with open(CONTEXT_PATH, "w", encoding="utf-8") as f:
        json.dump(ctx, f, indent=2)

    return {
        "status": "success",
        "paper_id": pid,
        "message": f"Draft for paper {pid} approved successfully."
    }


@app.get("/api/dedup")
def get_duplicate_questions():
    """Returns detected duplicate or near-duplicate question pairs across board exam years."""
    from src.dedup.deduplicator import find_duplicate_questions
    duplicates = find_duplicate_questions(similarity_threshold=0.92)
    return {
        "total_duplicate_pairs": len(duplicates),
        "threshold": 0.92,
        "duplicate_pairs": duplicates[:50]
    }


class RemoveDuplicateRequest(BaseModel):
    chunk_id: str


@app.post("/api/dedup/remove")
def remove_duplicate_chunk(req: RemoveDuplicateRequest):
    """Deletes a duplicate question chunk from the vector store database."""
    cid = req.chunk_id
    vs = get_vector_store()
    with vs.conn:
        vs.conn.execute("DELETE FROM vectors WHERE id = ?", (cid,))
        try:
            vs.conn.execute("DELETE FROM vectors_fts WHERE id = ?", (cid,))
        except Exception:
            pass
    return {
        "status": "success",
        "deleted_chunk_id": cid,
        "message": f"Successfully removed duplicate chunk {cid} from vector DB store."
    }


class ExplainRequest(BaseModel):
    question_text: str
    options: Optional[List[str]] = None
    class_level: Optional[str] = None
    subject: Optional[str] = None
    model_name: Optional[str] = "qwen3.5:latest"


@app.post("/api/explain")
def generate_question_explanation(req: ExplainRequest):
    """Generates step-by-step AI explanation and solution using local Ollama model."""
    import urllib.request

    opts_str = ", ".join(req.options) if req.options else "N/A (Descriptive)"
    subj_str = req.subject or "General Science/Maths"
    cls_str = req.class_level or "10"

    system_prompt = f"""You are an expert CBSE/ICSE Subject Teacher.
Provide a clear, step-by-step mathematical/scientific solution for the following question.
Render all mathematical and scientific formulas using LaTeX syntax (e.g. $E=mc^2$ or $$\\frac{{a}}{{b}}$$).
If this is a multiple choice question, clearly state the correct option at the beginning and explain why it is correct.

Subject: {subj_str} | Class: {cls_str}
Question:
{req.question_text}

Options:
{opts_str}
"""

    ollama_url = "http://localhost:11434/api/generate"
    payload = {
        "model": req.model_name or "qwen3.5:latest",
        "prompt": system_prompt,
        "stream": False
    }

    try:
        body_bytes = json.dumps(payload).encode('utf-8')
        ollama_req = urllib.request.Request(ollama_url, data=body_bytes, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(ollama_req, timeout=120) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            explanation_text = data.get("response", "No response generated.")
    except Exception as e:
        # Graceful fallback if Ollama times out or errors
        explanation_text = f"""### Step-by-Step Solution & Concept Guide

**Question:** {req.question_text}

**Correct Answer Identification:**
Refer to standard textbook principles for Class {cls_str} {subj_str}.

*Note: Local Ollama AI response fallback triggered ({str(e)}).*
"""

    latex_explanation = format_to_latex(explanation_text)

    return {
        "status": "success",
        "question_text": req.question_text,
        "explanation": explanation_text,
        "latex_explanation": latex_explanation,
        "model_used": req.model_name or "qwen3.5:latest"
    }


# Mount static routes for extracted diagram PNGs and Web UI
if os.path.exists(DATA_PARSED_DIR):
    app.mount("/static/parsed", StaticFiles(directory=DATA_PARSED_DIR), name="static_parsed")

os.makedirs(WEB_DIR, exist_ok=True)
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
