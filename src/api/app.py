"""
FastAPI Backend Server for PDF Question-Paper RAG System.
Provides REST API endpoints with structured question metadata, step timeline info,
and serves extracted diagram images for rich LaTeX Web UI rendering.
"""

import os
import json
import re
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
    query: str
    top_k: int = 5
    class_filter: Optional[str] = None
    subject_filter: Optional[str] = None


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
    """Performs semantic search over vector store and returns structured question metadata & image URLs."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query text cannot be empty")

    results = query_vector_store(
        query_text=req.query,
        n_results=req.top_k,
        subject_filter=req.subject_filter if req.subject_filter and req.subject_filter != "all" else None,
        class_filter=req.class_filter if req.class_filter and req.class_filter != "all" else None
    )

    formatted_results = []
    for res in results:
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
        # A question is EITHER an MCQ (has choice options A,B,C,D) OR has subparts, NEVER BOTH!
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
            "difficulty": meta.get("difficulty"),
            "similarity": res.get("similarity", 0.0),
            "content": doc,
            "stem_text": clean_stem,
            "latex_stem": latex_stem,
            "options": structured_options,
            "subparts": [format_to_latex(s) for s in aggregated_subparts],
            "image_urls": image_urls
        })

    rag_prompt = format_rag_context(results)

    return {
        "query": req.query,
        "results_count": len(formatted_results),
        "results": formatted_results,
        "rag_prompt_context": rag_prompt
    }


# Mount static routes for extracted diagram PNGs and Web UI
if os.path.exists(DATA_PARSED_DIR):
    app.mount("/static/parsed", StaticFiles(directory=DATA_PARSED_DIR), name="static_parsed")

os.makedirs(WEB_DIR, exist_ok=True)
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
