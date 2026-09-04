"""
Hybrid AI & Rule-Based Question Structurer & Normalizer.
Combines high-speed layout rules with Local (Ollama) or Cloud (Google Gemini / Mistral) LLMs
to produce 100% clean, noise-free, LaTeX-formatted question objects.

Key entry points:
  - normalize_latex_rules(text)          : fast rule-based LaTeX cleanup
  - enhance_question_with_ai(...)        : LLM-based full structuring
  - ai_split_question_block(block_text)  : strip wrapper instructions and
                                           explode sub-questions (a)/(b)/...
                                           into independent question strings
"""

import urllib.request
import json
import re
from pathlib import Path

from src.config import (
    LLM_PROVIDER,
    CLOUD_PROVIDER,
    OLLAMA_API_URL,
    OLLAMA_MODEL_NAME,
    OLLAMA_API_KEY,
    GOOGLE_API_KEY,
    GEMINI_MODEL_NAME,
    MISTRAL_API_KEY,
    MISTRAL_MODEL_NAME
)

MODEL_NAME = OLLAMA_MODEL_NAME

# Central mathematical symbol mapping
_SYMBOLS_PATH = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "math_symbols.json"
)

with open(_SYMBOLS_PATH, "r", encoding="utf-8") as f:
    _MATH_SYMBOLS = json.load(f)

MATH_SYMBOL_MAP = {}

for category in _MATH_SYMBOLS.values():
    MATH_SYMBOL_MAP.update(category)
    

def normalize_math_symbols(text: str) -> str:
    """Convert known Unicode mathematical symbols to LaTeX."""
    for symbol, latex in MATH_SYMBOL_MAP.items():
        text = text.replace(symbol, latex)

    return text


def normalize_latex_rules(text: str) -> str:
    """Fast deterministic rule-based LaTeX & chemical formula normalizer."""
    if not text:
        return ""
    t = text
    # 0. Strip Object Replacement Box (\ufffc), unknown box (\ufffd), PUA font range (\ue000-\uf8ff), and Indic PUA font glyphs
   # 3. Greek symbols, Delta & Special Math Symbols
    t = t.replace("∆", r"\Delta").replace("𝛱", r"\pi").replace("π", r"\pi")
    t = t.replace("θ", r"\theta").replace("𝜃", r"\theta").replace("Ω", r"\Omega").replace("µ", r"\mu").replace("μ", r"\mu")
    t = t.replace("±", r"\pm").replace("≈", r"\approx").replace("≠", r"\neq").replace("≤", r"\le").replace("≥", r"\ge").replace("∞", r"\infty")
    t = normalize_math_symbols(t)
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
    t = t.replace("±", r"\pm").replace("≈", r"\approx").replace("≠", r"\neq").replace("≤", r"\le").replace("≥", r"\ge").replace("∞", r"\infty")

    # 4. Degree symbols (e.g. 135° -> $135^\circ$)
    t = re.sub(r"(?<!\$)\b(\d+)\s*(?:°|deg|\^o)(?!\$)", r"$\1^\\circ$", t)

    # 5. Radicals (e.g. √135 -> $\sqrt{135}$)
    t = re.sub(r"(?<!\$)√\s*(\d+|\w+|\([^)]+\))(?!\$)", r"$\\sqrt{\1}$", t)

    # 6. Chemical Formulas
    chem_formulas = [
        ("CO2", r"$\text{CO}_2$"), ("O2", r"$\text{O}_2$"), ("H2O", r"$\text{H}_2\text{O}$"),
        ("N2", r"$\text{N}_2$"), ("CH4", r"$\text{CH}_4$"), ("NH3", r"$\text{NH}_3$"),
        ("SO2", r"$\text{SO}_2$"), ("NO2", r"$\text{NO}_2$"), ("H2SO4", r"$\text{H}_2\text{SO}_4$"),
        ("CaCO3", r"$\text{CaCO}_3$"), ("NaCl", r"$\text{NaCl}$"), ("HCl", r"$\text{HCl}$")
    ]
    for orig, repl in chem_formulas:
        if not re.search(r"\$" + orig, t):
            t = re.sub(r"\b" + orig + r"\b", repl, t)

    # 7. Exponents & Orbitals
    t = re.sub(r"(?<!\$)\b10\-(\d+)\b(?!\$)", r"$10^{-\1}$", t)
    t = re.sub(r"(?<!\$)\b10\^([-\+]?\d+)\b(?!\$)", r"$10^{\1}$", t)
    t = re.sub(r"\bt2g\b", r"t_{2g}", t)
    t = re.sub(r"\beg\b", r"e_g", t)

    # 8. Wrap bare LaTeX expressions containing TeX backslashes or mathematical superscripts/subscripts (x^2, x_1), NOT fill-in-the-blank underscores!
    has_tex_macro = bool(re.search(r"\\(?:frac|sqrt|vec|hat|bar|dot|ddot|int|sum|prod|lim|alpha|beta|gamma|delta|epsilon|theta|lambda|mu|pi|rho|sigma|tau|phi|omega|Delta|Gamma|Theta|Lambda|Sigma|Omega|rightarrow|leftarrow|Rightarrow|Leftarrow|in|notin|subset|cap|cup|times|div|pm|approx|neq|le|ge|circ)\b", t))
    has_math_super_sub = bool(re.search(r"\b[a-zA-Z0-9]\^(?:\{\d+\}|\d+)\b|\b[a-zA-Z]\_(?:\{[^{}]+\}|\d|[a-zA-Z])\b", t))

    if (has_tex_macro or has_math_super_sub) and not ("$" in t or "\\(" in t or "\\[" in t):
        t = f"${t.strip()}$"

    # 9. Final Pass: Re-verify display math blocks for nested '$'
    t = re.sub(r"\$\$\s*(.*?)\s*\$\$", fix_display_block, t, flags=re.DOTALL)

    return t


