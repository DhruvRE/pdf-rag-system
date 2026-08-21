"""
FastAPI Backend Server for PDF Question-Paper RAG System.
Provides REST API endpoints with structured question metadata, step timeline info,
and serves extracted diagram images for rich LaTeX Web UI rendering.
"""

import os
import json
import re
import math
from fastapi import FastAPI, Query, HTTPException, Response, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Any, Union

from src.embedding.embedder import query_vector_store, get_vector_store
from src.retrieval.retriever import format_rag_context

from src.config import PROJECT_ROOT, PARSED_DIR, WEB_DIR, CONTEXT_PATH, API_HOST, API_PORT
from src.parsing.ai_normalizer import is_instruction_header_ai, extract_options_and_stem

DATA_PARSED_DIR = PARSED_DIR

MANIFEST_CACHE = {}

def get_paper_image_manifest(cls: Any, subj: Any, year: Any, pid: Any) -> dict:
    """Loads and caches image_manifest.json for a paper."""
    key = f"{cls}/{subj}/{year}/{pid}"
    if key in MANIFEST_CACHE:
        return MANIFEST_CACHE[key]
    
    manifest_path = os.path.join(DATA_PARSED_DIR, str(cls), str(subj), str(year), str(pid), "image_manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
                MANIFEST_CACHE[key] = manifest
                return manifest
        except Exception:
            return {}
    return {}


def resolve_image_urls_for_chunk(linked_imgs: list, pid: str, cls: str, subj: str, year: str) -> list[str]:
    """
    Resolves linked image references (placeholder tokens like [IMAGE_PLACEHOLDER_1], relative paths, dicts, or filenames)
    into clean static URLs (/static/parsed/<class>/<subject>/<year>/<paper_id>/images/<filename>).
    """
    if not linked_imgs:
        return []

    manifest = get_paper_image_manifest(cls, subj, year, pid)
    image_urls = []

    for img_ref in linked_imgs:
        if not img_ref:
            continue

        filename = None

        # 1. Handle dictionary or stringified dictionary
        if isinstance(img_ref, dict):
            filename = img_ref.get("filename") or os.path.basename(img_ref.get("url") or img_ref.get("relative_path") or "")
        elif isinstance(img_ref, str):
            img_str = img_ref.strip()
            if img_str.startswith("{") and ("filename" in img_str or "relative_path" in img_str):
                try:
                    import ast
                    d = ast.literal_eval(img_str)
                    if isinstance(d, dict):
                        filename = d.get("filename") or os.path.basename(d.get("url") or d.get("relative_path") or "")
                except Exception:
                    pass

            if not filename:
                # 2. Lookup in image_manifest.json if placeholder token or key
                if img_str in manifest:
                    m_val = manifest[img_str]
                    if isinstance(m_val, dict):
                        filename = m_val.get("filename") or os.path.basename(m_val.get("url") or m_val.get("relative_path") or "")
                    elif isinstance(m_val, str):
                        filename = m_val
                elif img_str.startswith("q") and ".png" in img_str:
                    filename = img_str
                elif img_str.startswith("img_") and ".png" in img_str:
                    filename = img_str
                elif "/" in img_str or "\\" in img_str:
                    filename = os.path.basename(img_str)
                else:
                    filename = img_str

        if filename:
            # Clean up filename if quotes or brackets attached
            filename_str = str(filename).strip("'\"} ")
            url = f"/static/parsed/{cls}/{subj}/{year}/{pid}/images/{filename_str}"
            if url not in image_urls:
                image_urls.append(url)

    return image_urls


app = FastAPI(title="PDF Question-Paper RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


class SearchRequest(BaseModel):
    query: Optional[str] = ""
    top_k: Optional[int] = None
    page: int = 1
    page_size: int = 10
    class_filter: Optional[str] = None
    subject_filter: Optional[str] = None
    type_filter: Optional[str] = None
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


@app.get("/api/filters")
def get_dynamic_filters():
    """Dynamically extracts all available classes, subjects, and question types present in the vector store DB."""
    vs = get_vector_store()
    classes = set()
    subjects = set()
    question_types = set()

    with vs.conn:
        cur = vs.conn.cursor()
        cur.execute("SELECT metadata_json FROM vectors")
        for row in cur.fetchall():
            try:
                meta = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                if meta.get("class"):
                    classes.add(str(meta.get("class")))
                if meta.get("subject"):
                    subjects.add(str(meta.get("subject")))
                q_type = meta.get("question_type")
                if q_type:
                    question_types.add(str(q_type))
            except Exception:
                pass

    sorted_classes = sorted(list(classes), key=lambda x: int(x) if x.isdigit() else x)
    sorted_subjects = sorted(list(subjects))
    sorted_types = sorted(list(question_types))

    return {
        "classes": sorted_classes,
        "subjects": sorted_subjects,
        "question_types": sorted_types
    }


PUA_FONT_MAP = {
    "\uf020": " ", "\uf022": '"', "\uf023": "#", "\uf028": "(", "\uf029": ")",
    "\uf03c": r"\le ", "\uf03e": r"\ge ", "\uf057": r" \Omega ", "\uf05b": "[", "\uf05d": "]",
    "\uf06c": r"\lambda ", "\uf06d": r"\mu ", "\uf070": r"\pi ", "\uf071": r"\theta ", "\uf07b": "{",
    "\uf061": r"\alpha ", "\uf062": r"\beta ", "\uf067": r"\gamma ",
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

SUBPART_LABEL_ONLY_RE = re.compile(
    r"^\s*(?:\([a-eA-E]\)|\((?:i|ii|iii|iv|v|I|II|III|IV|V)\)|[a-eA-E]\.|\b(?:i|ii|iii|iv|v|I|II|III|IV|V)\.)\s*$",
    re.IGNORECASE
)

TRAILING_PROMPT_RE = re.compile(
    r"\n\s*(?:Options?\:?|Select the most appropriate answer[^\n]*|Choose the correct[^\n]*|Read the following[^\n]*)\s*$",
    re.IGNORECASE
)


def format_to_latex(text: str) -> str:
    """Converts mathematical & chemical notation, exponents, units, radicals, fractions, and Greek symbols dynamically to MathJax LaTeX format, cleaning any nested $ delimiters."""
    if not text:
        return ""
    t = text

    # Replace Odia/Tamil fraction font glyphs
    t = re.sub(r"[\u0b39\u0be8][\s\n]*[\u0b36\u0bea]", r"-\\frac{5}{2}", t)

    for k, v in PUA_FONT_MAP.items():
        t = t.replace(k, v)

    # 1. Clean nested '$' markers inside display math '$$ ... $$' blocks & replace underscores
    def fix_display_block(m):
        content = m.group(1).replace("$", "").strip()
        content = re.sub(r"_{2,}", r"\\underline{\\hspace{1.5cm}}", content)
        return f"\n$$\n{content}\n$$\n"

    t = re.sub(r"\$\$\s*(.*?)\s*\$\$", fix_display_block, t, flags=re.DOTALL)

    # 2. Clean nested '$' markers inside single '$ ... $' inline math blocks & replace underscores
    def fix_inline_block(m):
        content = m.group(1).replace("$", "").strip()
        content = re.sub(r"_{2,}", r"\\underline{\\hspace{1.5cm}}", content)
        return f"${content}$"

    t = re.sub(r"(?<!\$)\$([^\$\n]+)\$(?!\$)", fix_inline_block, t)

    # 3. Greek symbols, Delta & Special Math Symbols
    t = t.replace("∆", r"\Delta").replace("𝛱", r"\pi").replace("π", r"\pi")
    t = t.replace("θ", r"\theta").replace("𝜃", r"\theta").replace("Ω", r"\Omega").replace("µ", r"\mu").replace("μ", r"\mu")
    t = (
        t.replace("α", r"\alpha")
        .replace("β", r"\beta")
        .replace("γ", r"\gamma")
        .replace("Α", r"\Alpha")
        .replace("Β", r"\Beta")
        .replace("Γ", r"\Gamma")
    )
    t = t.replace("±", r"\pm").replace("≈", r"\approx").replace("≠", r"\neq").replace("≤", r"\le").replace("≥", r"\ge").replace("∞", r"\infty")

    # 4. Degree symbols (e.g. 135° -> $135^\circ$, 90 deg -> $90^\circ$)
    t = re.sub(r"(?<!\$)\b(\d+)\s*(?:°|deg|\^o)(?!\$)", r"$\1^\\circ$", t)

    # 5. Square roots & Radicals (e.g. √135 -> $\sqrt{135}$)
    t = re.sub(r"(?<!\$)√\s*(\d+|\w+|\([^)]+\))(?!\$)", r"$\\sqrt{\1}$", t)

    # 6. Chemical Notation & Subscripts (e.g. CO2 -> $\text{CO}_2$, H2O -> $\text{H}_2\text{O}$)
    chem_formulas = [
        ("CO2", r"$\text{CO}_2$"), ("O2", r"$\text{O}_2$"), ("H2O", r"$\text{H}_2\text{O}$"),
        ("N2", r"$\text{N}_2$"), ("CH4", r"$\text{CH}_4$"), ("NH3", r"$\text{NH}_3$"),
        ("SO2", r"$\text{SO}_2$"), ("NO2", r"$\text{NO}_2$"), ("H2SO4", r"$\text{H}_2\text{SO}_4$"),
        ("CaCO3", r"$\text{CaCO}_3$"), ("NaCl", r"$\text{NaCl}$"), ("HCl", r"$\text{HCl}$"),
        ("NaOH", r"$\text{NaOH}$"), ("KMnO4", r"$\text{KMnO}_4$"), ("Fe2O3", r"$\text{Fe}_2\text{O}_3$")
    ]
    for orig, repl in chem_formulas:
        if not re.search(r"\$" + orig, t):
            t = re.sub(r"\b" + orig + r"\b", repl, t)

    # 7. Physics & Math Exponents & Units (10-14 -> $10^{-14}$)
    t = re.sub(r"(?<!\$)\b10\-(\d+)\b(?!\$)", r"$10^{-\1}$", t)
    t = re.sub(r"(?<!\$)\b10\^([-\+]?\d+)\b(?!\$)", r"$10^{\1}$", t)

    # 8. Ensure standalone bare TeX commands / superscripts outside math blocks get wrapped in '$ ... $'
    t = re.sub(
        r"(?<!\$)\\(?:frac|sqrt|vec|hat|bar|dot|ddot|int|sum|prod|lim|alpha|beta|gamma|delta|epsilon|theta|lambda|mu|pi|rho|sigma|tau|phi|omega|Delta|Gamma|Theta|Lambda|Sigma|Omega|rightarrow|leftarrow|Rightarrow|Leftarrow|in|notin|subset|cap|cup|times|div|pm|approx|neq|le|ge|circ)\b(?:\{[^{}]*\}|\[[^\[\]]*\])*(?!\$)",
        lambda m: f"${m.group(0)}$",
        t
    )

    has_tex_macro = bool(re.search(r"\\(?:frac|sqrt|vec|hat|bar|dot|ddot|int|sum|prod|lim|alpha|beta|gamma|delta|epsilon|theta|lambda|mu|pi|rho|sigma|tau|phi|omega|Delta|Gamma|Theta|Lambda|Sigma|Omega|rightarrow|leftarrow|Rightarrow|Leftarrow|in|notin|subset|cap|cup|times|div|pm|approx|neq|le|ge|circ)\b", t))
    has_math_super_sub = bool(re.search(r"\b[a-zA-Z0-9]\^(?:\{\d+\}|\d+)\b|\b[a-zA-Z]\_(?:\{[^{}]+\}|\d|[a-zA-Z])\b", t))

    if (has_tex_macro or has_math_super_sub) and not ("$" in t or "\\(" in t or "\\[" in t):
        t = f"${t.strip()}$"

    # 9. Final Pass: Re-verify display math blocks for nested '$'
    t = re.sub(r"\$\$\s*(.*?)\s*\$\$", fix_display_block, t, flags=re.DOTALL)

    return t


def is_assertion_reason(text: str = "", meta_type: str = "") -> bool:
    """Detects whether a question is an Assertion-Reason question."""
    if meta_type and str(meta_type).lower() == "assertion_reason":
        return True
    if not text:
        return False
    lower = text.lower()
    if "assertion" in lower:
        return True
    if "reason" in lower and ("assertion" in lower or "statement" in lower or "given below" in lower or "(r)" in lower):
        return True
    return False


def format_option_for_display(text: str) -> str:
    """Display extracted fractions in compact textbook form, e.g. 3/2."""
    plain_fraction = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"\1/\2", text)
    return format_to_latex(plain_fraction)


def parse_structured_options(options_list: list, doc_text: str = "", meta_type: str = "") -> list:
    """
    Parses raw option strings/dicts into structured choice cards.
    Dynamically supports ANY number of options (2, 3, 4, 5, 8+, True/False, numerical, matching).
    Preserves original labels & options without hardcoding fixed 4-choice limits or overriding custom options.
    """
    if not options_list and is_assertion_reason(doc_text, meta_type):
        return [
            {"label": "A", "text": "Both Assertion (A) and Reason (R) are true and Reason (R) is the correct explanation of Assertion (A).", "latex_text": "Both Assertion (A) and Reason (R) are true and Reason (R) is the correct explanation of Assertion (A)."},
            {"label": "B", "text": "Both Assertion (A) and Reason (R) are true but Reason (R) is not the correct explanation of Assertion (A).", "latex_text": "Both Assertion (A) and Reason (R) are true but Reason (R) is not the correct explanation of Assertion (A)."},
            {"label": "C", "text": "Assertion (A) is true but Reason (R) is false.", "latex_text": "Assertion (A) is true but Reason (R) is false."},
            {"label": "D", "text": "Assertion (A) is false but Reason (R) is true.", "latex_text": "Assertion (A) is false but Reason (R) is true."}
        ]

    if not options_list and doc_text:
        _, extracted_opts = extract_options_and_stem(doc_text)
        if extracted_opts:
            options_list = extracted_opts

    if not options_list:
        return []

    structured = []
    
    for item in options_list:
        if isinstance(item, dict):
            lbl = str(item.get("label", "")).strip().replace("(", "").replace(")", "").replace(".", "")
            txt = str(item.get("text") or item.get("latex_text") or "").strip()
            if txt:
                display_txt = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"\1/\2", txt)
                structured.append({
                    "label": lbl.upper() if len(lbl) == 1 and lbl.isalpha() else lbl,
                    "text": display_txt,
                    "latex_text": format_option_for_display(txt)
                })
        elif isinstance(item, str) and item.strip():
            opt_str = item.strip()
            match = re.match(r"^[\(\[\{]?([a-hA-H0-9]{1,3})[\)\]\}\.\:\-]\s*(.+)$", opt_str)
            if match:
                lbl = match.group(1).strip()
                txt = match.group(2).strip()
                display_txt = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"\1/\2", txt)
                structured.append({
                    "label": lbl.upper() if len(lbl) == 1 and lbl.isalpha() else lbl,
                    "text": display_txt,
                    "latex_text": format_option_for_display(txt)
                })
            else:
                structured.append({
                    "label": f"#{len(structured) + 1}",
                    "text": opt_str,
                    "latex_text": format_to_latex(opt_str)
                })

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
        # Strip generic section instruction headers (e.g. 'Answer the following questions:') via AI/NLP semantic check
        if INSTRUCTION_HEADER_RE.match(l_str) or is_instruction_header_ai(l_str):
            continue
        # Strip [Embedded Diagram Reference: ...] and standalone [IMAGE_PLACEHOLDER_N]
        if l_str.startswith("[Embedded Diagram Reference:") or re.match(r"^\s*\[IMAGE_PLACEHOLDER_\d+\]\s*$", l_str):
            continue
        l_str = re.sub(r"\[IMAGE_PLACEHOLDER_\d+\]", "", l_str).strip()
        l_str = re.sub(r"\[Embedded Diagram Reference:[^\]]*\]", "", l_str).strip()
        if not l_str or INSTRUCTION_HEADER_RE.match(l_str) or is_instruction_header_ai(l_str):
            continue

        # Skip options lines
        # When options have already been structured, their source lines must
        # not remain in the question stem. This is case-insensitive so PDF
        # labels such as (A) also match stored labels such as (a).
        if options_list and re.match(r"^\s*\(?[A-Da-d]\)\s*", l_str):
            continue
        opt_texts = []
        for opt in options_list:
            if isinstance(opt, str):
                opt_texts.append(opt)
            elif isinstance(opt, dict):
                if opt.get("text"):
                    opt_texts.append(str(opt["text"]))
                if opt.get("latex_text"):
                    opt_texts.append(str(opt["latex_text"]))
        if any(ot in line for ot in opt_texts if ot and len(ot) > 2):
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

    formatted_all = []
    for res in all_results:
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

        if not isinstance(linked_imgs, list):
            linked_imgs = [linked_imgs] if linked_imgs else []
        else:
            linked_imgs = list(linked_imgs)

        # Also collect any placeholders embedded directly in document text
        if doc:
            found_placeholders = re.findall(r"\[IMAGE_PLACEHOLDER_\d+\]", doc)
            for ph in found_placeholders:
                if ph not in linked_imgs:
                    linked_imgs.append(ph)

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

        # Smart Image Resolution: Resolve linked images, or manifest fallback if chunk requires image
        req_img = bool(meta.get("requires_image"))
        image_urls = resolve_image_urls_for_chunk(linked_imgs, pid, cls, subj, year)

        # Manifest fallback if question requires image but image_urls is still empty
        if not image_urls and req_img:
            manifest = get_paper_image_manifest(cls, subj, year, pid)
            if manifest:
                for m_val in manifest.values():
                    fn = None
                    if isinstance(m_val, dict):
                        fn = m_val.get("filename") or os.path.basename(m_val.get("url") or m_val.get("relative_path") or "")
                    elif isinstance(m_val, str):
                        fn = m_val
                    if fn:
                        clean_fn = str(fn).strip("'\"} ")
                        url = f"/static/parsed/{cls}/{subj}/{year}/{pid}/images/{clean_fn}"
                        if url not in image_urls:
                            image_urls.append(url)

        is_ar = is_assertion_reason(doc, meta.get("question_type"))
        structured_options = parse_structured_options(options_list, doc, "assertion_reason" if is_ar else meta.get("question_type"))
        q_type = "assertion_reason" if is_ar else (meta.get("question_type") or ("single_choice_mcq" if structured_options else "short_answer"))

        clean_stem, aggregated_subparts = parse_question_blocks(doc, options_list, subparts_list)

        is_diagram = (
            q_type == "diagram_based"
            or meta.get("question_type") == "diagram_based"
            or req_img
            or len(image_urls) > 0
            or len(linked_imgs) > 0
            or "figure" in clean_stem.lower()
            or "diagram" in clean_stem.lower()
            or "[IMAGE_PLACEHOLDER" in doc
        )

        # Apply Question Type Filter if specified
        if req.type_filter and req.type_filter != "all":
            if req.type_filter == "diagram_based":
                if not is_diagram:
                    continue
            elif q_type != req.type_filter and meta.get("question_type") != req.type_filter:
                continue

        if not clean_stem and (image_urls or req_img):
            clean_stem = "Refer to the linked diagram figure below to answer this question."

        if is_ar:
            new_subparts = []
            reason_added = False
            for sub in aggregated_subparts:
                sub_str = str(sub)
                if ("reason" in sub_str.lower() or sub_str.strip().startswith("Reason") or sub_str.strip().startswith("(R)")) and not reason_added:
                    if "reason" not in clean_stem.lower():
                        clean_stem = f"{clean_stem}\n{sub_str}"
                        reason_added = True
                else:
                    new_subparts.append(sub)
            aggregated_subparts = new_subparts

        # Enforce Option vs Subpart Mutual Exclusivity:
        if structured_options and len(structured_options) > 0:
            aggregated_subparts = []

        latex_stem = format_to_latex(clean_stem)

        formatted_all.append({
            "chunk_id": res["chunk_id"],
            "paper_id": pid,
            "class": cls,
            "subject": subj,
            "year": year,
            "question_number": meta.get("question_number"),
            "section": meta.get("section"),
            "question_type": q_type,
            "requires_image": bool(meta.get("requires_image", False)) or (len(image_urls) > 0),
            "difficulty": meta.get("difficulty"),
            "similarity": res.get("similarity", 1.0),
            "content": doc,
            "stem_text": clean_stem,
            "latex_stem": latex_stem,
            "options": structured_options,
            "subparts": [format_to_latex(s) for s in aggregated_subparts],
            "image_urls": image_urls,
            "ai_validated": bool(meta.get("ai_validated", False) or meta.get("corrected", False)),
            "corrected": bool(meta.get("corrected", False))
        })

    total_results = len(formatted_all)

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
    page_items = formatted_all[start_idx:end_idx]

    rag_prompt = format_rag_context(page_items)

    return {
        "query": query_text,
        "page": current_page,
        "page_size": page_size,
        "total_results": total_results,
        "total_pages": total_pages,
        "is_random": is_random,
        "results_count": len(page_items),
        "results": page_items,
        "rag_prompt_context": rag_prompt
    }