# Model to use for the AI question splitter — lighter/faster than the default embedding model
_SPLIT_MODEL = "qwen3-vl:8b"


def _call_ollama(prompt: str, model: str = None, timeout: int = 3) -> str:
    payload = json.dumps({
        "model": model or OLLAMA_MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if OLLAMA_API_KEY:
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"

    req = urllib.request.Request(OLLAMA_API_URL, data=payload, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
        return data.get("response", "")


def _call_google_gemini(prompt: str) -> str:
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable is not set")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}]
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts:
                return parts[0].get("text", "")
    return ""


def _call_mistral(prompt: str) -> str:
    if not MISTRAL_API_KEY:
        raise ValueError("MISTRAL_API_KEY environment variable is not set")
    
    url = "https://api.mistral.ai/v1/chat/completions"
    payload = json.dumps({
        "model": MISTRAL_MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }).encode("utf-8")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }
    
    req = urllib.request.Request(url, data=payload, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        choices = data.get("choices", [])
        if choices and "message" in choices[0]:
            return choices[0]["message"].get("content", "")

def is_instruction_header_ai(line: str) -> bool:
    """
    Dynamic AI/NLP Semantic Classifier:
    Detects meta-instruction wrapper titles vs actual question prompts,
    handling arbitrary phrasings without requiring exact string matching.
    """
    if not line or not line.strip():
        return False
    
    t = line.strip()

    # Rule 1: Questions with question marks or mathematical equations are real questions
    if '?' in t or re.search(r'=\s*[\d\?\.]', t):
        return False
    
    # Rule 2: Lines ending in standard options like (a), (b) or numbers are not instructions
    if re.search(r'\b[a-d]\)\s+\w+', t, re.IGNORECASE):
        return False

    t_lower = t.lower()

    # Semantic Command Verbs for instructions
    cmd_verbs = (
        'answer', 'solve', 'attempt', 'choose', 'select', 'fill', 'state',
        'read', 'match', 'complete', 'write', 'note', 'directions', 'refer',
        'identify', 'pick', 'give', 'indicate', 'carry'
    )
    
    # Target Section / Meta-Instruction Objects
    target_objs = (
        'following', 'questions', 'question', 'any two', 'any three', 'any four', 'any one', 'any five',
        'all questions', 'below', 'given below', 'true or false', 'true/false', 'blank', 'blanks',
        'passage', 'text', 'options', 'option', 'either', 'statements', 'section', 'part', 'marks each', 'compulsory'
    )

    starts_with_cmd = any(t_lower.startswith(v) for v in cmd_verbs)
    has_target = any(target in t_lower for target in target_objs)
    
    if (starts_with_cmd and has_target) or ('carry' in t_lower and 'mark' in t_lower) or ('all questions' in t_lower):
        if len(t) < 160 and not re.search(r'\b(?:why|how|what|where|when|which|who|calculate|prove|derive|find)\b', t_lower):
            return True

def extract_options_and_stem(text: str) -> tuple[str, list[dict]]:
    """
    Robust Option & Question Stem Extractor:
    Extracts options whether stacked vertically or aligned horizontally on a single line.
    Strips option choices from stem text and returns: (clean_stem_text, list_of_option_dicts)
    """
    if not text:
        return "", []

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    stem_lines = []
    options = []

    mark_junk_re = re.compile(r"^\s*(?:\[\d+\]|\(\d+\)|\b\d+\b)\s*$")
    option_marker_re = re.compile(r"(?<![A-Za-z])(?:\(([A-Da-d1-4])\)|\b([A-Da-d1-4])[\)\.\:])\s*")
    label_map = {"1": "A", "2": "B", "3": "C", "4": "D"}
    current_label = None
    current_parts = []

    def clean_option_value(value: str) -> str:
        cleaned = re.sub(r"[\ufffc\ufffd\ue000-\uf8ff]", "", value)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ;,")
        return cleaned

    def flush_option() -> None:
        nonlocal current_label, current_parts
        if current_label:
            opt_text = clean_option_value(" ".join(current_parts))
            if opt_text:
                options.append({"label": current_label, "text": opt_text})
        current_label = None
        current_parts = []

    for line in lines:
        if mark_junk_re.match(line) and not stem_lines and not current_label:
            continue

        matches = list(option_marker_re.finditer(line))
        if matches:
            leading = line[:matches[0].start()].strip()
            if leading:
                if current_label:
                    current_parts.append(leading)
                elif not options:
                    stem_lines.append(leading)

            for idx, match in enumerate(matches):
                flush_option()
                raw_label = (match.group(1) or match.group(2) or "").upper()
                current_label = label_map.get(raw_label, raw_label)
                part_start = match.end()
                part_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(line)
                option_piece = line[part_start:part_end].strip()
                current_parts = [option_piece] if option_piece else []
            continue

        if current_label:
            current_parts.append(line)
        elif not mark_junk_re.match(line):
            stem_lines.append(line)

    flush_option()

    deduped_options = []
    seen_labels = set()
    for opt in options:
        label = opt["label"]
        if label in seen_labels:
            continue
        seen_labels.add(label)
        deduped_options.append(opt)

    stem = "\n".join(stem_lines).strip()
    return stem, deduped_options


# Lines that are meta-instructions, not actual questions.
# Matches the instruction wrapper at the top of a numbered block.
_WRAPPER_RE = re.compile(
    r"^\s*(?:"
    r"fill\s+in\s+the\s+blank[s]?"
    r"|state\s+whether"
    r"|answer\s+(?:any\s+)?(?:the\s+)?(?:following|all|three|two|one|four|five|\d+)"
    r"|choose\s+the\s+correct"
    r"|select\s+the\s+(?:most\s+)?(?:correct|appropriate)"
    r"|match\s+the\s+following"
    r"|read\s+the\s+(?:following|passage|text)"
    r"|given\s+below\s+(?:are|is)"
    r"|complete\s+the\s+(?:following|sentence|table)"
    r"|write\s+(?:true|false|yes|no|t\s*/\s*f)"
    r"|identify\s+the\s+(?:following|correct)"
    r"|attempt\s+(?:any|all)"
    r"|do\s+(?:any|all)\s+(?:the\s+)?(?:following|\d+)"
    r"|very\s+short\s+answer"
    r"|short\s+answer"
    r"|long\s+answer"
    r"|directions?\s*:"
    r"|note\s*:"
    r")\b",
    re.IGNORECASE,
)

# Sub-part openers: (a), (b), a), a., (i), (ii), i., etc.
_SUBPART_SPLIT_RE = re.compile(
    r"(?m)^\s*(?:\(([a-e])\)|\((i{1,3}v?|vi{0,3}|ix|x|I{1,3}V?|VI{0,3}|IX|X)\)|([a-e])\.|([ivxIVX]{1,4})\.)\s+",
)


# Standalone sub-part label on its own line: (a), (b), (i), (ii) etc.
# These are DIVIDERS — content before (a) = Q1, between (a) and (b) = Q2, etc.
_STANDALONE_LABEL_RE = re.compile(
    r"^\s*(?:\(([a-e])\)|\((i{1,3}v?|vi{0,3}|ix|x|I{1,3}V?|VI{0,3}|IX|X)\)|([a-e])\.\s*)\s*$",
)


def _rule_based_split(block_text: str) -> list[str]:
    """
    Divider-based splitter — works for both normal and inverted MCQ layouts.

    Standalone sub-part labels like (a), (b), (c) on their own lines are
    treated as PURE DIVIDERS regardless of whether they appear before or
    after the question content (handles inverted PDF layouts).

    Steps:
    1. Drop the question-number label line and wrapper instruction.
    2. Split remaining lines into chunks at each standalone label divider.
    3. Clean each chunk (strip URL footers, page numbers, short noise).
    4. Return non-empty chunks as individual question strings.
    """
    lines = [l.strip() for l in block_text.strip().splitlines() if l.strip()]
    if not lines:
        return []

    # Drop question-number label (e.g. "1.", "Q2", "2.")
    _q_label_re = re.compile(r"^(?:Q\.?\s*)?\d{1,3}[\.\:]?\s*$", re.IGNORECASE)
    while lines and _q_label_re.match(lines[0]):
        lines.pop(0)

    # Strip leading wrapper instruction line(s)
    while lines and _WRAPPER_RE.match(lines[0]):
        lines.pop(0)

    if not lines:
        return []

    # --- Split on standalone label dividers ---
    chunks: list[list[str]] = [[]]
    for line in lines:
        if _STANDALONE_LABEL_RE.match(line):
            # This label is a divider — start a new chunk
            chunks.append([])
        else:
            chunks[-1].append(line)

    if len(chunks) == 1:
        # No dividers found — single question
        text = "\n".join(chunks[0]).strip()
        return [text] if text else []

    # Clean each chunk
    results = []
    for chunk_lines in chunks:
        # Strip URL/footer lines
        filtered = [
            l for l in chunk_lines
            if not re.match(r"^https?://", l) and not re.match(r"^\d+\s*/\s*\d+$", l)
        ]
        text = "\n".join(filtered).strip()
        if len(text) >= 10:
            results.append(text)

    return results



def ai_split_question_block(block_text: str, provider: str = None, use_llm: bool = False) -> list[str]:
    """
    Strips meta-instruction wrappers and explodes sub-questions (a)/(b)/...
    into a list of independent question strings.

    Default (use_llm=False): fast rule-based divider approach — works for
    both normal and inverted MCQ layouts without any network call.

    Optional (use_llm=True): calls qwen3-vl:8b via Ollama (slow ~55s/call).
    Only recommended when a cloud LLM is configured.
    """
    if not block_text or not block_text.strip():
        return []

    if use_llm:
        prompt = _SPLIT_PROMPT_TEMPLATE.format(block=block_text.strip())

        # --- Primary: Ollama qwen3-vl:8b ---
        try:
            print(f"  [ai_split] calling qwen3-vl:8b ({len(block_text)} chars)...")
            raw_response = _call_ollama(prompt, model=_SPLIT_MODEL, timeout=3)
            m = re.search(r"\[.*\]", raw_response, re.DOTALL)
            if m:
                items = json.loads(m.group(0))
                if isinstance(items, list):
                    cleaned = _post_process_llm_items(items)
                    if cleaned:
                        print(f"  [ai_split] → {len(cleaned)} question(s)")
                        return cleaned
        except Exception as exc:
            print(f"  [ai_split] LLM failed: {exc} — using rule-based fallback")

    # --- Fallback: rule-based ---
    result = _rule_based_split(block_text)
    return result if result else [block_text.strip()]


# Footer/noise patterns to strip from LLM-returned question text
_FOOTER_RE = re.compile(
    r"https?://\S+|"
    r"\d+\s*/\s*\d+|"           # page numbers like "2 / 4"
    r"\[\d+\]$",                 # trailing mark annotations like [1]
    re.IGNORECASE,
)


def _post_process_llm_items(items: list) -> list[str]:
    """
    Cleans a list of strings returned by the LLM:
    1. Strips URL footers and page number noise.
    2. Removes duplicates (LLM sometimes returns same text for multiple sub-parts).
    3. Drops items shorter than 15 chars (likely parsing artifacts).
    """
    seen = set()
    cleaned = []
    for raw in items:
        text = str(raw).strip()
        # Strip footer noise line by line
        lines = [l for l in text.splitlines() if not _FOOTER_RE.fullmatch(l.strip()) and l.strip()]
        text = "\n".join(lines).strip()
        if len(text) < 15:
            continue
        # Deduplicate on first 80 chars (catches LLM returning same question multiple times)
        key = text[:80]
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


# Prompt retained for future cloud LLM use
_SPLIT_PROMPT_TEMPLATE = """\
You are processing a question block from an Indian school exam paper (PDF-extracted text).

IMPORTANT LAYOUT NOTES:
- Some PDFs have INVERTED MCQ layout: options (a/b/c/d) come BEFORE the question text,
  and the sub-part label like (a), (b), (c) comes AFTER the question text.
  Pattern: [options for this sub-question] → [question text] → [(label)]
- Do NOT carry over options or text from one sub-question to the next.
- Each sub-question's answer choices belong ONLY to that sub-question.

Your job:
1. Strip any meta-instruction wrapper line at the top such as:
   "Fill in the blank", "State whether True or False", "Answer any THREE",
   "Choose the correct option", "Match the following", "Read the following", etc.
   These are NOT questions — they describe the question type.

2. Split into individual independent questions. Each sub-part (a)/(b)/(c)/(i)/(ii) is its own question.
   - For INVERTED layout: the sub-part label (a)/(b) marks the END of a sub-question block,
     so each sub-question = everything between two consecutive labels.
   - For NORMAL layout: the sub-part label (a)/(b) marks the START of a sub-question block.

3. For each sub-question return ONLY its own question text + its own MCQ options (if any).
   - Do NOT prepend text or options from a previous sub-question.
   - Drop sub-part labels like "(a)", "(b)" from the question text.
   - Drop mark annotations like [1], [2], (1 mark).
   - Drop URL footers or page numbers.

4. If the block is already a single standalone question with no sub-parts, return it as a single-element list.

5. Return ONLY a valid JSON array of strings. No explanation, no markdown fences, no extra text.

Block:
{block}

JSON array:"""




def enhance_question_with_ai(raw_text: str, question_num: str = "", use_ollama: bool = False, provider: str = None) -> dict:
    """
    Normalizes raw question text into structured JSON.
    Supports Local (Ollama) or Cloud (Google Gemini / Mistral) LLMs based on configuration or provider override.
    """
    clean_text = normalize_latex_rules(raw_text)

    active_provider = provider if provider else LLM_PROVIDER

    if use_ollama:
        try:
            prompt = f"Format this question as JSON with keys stem_latex, options, subparts. Input:\n{raw_text}"
            res_text = ""

            if active_provider == "cloud":
                if CLOUD_PROVIDER == "mistral":
                    res_text = _call_mistral(prompt)
                else:
                    res_text = _call_google_gemini(prompt)
            else:
                res_text = _call_ollama(prompt)

            m = re.search(r"\{.*\}", res_text, re.DOTALL)
            if m:
                return json.loads(m.group(0))
        except Exception:
            pass

    return {
        "question_number": question_num,
        "clean_full_text": clean_text,
        "latex_stem": clean_text
    }