@app.get("/api/drafts")
def get_drafts_queue():
    """Returns the list of parsed paper drafts and questions flagged for review with full options & stem details."""
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
                            raw_opts = q.get("options", [])
                            if not raw_opts and q.get("subparts"):
                                for sub in q.get("subparts", []):
                                    if isinstance(sub, dict) and sub.get("options"):
                                        raw_opts = sub.get("options", [])
                                        break
                            
                            stem_txt = q.get("stem_text", "")
                            is_ar = is_assertion_reason(stem_txt, q.get("question_type"))
                            q_type = "assertion_reason" if is_ar else q.get("question_type", "single_choice_mcq")

                            if is_ar:
                                opts_list = parse_structured_options([], stem_txt, "assertion_reason")
                                subparts_list = q.get("subparts", [])
                                new_subparts = []
                                reason_added = False
                                for sub in subparts_list:
                                    sub_txt = sub.get("text", "") if isinstance(sub, dict) else str(sub)
                                    if ("reason" in sub_txt.lower() or sub_txt.strip().startswith("Reason") or sub_txt.strip().startswith("(R)")) and not reason_added:
                                        if "reason" not in stem_txt.lower():
                                            stem_txt = f"{stem_txt}\n{sub_txt}"
                                            reason_added = True
                                    else:
                                        new_subparts.append(sub)
                                q_subparts = new_subparts
                            else:
                                opts_list = []
                                if isinstance(raw_opts, list):
                                    for opt in raw_opts:
                                        if isinstance(opt, dict):
                                            lbl = opt.get("label", "").upper()
                                            txt = opt.get("text", "")
                                            opts_list.append({
                                                "label": lbl,
                                                "text": txt,
                                                "latex_text": format_to_latex(txt)
                                            })
                                        elif isinstance(opt, str):
                                            opts_list.append({
                                                "label": "",
                                                "text": opt,
                                                "latex_text": format_to_latex(opt)
                                            })
                                q_subparts = q.get("subparts", [])

                            flagged_qs.append({
                                "paper_id": pid,
                                "class": cls,
                                "subject": subj,
                                "year": year,
                                "filename": p_info["filename"],
                                "question_number": q.get("question_number", "Q?"),
                                "question_type": q_type,
                                "stem_text": stem_txt,
                                "latex_stem": format_to_latex(stem_txt),
                                "options": opts_list,
                                "subparts": q_subparts,
                                "confidence": conf,
                                "flag_reason": q.get("flag_reason", "Low extraction confidence / Needs manual review"),
                                "ai_validated": bool(q.get("ai_validated", False) or q.get("corrected", False)),
                                "corrected": q.get("corrected", False)
                            })
            except Exception:
                pass
        elif os.path.exists(q_path):
            try:
                with open(q_path, "r", encoding="utf-8") as qf:
                    q_data = json.load(qf)
                for q in q_data.get("questions", []):
                    if not q.get("is_valid", True):
                        raw_stem = q.get("raw_text", "")
                        flagged_qs.append({
                            "paper_id": pid,
                            "class": cls,
                            "subject": subj,
                            "year": year,
                            "filename": p_info["filename"],
                            "question_number": q.get("question_number", "Q?"),
                            "question_type": "unknown",
                            "stem_text": raw_stem,
                            "latex_stem": format_to_latex(raw_stem),
                            "options": [],
                            "subparts": [],
                            "confidence": "low",
                            "flag_reason": "Phantom stem / missing text",
                            "corrected": False
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


class RecreateQuestionRequest(BaseModel):
    paper_id: str
    question_number: str
    stem_text: str
    options: Optional[List[Any]] = None
    class_level: Optional[str] = None
    subject: Optional[str] = None


@app.post("/api/drafts/recreate-question")
def recreate_question_with_ai(req: RecreateQuestionRequest):
    """Uses local Ollama AI model to reconstruct, clean up, and fix question stem, MCQ choice grid, and correct solution."""
    import urllib.request

    opts_lines = []
    if req.options:
        for opt in req.options:
            if isinstance(opt, dict):
                lbl = opt.get("label", "")
                txt = opt.get("text") or opt.get("latex_text") or ""
                opts_lines.append(f"({lbl}) {txt}")
            elif isinstance(opt, str):
                opts_lines.append(opt)
    opts_str = "\n".join(opts_lines) if opts_lines else "N/A"

    subj_str = req.subject or "General Science/Maths"
    cls_str = req.class_level or "10"

    system_prompt = f"""You are an expert CBSE/ICSE Exam Question Proofreader & Curriculum Specialist.
Fix and reconstruct the following examination question ({req.question_number}).
Clean up any OCR typos, fix missing question text, format clear MCQ choice options (A, B, C, D), and provide the correct answer.

Subject: {subj_str} | Class: {cls_str} | Question: {req.question_number}

Raw Question Stem:
{req.question_text}

Raw Choice Options:
{opts_str}

CRITICAL JSON OUTPUT FORMAT:
Return ONLY valid JSON matching this schema:
{{
  "question_number": "{req.question_number}",
  "question_type": "single_choice_mcq",
  "clean_stem": "<Corrected clear question stem>",
  "options": [
    {{"label": "A", "text": "<Option A text>"}},
    {{"label": "B", "text": "<Option B text>"}},
    {{"label": "C", "text": "<Option C text>"}},
    {{"label": "D", "text": "<Option D text>"}}
  ],
  "correct_answer": "Option (X) - <Correct Option Text>",
  "explanation": "<Step-by-step scientific/mathematical solution>"
}}
"""

    from src.segmentation.structured_parser import extract_json_from_ai_text

    ollama_url = "http://localhost:11434/api/generate"
    payload = {
        "model": "qwen3-vl:30b",
        "prompt": system_prompt,
        "stream": False
    }

    try:
        body_bytes = json.dumps(payload).encode('utf-8')
        ollama_req = urllib.request.Request(ollama_url, data=body_bytes, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(ollama_req, timeout=120) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            resp_str = data.get("response", "")
            recreated_json = extract_json_from_ai_text(resp_str)
    except Exception as e:
        # Fallback if Ollama times out or errors
        recreated_json = {
            "question_number": req.question_number,
            "question_type": "single_choice_mcq",
            "clean_stem": req.question_text,
            "options": req.options or [
                {"label": "A", "text": "Option A"},
                {"label": "B", "text": "Option B"},
                {"label": "C", "text": "Option C"},
                {"label": "D", "text": "Option D"}
            ],
            "correct_answer": "Option (A)",
            "explanation": f"AI Recreation Fallback: {str(e)}"
        }

    clean_stem = recreated_json.get("clean_stem") or req.question_text
    recreated_json["latex_stem"] = format_to_latex(clean_stem)
    for opt in recreated_json.get("options", []):
        opt["latex_text"] = format_to_latex(opt.get("text", ""))

    return {
        "status": "success",
        "paper_id": req.paper_id,
        "question_number": req.question_number,
        "recreated_question": recreated_json
    }


class ReplaceQuestionRequest(BaseModel):
    paper_id: str
    question_number: str
    stem_text: str
    options: Optional[List[Any]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None


@app.post("/api/drafts/replace-question")
def replace_question_in_draft(req: ReplaceQuestionRequest):
    """Replaces a question entry in structured_draft.json with approved AI-recreated content."""
    pid = req.paper_id
    if not os.path.exists(CONTEXT_PATH):
        raise HTTPException(status_code=404, detail="context.json not found")

    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        ctx = json.load(f)

    if pid not in ctx.get("papers", {}):
        raise HTTPException(status_code=404, detail=f"Paper ID {pid} not found")

    p_info = ctx["papers"][pid]
    cls = p_info["class"]
    subj = p_info["subject"]
    year = p_info["year"]

    draft_path = os.path.join(DATA_PARSED_DIR, cls, subj, year, pid, "structured_draft.json")
    if not os.path.exists(draft_path):
        raise HTTPException(status_code=404, detail=f"structured_draft.json not found for paper {pid}")

    with open(draft_path, "r", encoding="utf-8") as df:
        d_data = json.load(df)

    replaced = False
    for sec in d_data.get("sections", []):
        for q in sec.get("questions", []):
            if q.get("question_number") == req.question_number:
                q["stem_text"] = req.stem_text
                q["options"] = req.options or q.get("options", [])
                q["correct_answer"] = req.correct_answer
                q["explanation"] = req.explanation
                q["flagged_for_review"] = False
                q["flag_reason"] = None
                q["corrected"] = True
                q["extraction_confidence"] = "high"
                replaced = True
                break

    if replaced:
        with open(draft_path, "w", encoding="utf-8") as df:
            json.dump(d_data, df, indent=2)

    return {
        "status": "success",
        "paper_id": pid,
        "question_number": req.question_number,
        "message": f"Question {req.question_number} replaced & approved successfully in paper {pid}."
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
    options: Optional[List[Any]] = None
    class_level: Optional[str] = None
    subject: Optional[str] = None
    model_name: Optional[str] = "qwen3-vl:30b"


@app.post("/api/explain")
def generate_question_explanation(req: ExplainRequest):
    """Generates step-by-step AI explanation and solution using local Ollama model."""
    import urllib.request

    opts_lines = []
    if req.options:
        for opt in req.options:
            if isinstance(opt, dict):
                lbl = opt.get("label", "")
                txt = opt.get("text") or opt.get("latex_text") or ""
                opts_lines.append(f"({lbl}) {txt}")
            elif isinstance(opt, str):
                opts_lines.append(opt)
    opts_str = "\n".join(opts_lines) if opts_lines else "N/A (Descriptive / Short Answer)"

    subj_str = req.subject or "General Science/Maths"
    cls_str = req.class_level or "10"

    system_prompt = f"""You are an expert CBSE/ICSE Subject Teacher.
Provide a clear, step-by-step mathematical/scientific solution for the following question.
Render all mathematical and scientific formulas using LaTeX syntax (e.g. $E=mc^2$ or $$\\frac{{a}}{{b}}$$).

Subject: {subj_str} | Class: {cls_str}

Question:
{req.question_text}

Options:
{opts_str}

CRITICAL FORMATTING RULES:
1. Put the correct answer on Line 1 formatted EXACTLY as:
   **Correct Answer:** Option (X) - <Full Text of Correct Option>
   (If options are not lettered A/B/C/D, state the exact matching answer text).
2. Follow with a blank line and horizontal rule `---`.
3. Provide a detailed step-by-step solution formatted with Markdown headings (###), bold text (**bold**), bullet points (* point), and LaTeX formulas.
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
        explanation_text = f"""**Correct Answer:** Refer to standard textbook principles for Class {cls_str} {subj_str}.

---

### Step-by-Step Solution & Concept Guide

**Question:** {req.question_text}

*Note: Local Ollama AI response fallback triggered ({str(e)}).*
"""

    latex_explanation = format_to_latex(explanation_text)

    return {
        "status": "success",
        "question_text": req.question_text,
        "explanation": latex_explanation,
        "latex_explanation": latex_explanation,
        "model_used": req.model_name or "qwen3.5:latest"
    }


class RefineRequest(BaseModel):
    paper_id: str

class EmbedPaperRequest(BaseModel):
    paper_id: str


@app.post("/api/upload_pdf")
async def upload_pdf_paper(
    file: UploadFile = File(...),
    class_name: str = Form(...),
    subject: str = Form(...),
    year: str = Form(...),
    pdf_type: str = Form("Question Paper")
):
    """Uploads a PDF file, parses text and images, creates paper record and chunks draft."""
    import hashlib
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    cls = str(class_name).strip().lower().replace("class ", "")
    subj = str(subject).strip().lower().replace(" ", "_")
    yr = str(year).strip()

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    paper_id = hashlib.md5(contents).hexdigest()[:12]

    raw_dir = os.path.join(PROJECT_ROOT, "data", "raw_pdfs", cls, subj, yr)
    os.makedirs(raw_dir, exist_ok=True)
    pdf_dest = os.path.join(raw_dir, f"{paper_id}.pdf")
    with open(pdf_dest, "wb") as f:
        f.write(contents)

    # Register in context.json
    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        ctx = json.load(f)

    ctx.setdefault("papers", {})[paper_id] = {
        "filename": file.filename,
        "relative_path": f"data/raw_pdfs/{cls}/{subj}/{yr}/{paper_id}.pdf",
        "class": cls,
        "subject": subj,
        "year": yr,
        "pdf_type": pdf_type,
        "phase_status": {
            "scrape": "done",
            "parse": "pending",
            "segment": "pending",
            "image_link": "pending",
            "chunk": "pending",
            "embed": "pending"
        }
    }
    with open(CONTEXT_PATH, "w", encoding="utf-8") as f:
        json.dump(ctx, f, indent=2)

    # Run identical manual pipeline sequence
    from src.parsing.parser import parse_paper
    from src.segmentation.segmenter import segment_paper
    from src.image_linking.extractor import extract_and_link_images
    from src.chunking.chunker import chunk_paper

    parsed_path = parse_paper(paper_id)
    if not parsed_path:
        raise HTTPException(
            status_code=422,
            detail=(
                "This PDF does not contain an English text layer that can be "
                "reliably extracted. Upload an English PDF or enable OCR for "
                "scanned/non-English papers."
            )
        )
    segment_paper(paper_id)
    extract_and_link_images(paper_id)
    chunk_paper(paper_id)

    # Load generated chunks.json
    parsed_dir = os.path.join(DATA_PARSED_DIR, cls, subj, yr, paper_id)
    chunks_json_path = os.path.join(parsed_dir, "chunks.json")
    chunks = []
    if os.path.exists(chunks_json_path):
        with open(chunks_json_path, "r", encoding="utf-8") as f:
            cdata = json.load(f)
            chunks = cdata.get("chunks", [])

    images_dir = os.path.join(parsed_dir, "images")
    n_images = len(os.listdir(images_dir)) if os.path.exists(images_dir) else 0

    return {
        "status": "success",
        "paper_id": paper_id,
        "filename": file.filename,
        "class": cls,
        "subject": subj,
        "year": yr,
        "pdf_type": pdf_type,
        "total_questions": len(chunks),
        "total_images": n_images,
        "questions_preview": chunks[:10]
    }


@app.post("/api/refine_context")
def refine_paper_context(req: RefineRequest):
    """AI Context Improvement engine: re-analyzes question stems, options, and image connections."""
    paper_id = req.paper_id
    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        ctx = json.load(f)

    if paper_id not in ctx.get("papers", {}):
        raise HTTPException(status_code=404, detail=f"Paper ID {paper_id} not found.")

    p_info = ctx["papers"][paper_id]
    cls = p_info["class"]
    subj = p_info["subject"]
    yr = p_info["year"]

    parsed_dir = os.path.join(DATA_PARSED_DIR, cls, subj, yr, paper_id)
    chunks_json_path = os.path.join(parsed_dir, "chunks.json")

    if not os.path.exists(chunks_json_path):
        raise HTTPException(status_code=404, detail="chunks.json file not found.")

    with open(chunks_json_path, "r", encoding="utf-8") as f:
        chunks_data = json.load(f)

    chunks = chunks_data.get("chunks", [])
    manifest = get_paper_image_manifest(cls, subj, yr, paper_id)

    from src.segmentation.segmenter import extract_options

    refined_chunks = []
    for chunk in chunks:
        raw_content = chunk.get("content") or chunk.get("raw_text") or chunk.get("stem_text", "")
        
        # 1. Extract options FIRST from raw content
        existing_opts = chunk.get("options", [])
        opt_list = parse_structured_options(existing_opts, raw_content)
        if not opt_list:
            raw_ext = extract_options(raw_content, chunk.get("section", "SECTIONA"), str(chunk.get("question_number", "")))
            if raw_ext:
                opt_list = parse_structured_options([], "\n".join(raw_ext))

        # Deduplicate options list by label A, B, C, D
        unique_opts = []
        seen_labels = set()
        for opt in opt_list:
            if isinstance(opt, dict):
                lbl = str(opt.get("label", "")).upper()
                if lbl and lbl not in seen_labels:
                    seen_labels.add(lbl)
                    unique_opts.append(opt)
            elif isinstance(opt, str) and opt not in unique_opts:
                unique_opts.append(opt)
        opt_list = unique_opts

        # 2. Parse stem & subparts passing opt_list
        clean_stem, subparts = parse_question_blocks(raw_content, opt_list, chunk.get("subparts", []))

        # Filter subparts that duplicate options or contain option header noise
        clean_subparts = []
        for sp in subparts:
            sp_str = str(sp).strip()
            if sp_str.lower() in ("options:", "options", "or") or len(sp_str) < 3:
                continue
            if "Options:" in sp_str:
                sp_str = sp_str.split("Options:")[0].strip()
            if not sp_str:
                continue
            if opt_list and any(sp_str.rstrip(".").endswith(str(opt.get("text", "")).strip()) for opt in opt_list if isinstance(opt, dict)):
                continue
            clean_subparts.append(sp_str)

        linked = chunk.get("linked_images", [])
        if not linked and manifest and ("figure" in clean_stem.lower() or "diagram" in clean_stem.lower() or "given below" in clean_stem.lower() or "graph" in clean_stem.lower()):
            linked = list(manifest.keys())

        # Clean question type
        q_type = "mcq" if len(opt_list) >= 2 else ("short_answer" if not clean_subparts else "descriptive")

        # Skip orphan bare "Options:" chunks and attach options to previous question if needed
        if clean_stem.strip().lower() in ("options:", "options", "or") or len(clean_stem.strip()) < 4:
            if refined_chunks and opt_list:
                if not refined_chunks[-1].get("options"):
                    refined_chunks[-1]["options"] = opt_list
                    refined_chunks[-1]["question_type"] = "mcq"
            continue

        chunk["stem_text"] = clean_stem
        chunk["question_type"] = q_type
        chunk["subparts"] = clean_subparts
        chunk["has_subparts"] = len(clean_subparts) > 0
        chunk["options"] = opt_list
        chunk["linked_images"] = linked
        chunk["requires_image"] = len(linked) > 0
        chunk["context_refined"] = True
        refined_chunks.append(chunk)

    chunks_data["chunks"] = refined_chunks
    with open(chunks_json_path, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, indent=2)

    return {
        "status": "success",
        "paper_id": paper_id,
        "message": f"Successfully refined context for {len(refined_chunks)} questions using AI Normalizer.",
        "questions_preview": refined_chunks[:10]
    }


@app.post("/api/embed_paper")
def embed_paper_to_vector_store(req: EmbedPaperRequest):
    """Commits paper question chunks into LocalVectorStore DB and updates context.json."""
    from src.embedding.embedder import embed_paper_chunks
    paper_id = req.paper_id
    try:
        res = embed_paper_chunks(paper_id)
        return {
            "status": "success",
            "paper_id": paper_id,
            "embedded_count": res.get("total_embedded", 0),
            "message": f"Successfully embedded {res.get('total_embedded', 0)} questions into Vector Store DB."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding error: {str(e)}")


# Mount static routes for extracted diagram PNGs and Web UI
if os.path.exists(DATA_PARSED_DIR):
    app.mount("/static/parsed", StaticFiles(directory=DATA_PARSED_DIR), name="static_parsed")

os.makedirs(WEB_DIR, exist_ok=True)
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
