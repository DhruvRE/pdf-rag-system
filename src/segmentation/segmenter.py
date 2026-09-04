"""
Phase 3 Segmenter: Question-Boundary Detection & Text Normalization.
Handles Formats A, B, C, mid-paper subsection headers, font symbol replacements,
universal multi-line subpart block aggregation, mark allocation stripping, and strict Section A MCQ isolation.

Sub-question explosion strategy:
  Each numbered block (Q1, Q2 ...) is forwarded to ai_split_question_block(),
  which uses the configured LLM to dynamically:
    - Strip meta-instruction wrappers ("Fill in the blank", "State whether T/F", etc.)
    - Explode (a)/(b)/(c)/... into independent question strings
  This is PDF-format agnostic and requires no font/bold heuristics.
"""

import os
import re
import json
from datetime import datetime, timezone

from src.config import PROJECT_ROOT, CONTEXT_PATH
from src.parsing.ai_normalizer import ai_split_question_block


SECTION_REGEX = re.compile(
    r"^\s*(?:<b>)?\s*(Section\s*[\-\:\s]*[A-E]|SECTION\s*[\-\:\s]*[A-E]|Direction[\s\:]|ASSERTION\s*[\-\:\s]*REASON|Case\s+Study)",
    re.IGNORECASE
)
INSTRUCTION_HEADER_REGEX = re.compile(
    r"^\s*(?:<b>)?\s*General\s+Instructions",
    re.IGNORECASE
)

# Format A: Q1. / Q.1. / Question 1:
Q_PATTERN_A = re.compile(
    r"^\s*(?:<b>)?\s*(Q\.?\s*(\d{1,3})[\.\:]|Question\s+(\d{1,3})[\.\:])",
    re.IGNORECASE
)
# Format B: 1. / 21. / 38. / 33.a. / "1 Question text" at line start
Q_PATTERN_B = re.compile(
    r"^\s*(?:<b>)?\s*(\d{1,3})(?:\.(?:[a-zA-Z]\.|\s+|$)|\)\s+|(?=\s+[A-Z(]))"
)
# Format C: Standalone integer line '1', '2', '21'
Q_PATTERN_C = re.compile(r"^\s*(\d{1,2})\s*$")

HEADER_FOOTER_RE = re.compile(r"Class[\-\s]*XII|Class[\-\s]*X|Sample\s+Paper|Page\s+\d+\s+of\s+\d+|P\s*a\s*g\s*e\s*\d+\s*\|\s*\d+", re.IGNORECASE)
PAGE_NUM_RE = re.compile(r"^(Page\s*\d+|\d+\s*of\s*\d+)$", re.IGNORECASE)

MARK_JUNK_RE = re.compile(
    r"^\s*(?:\[\s*\]|\(|\)|\[|\]|\,|\'|\"|\`|\d+\s*Marks?|\[\d+\s*Marks?\]|\(\d+\s*Marks?\)|\[\d+\]|\(\d+\))\s*$",
    re.IGNORECASE
)

SUBPART_LABEL_ONLY_RE = re.compile(
    r"^\s*(?:\([a-eA-E]\)|\((?:i|ii|iii|iv|v|I|II|III|IV|V)\)|[a-eA-E]\.|\b(?:i|ii|iii|iv|v|I|II|III|IV|V)\.)\s*$",
    re.IGNORECASE
)

SUBPART_START_RE = re.compile(
    r"^\s*(?:\([a-eA-E]\)|\((?:i|ii|iii|iv|v|I|II|III|IV|V)\)|[a-eA-E]\.|\b(?:i|ii|iii|iv|v|I|II|III|IV|V)\.)(?:\s+|\:|\.|\n|$)",
    re.IGNORECASE
)

OR_RE = re.compile(r"^\s*(?:\[or\]|or)\s*$", re.IGNORECASE)


PUA_FONT_MAP = {
    "\uf020": " ", "\uf022": '"', "\uf023": "#", "\uf028": "(", "\uf029": ")",
    "\uf03c": "≤", "\uf03e": "≥", "\uf057": " Ω ", "\uf05b": "[", "\uf05d": "]",
    "\uf06c": "λ", "\uf06d": "μ", "\uf070": "π", "\uf071": "θ", "\uf07b": "{",
    "\uf061": "α", "\uf062": "β", "\uf067": "γ",
    "\uf07d": "}", "\uf0a5": "∞", "\uf0ae": " → ", "\uf0b3": "∫", "\uf0c7": "×",
    "\uf0ce": " ∈ ", "\uf0e0": " → ", "\uf0e9": "[", "\uf0ea": " ", "\uf0eb": "]",
    "\uf0f9": "[", "\uf0fa": " ", "\uf0fb": "]",
}

# Indic script unicode blocks to strip from English-only corpus.
# Covers: Devanagari, Bengali, Gurmukhi, Gujarati, Oriya/Odia, Tamil,
# Telugu, Kannada, Malayalam, Sinhala, Thai, Myanmar, Tibetan.
INDIC_SCRIPT_RE = re.compile(
    r"[\u0900-\u097f"   # Devanagari (Hindi, Marathi, Sanskrit)
    r"\u0980-\u09ff"   # Bengali
    r"\u0a00-\u0a7f"   # Gurmukhi (Punjabi)
    r"\u0a80-\u0aff"   # Gujarati
    r"\u0b00-\u0b7f"   # Oriya / Odia
    r"\u0b80-\u0bff"   # Tamil
    r"\u0c00-\u0c7f"   # Telugu
    r"\u0c80-\u0cff"   # Kannada
    r"\u0d00-\u0d7f"   # Malayalam
    r"\u0d80-\u0dff"   # Sinhala
    r"\u0e00-\u0e7f"   # Thai
    r"\u0e80-\u0eff"   # Lao
    r"\u0f00-\u0fff"   # Tibetan
    r"\u1000-\u109f]"  # Myanmar
)

# Some bilingual PDFs encode Indic text as private-use glyphs instead of real
# Unicode. These cannot be rendered or searched reliably; the corresponding
# English page is processed instead.
PRIVATE_FONT_GLYPH_RE = re.compile(r"[\ue000-\uf8ff]")
PRIVATE_FONT_THRESHOLD = 0.20

# A line is "Indic-contaminated" if more than 20% of its non-space chars are Indic.
INDIC_THRESHOLD = 0.20


def _is_indic_line(line: str) -> bool:
    """Returns True if the line is dominated by Indic-script characters."""
    stripped = line.replace(" ", "")
    if not stripped:
        return False
    indic_chars = len(INDIC_SCRIPT_RE.findall(stripped))
    return (indic_chars / len(stripped)) > INDIC_THRESHOLD


def is_english_dominant(text: str) -> bool:
    """Returns True if the text is predominantly English/Latin (safe to process).
    Used to skip entire PDFs that are written in Hindi or other Indic languages."""
    if not text.strip():
        return False
    # Count printable non-space chars
    total = sum(1 for c in text if c.strip() and not c.isspace())
    if total == 0:
        return False
    indic = len(INDIC_SCRIPT_RE.findall(text))
    private_font = len(PRIVATE_FONT_GLYPH_RE.findall(text))
    # If more than 30% of content is Indic script, or 20% is undecodable
    # private-font text, do not use it as the English searchable corpus.
    return (indic / total) < 0.30 and (private_font / total) < PRIVATE_FONT_THRESHOLD


def normalize_and_clean_lines(lines: list[str]) -> list[str]:
    """
    Normalizes PDF private font encodings, strips running page headers/footers,
    merges single-character vertical equation fragments, and removes non-printable boxes.
    """
    raw_text = "\n".join(lines)
    # Remove Odia/Tamil fraction PUA glyph pairs before general strip
    t = re.sub(r"[\u0b39\u0be8][\s\n]*[\u0b36\u0bea]", r"-\\frac{5}{2}", raw_text)
    # Replace private math font encodings
    t = t.replace("", "=").replace("", "+").replace("", "-").replace("", "×").replace("", "÷")
    for k, v in PUA_FONT_MAP.items():
        t = t.replace(k, v)
    # Any remaining PUA glyph has no reliable Unicode meaning. It belongs to a
    # private-font language page that is filtered before segmentation.
    t = PRIVATE_FONT_GLYPH_RE.sub("", t)
    # Remove non-printable boxes & zero-width spaces
    t = re.sub(r"[\u25a0-\u25ff\ufffd\u200b]", "", t)
    # Strip ALL remaining Indic-script characters (English-only corpus)
    t = INDIC_SCRIPT_RE.sub("", t)

    split_lines = [l.strip() for l in t.split("\n") if l.strip()]
    clean_lines = []

    for line in split_lines:
        # Skip lines still dominated by Indic script after PUA conversion
        if _is_indic_line(line):
            continue
        # Strip running document headers/footers
        if HEADER_FOOTER_RE.search(line):
            continue
        if PAGE_NUM_RE.match(line):
            continue
        if MARK_JUNK_RE.match(line):
            continue
        clean_lines.append(line)

    # Merge vertical short equation & symbol fragments
    merged_lines = []
    idx = 0
    while idx < len(clean_lines):
        line = clean_lines[idx]
        if len(line) <= 3 and re.match(r"^[0-9A-Za-z\=\+\-\/\*\s\(\)]+$", line):
            buf = [line]
            j = idx + 1
            while j < len(clean_lines) and len(clean_lines[j]) <= 3 and re.match(r"^[0-9A-Za-z\=\+\-\/\*\s\(\)]+$", clean_lines[j]):
                buf.append(clean_lines[j])
                j += 1
            if len(buf) > 1:
                merged_lines.append(" ".join(buf))
                idx = j
                continue
        merged_lines.append(line)
        idx += 1

    return merged_lines


# Verbs that indicate a line is a question/instruction, not an MCQ option
OPTION_INVALID_VERBS_RE = re.compile(
    r'^(?:calculate|define|state|find|write|explain|identify|draw|name|give|derive|'
    r'determine|show|prove|list|describe|justify|evaluate|compare|distinguish|compute|'
    r'what|why|how|when|where|which of the two|one of the|out of|answer the|read the)',
    re.IGNORECASE
)

OPTION_MARKER_RE = re.compile(r"(?<![A-Za-z])\(?([A-Da-d])\)\s*")


def _clean_option_value(value: str) -> str:
    text = value
    text = text.replace("", "=").replace("", "+").replace("", "-").replace("", "×").replace("", "÷")
    for k, v in PUA_FONT_MAP.items():
        text = text.replace(k, v)
    text = INDIC_SCRIPT_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" ;,")
    return text


def _extract_multiline_options(raw_text: str) -> list[str]:
    """
    Extracts A-D options even when formula text is emitted on separate lines.
    This is common in math PDFs where superscripts, fractions, and matrix cells
    are independent PDF spans.
    """
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    collected: list[tuple[str, str]] = []
    current_label: str | None = None
    current_parts: list[str] = []

    def flush_current() -> None:
        nonlocal current_label, current_parts
        if current_label:
            value = _clean_option_value(" ".join(current_parts))
            if value:
                collected.append((current_label.lower(), value))
        current_label = None
        current_parts = []

    for line in lines:
        matches = list(OPTION_MARKER_RE.finditer(line))
        if matches:
            leading = line[:matches[0].start()].strip()
            if current_label and leading:
                current_parts.append(leading)

            for idx, match in enumerate(matches):
                flush_current()
                current_label = match.group(1).lower()
                part_start = match.end()
                part_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(line)
                option_piece = line[part_start:part_end].strip()
                current_parts = [option_piece] if option_piece else []
            continue

        if current_label:
            if Q_PATTERN_A.search(line) or SECTION_REGEX.search(line):
                flush_current()
                continue
            current_parts.append(line)

    flush_current()

    by_label: dict[str, str] = {}
    for label, value in collected:
        by_label.setdefault(label, value)

    if all(label in by_label for label in ("a", "b", "c", "d")):
        return [f"({label}) {by_label[label]}" for label in ("a", "b", "c", "d")]
    return []

# Section header lines that bleed into the last question of a section
SECTION_HDR_BLEED_RE = re.compile(
    r'\n\s*(?:SECTION\s*[\-\u2013\u2014]\s*[A-E]|Q\.?\s*(?:No\.?)?\s*\d+\s*to\s*\d+'
    r'|Questions?\s+\d+\s*(?:to|-)\s*\d+)[^\n]*$',
    re.IGNORECASE
)


def extract_options(raw_text: str, section: str, question_number: str = "") -> list[str]:
    """Extracts MCQ options ONLY for genuine multiple-choice questions in Section A.
    Enforces: exactly 4 options, each <= 100 chars, none starting with an instruction verb.
    Returns [] for descriptive, case-study, assertion-reason (those use auto-injected choices)."""

    # Assertion-Reason: always return standard CBSE 4 choices, skip PDF option parsing
    if "Assertion" in raw_text and "Reason" in raw_text:
        return [
            "(a) Both Assertion (A) and Reason (R) are true and Reason (R) is the correct explanation of Assertion (A).",
            "(b) Both Assertion (A) and Reason (R) are true but Reason (R) is not the correct explanation of Assertion (A).",
            "(c) Assertion (A) is true but Reason (R) is false.",
            "(d) Assertion (A) is false but Reason (R) is true."
        ]

    # Non-MCQ section types: always empty
    if any(kw in raw_text for kw in ("Answer the following", "Read the following", "Case Study")):
        return []

    sec_clean = section.upper().replace(" ", "").replace("-", "")
    q_val = int(re.sub(r"\D", "", question_number)) if re.sub(r"\D", "", question_number) else 1

    # Only Section A (Q1-Q20) can be MCQ
    in_mcq_section = sec_clean in {"SECTIONA", "MCQ", "DIRECTION:"} or q_val <= 20
    in_desc_section = any(s in sec_clean for s in ("SECTIONB", "SECTIONC", "SECTIOND", "SECTIONE", "CASESTUDY"))
    # Some bilingual papers repeat Section A after another-language pages, and
    # their running section label can be stale. Questions 1–20 remain MCQs.
    if not in_mcq_section or (in_desc_section and q_val > 20):
        return []

    multiline_choices = _extract_multiline_options(raw_text)
    if len(multiline_choices) == 4:
        return multiline_choices

    # Split on option markers: (a), (b), A), A. etc — but NOT (A) inside Assertion text
    # Use lookahead to avoid matching Assertion(A)/Reason(R) patterns
    tokens = re.split(r"(?<![A-Za-z])(?:\(?\b([A-Da-d])[\)\.]\s*)(?!\s*(?:ssert|eason|oth|nd|r |s |he ))",
                      raw_text)

    choices = []
    for i, tok in enumerate(tokens):
        if not tok:
            continue
        if re.match(r'^[A-Da-d]$', tok.strip()):  # this is a captured label group
            if i + 1 < len(tokens):
                val = tokens[i + 1].strip()
                # Take only first line of value (before any whitespace cluster or newline)
                val_first_line = re.split(r'\s{3,}|\n', val)[0].strip()
                if not val_first_line:
                    continue
                # Reject if too long (not a real MCQ choice)
                if len(val_first_line) > 100:
                    continue
                # Reject if starts with an instruction verb
                if OPTION_INVALID_VERBS_RE.match(val_first_line):
                    continue
                # One-digit signed numbers are valid MCQ answers, e.g. (B) 8.
                alphanum = re.sub(r'[^a-zA-Z0-9]', '', val_first_line)
                is_numeric_option = bool(re.fullmatch(r"[−–-]?\s*\d+(?:\.\d+)?", val_first_line))
                if len(alphanum) < 2 and not is_numeric_option:
                    continue
                label = tok.strip().lower()
                choices.append(f"({label}) {val_first_line}")

    # Only accept if we got exactly 4 valid distinct choices
    if len(choices) == 4 and len(set(c[1] for c in choices)) == 4:  # distinct labels
        return choices

    # Fallback: try simpler split pattern for papers using A) B) C) D) format
    alt_tokens = re.split(r'(?:^|\s)([A-Da-d][\)\.]\s)', raw_text, flags=re.MULTILINE)
    alt_choices = []
    for i in range(1, len(alt_tokens) - 1, 2):
        label_part = alt_tokens[i].strip()
        val_part = alt_tokens[i + 1].strip() if i + 1 < len(alt_tokens) else ""
        val_first = re.split(r'\s{3,}|\n|(?=[A-D][\)\.])', val_part)[0].strip()
        if not val_first or len(val_first) > 100:
            continue
        if OPTION_INVALID_VERBS_RE.match(val_first):
            continue
        alphanum = re.sub(r'[^a-zA-Z0-9]', '', val_first)
        is_numeric_option = bool(re.fullmatch(r"[−–-]?\s*\d+(?:\.\d+)?", val_first))
        if len(alphanum) < 2 and not is_numeric_option:
            continue
        alt_choices.append(f"{label_part} {val_first}")

    if len(alt_choices) == 4:
        return alt_choices

    # Could not reliably extract 4 options — return empty (render as descriptive)
    return []


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


def parse_question_blocks_from_lines(cleaned_lines: list[str], options: list[str]) -> tuple[str, list[str]]:
    """
    Universally splits question lines into:
    1. main_stem_text: Everything before the first subpart marker ((a), (i), (I))
    2. subparts: Complete multi-line subpart blocks ((a)..., (b)..., (c)...) with isolated OR badges.
    """
    stem_lines = []
    subparts_blocks = []
    current_subpart_lines = []
    in_subparts = False

    for line in cleaned_lines:
        l_str = line.strip()
        if not l_str or MARK_JUNK_RE.match(l_str):
            continue

        if any(opt in line for opt in options):
            continue

        if OR_RE.match(l_str):
            if current_subpart_lines:
                raw_block = "\n".join(current_subpart_lines).strip()
                cleaned_block = clean_subpart_text(raw_block)
                if cleaned_block:
                    subparts_blocks.append(cleaned_block)
                current_subpart_lines = []
            subparts_blocks.append("OR")
            in_subparts = True
            continue

        if SUBPART_START_RE.match(l_str):
            in_subparts = True
            if current_subpart_lines:
                raw_block = "\n".join(current_subpart_lines).strip()
                cleaned_block = clean_subpart_text(raw_block)
                if cleaned_block:
                    subparts_blocks.append(cleaned_block)
                current_subpart_lines = []
            current_subpart_lines.append(l_str)
        elif in_subparts:
            current_subpart_lines.append(l_str)
        else:
            stem_lines.append(l_str)

    if current_subpart_lines:
        raw_block = "\n".join(current_subpart_lines).strip()
        cleaned_block = clean_subpart_text(raw_block)
        if cleaned_block:
            subparts_blocks.append(cleaned_block)

    main_stem = "\n".join(stem_lines).strip()
    return main_stem, subparts_blocks


def restore_spatial_fractions(lines: list[str], bboxes: list[list]) -> list[str]:
    """Rebuild fractions whose denominators are separate, lower-positioned PDF lines."""
    items = [
        {"text": str(text).strip(), "bbox": bbox, "used": False}
        for text, bbox in zip(lines, bboxes)
    ]

    for denominator in items:
        denom_text = denominator["text"]
        if not re.fullmatch(r"\d+", denom_text):
            continue

        dx0, dy0, _, _ = denominator["bbox"]
        candidates = []

        for numerator in items:
            if numerator is denominator or numerator["used"]:
                continue

            nx0, ny0, nx1, ny1 = numerator["bbox"]
            if not (ny0 <= dy0 <= ny1 + 25):
                continue
            # PDF boxes often include trailing whitespace; the denominator's
            # left edge is therefore more reliable than its box centre.
            if not (nx0 - 5 <= dx0 <= nx1 + 5):
                continue

            match = re.search(r"([−–-]?\s*\d+)\s*$", numerator["text"])
            if match:
                candidates.append((dy0 - ny0, numerator, match))

        if not candidates:
            continue

        _, numerator, match = min(candidates, key=lambda candidate: candidate[0])
        numerator_value = (
            match.group(1)
            .replace(" ", "")
            .replace("–", "-")
            .replace("−", "-")
        )
        numerator["text"] = (
            numerator["text"][:match.start()]
            + f"\\frac{{{numerator_value}}}{{{denom_text}}}"
            + numerator["text"][match.end():]
        )
        denominator["used"] = True

    return [item["text"] for item in items if not item["used"]]


def segment_questions_from_pages(pages_dict: dict) -> dict:
    """
    Segments raw page layout blocks into question objects.

    For each numbered block (Q1, Q2, ...) the raw collected text is sent to
    ai_split_question_block(), which strips meta-instruction wrappers and
    explodes sub-parts (a)/(b)/... into individual independent questions.
    Sub-questions get IDs like q2a, q2b; single questions keep q1, q2, etc.
    """
    paper_id = pages_dict.get("paper_id")

    all_lines = []
    for page in pages_dict.get("pages", []):
        pnum = page["page_num"]
        pwidth = page.get("width", 612.0)
        page_text = "\n".join(
            line.get("text", "")
            for block in page.get("blocks", [])
            if block.get("type") == "text"
            for line in block.get("lines", [])
        )
        if not is_english_dominant(page_text):
            continue
        for block in page.get("blocks", []):
            if block.get("type") != "text":
                continue
            for line in block.get("lines", []):
                txt = line.get("text", "").strip()
                bbox = line.get("bbox", [0, 0, 0, 0])
                if txt:
                    all_lines.append({
                        "page_num": pnum,
                        "page_width": pwidth,
                        "text": txt,
                        "bbox": bbox
                    })

    current_section = "HEADER"
    in_instructions = False

    # Each entry: {"question_number": int, "section": str, "page_num": int,
    #              "lines": [str], "bboxes": [[x0,y0,x1,y1]]}
    raw_blocks: list[dict] = []
    current_block: dict | None = None
    current_q_num: int | None = None

    for idx, item in enumerate(all_lines):
        txt = item["text"]
        pnum = item["page_num"]
        pwidth = item["page_width"]
        bbox = item["bbox"]
        x0 = bbox[0]

        if INSTRUCTION_HEADER_REGEX.search(txt):
            in_instructions = True
            continue

        sec_m = SECTION_REGEX.search(txt)
        if sec_m:
            current_section = sec_m.group(1).upper().replace(" ", "").replace("-", " ")
            in_instructions = False
            if current_block:
                raw_blocks.append(current_block)
                current_block = None
                current_q_num = None
            continue

        if current_section == "HEADER" or in_instructions:
            continue

        # Right-margin mark labels (e.g. [1], [2]) — skip, they belong to blocks
        if x0 > (pwidth - 90):
            if current_block is not None:
                current_block["lines"].append(txt)
                current_block["bboxes"].append(bbox)
            continue

        num_val = None

        mA = Q_PATTERN_A.search(txt)
        if mA:
            n_str = [g for g in mA.groups()[1:] if g is not None][0]
            num_val = int(n_str)
        else:
            if x0 < 85:
                mB = Q_PATTERN_B.search(txt)
                if mB:
                    if not re.match(r"^[A-D]\.$", txt):
                        num_val = int(mB.group(1))
                else:
                    mC = Q_PATTERN_C.search(txt)
                    if mC:
                        v = int(mC.group(1))
                        if idx + 1 < len(all_lines):
                            next_txt = all_lines[idx + 1]["text"]
                            if len(next_txt) > 5 and not next_txt.startswith("Page") and not next_txt.startswith("Marks"):
                                num_val = v

        if num_val and 1 <= num_val <= 50:
            if current_q_num != num_val:
                last_seen_q_num = current_q_num
                if last_seen_q_num is None and raw_blocks:
                    last_seen_q_num = raw_blocks[-1]["question_number"]
                if last_seen_q_num is not None and num_val != last_seen_q_num + 1:
                    num_val = None

        if num_val and 1 <= num_val <= 50:
            if current_q_num != num_val:
                if current_block:
                    raw_blocks.append(current_block)
                current_q_num = num_val
                current_block = {
                    "question_number": num_val,
                    "section": current_section,
                    "page_num": pnum,
                    "lines": [txt],
                    "bboxes": [bbox],
                }
            else:
                current_block["lines"].append(txt)
                current_block["bboxes"].append(bbox)
        elif current_block is not None:
            current_block["lines"].append(txt)
            current_block["bboxes"].append(bbox)

    if current_block:
        raw_blocks.append(current_block)

    # --- AI-powered explosion: one LLM call per numbered block ---
    SUBPART_LABELS = list("abcdefghijklmnopqrstuvwxyz")
    questions: list[dict] = []

    for block in raw_blocks:
        q_num = block["question_number"]
        section = block["section"]
        page_num = block["page_num"]
        bboxes = block["bboxes"]

        # Compute union bbox for the whole block
        min_x = min(b[0] for b in bboxes)
        min_y = min(b[1] for b in bboxes)
        max_x = max(b[2] for b in bboxes)
        max_y = max(b[3] for b in bboxes)
        union_bbox = [round(min_x, 2), round(min_y, 2), round(max_x, 2), round(max_y, 2)]

        # Build the raw text, skip bare mark lines like [1] [3] etc.
        math_aware_lines = restore_spatial_fractions(
            block["lines"], block["bboxes"]
        )
        raw_text = "\n".join(
            l for l in normalize_and_clean_lines(math_aware_lines)
            if not MARK_JUNK_RE.match(l.strip())
        ).strip()

        if not raw_text or len(raw_text) < 10:
            continue

        print(f"  [segment] Q{q_num} -> calling AI splitter ({len(raw_text)} chars)...")
        split_texts = ai_split_question_block(raw_text)

        if len(split_texts) == 1:
            # Single question — keep as Q{n}
            q_id = f"q{q_num}"
            q_text = split_texts[0]
            options = extract_options(q_text, section, str(q_num))
            is_valid = len(q_text.strip()) > 15
            questions.append({
                "question_id": q_id,
                "question_number": f"Q{q_num}",
                "section": section,
                "page_num": page_num,
                "bounding_box": union_bbox,
                "raw_text": q_text,
                "options": options,
                "has_subparts": False,
                "subparts": [],
                "is_valid": is_valid,
            })
        else:
            # Multiple sub-questions — label as Q{n}a, Q{n}b, ...
            for sub_idx, q_text in enumerate(split_texts):
                suffix = SUBPART_LABELS[sub_idx] if sub_idx < len(SUBPART_LABELS) else str(sub_idx + 1)
                q_id = f"q{q_num}{suffix}"
                q_num_str = f"Q{q_num}{suffix.upper()}"
                options = extract_options(q_text, section, str(q_num))
                is_valid = len(q_text.strip()) > 10
                questions.append({
                    "question_id": q_id,
                    "question_number": q_num_str,
                    "section": section,
                    "page_num": page_num,
                    "bounding_box": union_bbox,
                    "raw_text": q_text,
                    "options": options,
                    "has_subparts": False,
                    "subparts": [],
                    "is_valid": is_valid,
                })

    return {
        "paper_id": paper_id,
        "class": pages_dict.get("class"),
        "subject": pages_dict.get("subject"),
        "year": pages_dict.get("year"),
        "total_questions": len(questions),
        "questions": questions
    }


def finalize_question(q_data: dict) -> dict:
    """Computes bounding box, cleans text, enforces MCQ-XOR-Subpart, strips phantom stems."""
    cleaned_lines = normalize_and_clean_lines(q_data["lines"])
    full_text = "\n".join(cleaned_lines)

    page_bboxes = [b for p, b in zip(q_data.get("pages", []), q_data["bboxes"]) if p == q_data["page_num"]]
    if not page_bboxes:
        page_bboxes = q_data["bboxes"]

    min_x = min(b[0] for b in page_bboxes)
    min_y = min(b[1] for b in page_bboxes)
    max_x = max(b[2] for b in page_bboxes)
    max_y = max(b[3] for b in page_bboxes)
    union_bbox = [round(min_x, 2), round(min_y, 2), round(max_x, 2), round(max_y, 2)]

    clean_opts = extract_options(full_text, q_data["section"], q_data["question_number"])

    # --- MCQ XOR Subpart enforcement ---
    # If we have 4 valid options -> MCQ, skip subpart parsing entirely
    # If not -> descriptive, discard partial options and parse subparts
    if len(clean_opts) == 4:
        subparts = []
        main_stem = full_text
    else:
        clean_opts = []
        main_stem, subparts = parse_question_blocks_from_lines(cleaned_lines, [])

    # --- Build clean stem ---
    stem_to_save = main_stem if main_stem else full_text
    # Strip section-header bleed from bottom of stem
    stem_to_save = SECTION_HDR_BLEED_RE.sub("", stem_to_save).strip()
    # Strip trailing instruction prompts
    stem_to_save = re.sub(
        r"\n[^\n]*(?:select the most appropriate|select the correct|choose the correct)[^\n]*$",
        "", stem_to_save, flags=re.IGNORECASE
    ).strip()
    stem_to_save = re.sub(r"\n\s*Options?\:?\s*$", "", stem_to_save, flags=re.IGNORECASE).strip()
    # For MCQ: strip the inline option lines from the stem so it's just the question
    if clean_opts:
        stem_to_save = re.sub(
            r'\n?\s*\(?[A-Da-d][\)\.]\s+.{1,100}(?:\s{2,}\(?[A-Da-d][\)\.]\s+.{1,100})*\s*$',
            '', stem_to_save
        ).strip()




    # --- Mark question invalid if stem is just the question number (phantom chunk) ---
    # e.g. raw_text = "22." means the actual text was stripped (Indic-only or missing)
    q_num_only = re.match(r'^(?:Q\.?\s*)?\d{1,2}\.?\s*$', stem_to_save)
    is_valid = not q_num_only and len(stem_to_save.strip()) > 15

    return {
        "question_id": q_data["question_id"],
        "question_number": q_data["question_number"],
        "section": q_data["section"],
        "page_num": q_data["page_num"],
        "bounding_box": union_bbox,
        "raw_text": stem_to_save,
        "options": clean_opts,
        "has_subparts": len(subparts) > 0,
        "subparts": subparts,
        "is_valid": is_valid,
    }


def segment_paper(paper_id: str, root_dir: str = PROJECT_ROOT) -> str:
    """Segments pages.json for paper_id, outputs questions.json, and updates context.json."""
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
    pages_json_path = os.path.join(parsed_dir, "pages.json")

    if not os.path.exists(pages_json_path):
        raise FileNotFoundError(f"pages.json missing at {pages_json_path}. Run Phase 2 parse first.")

    with open(pages_json_path, 'r', encoding='utf-8') as f:
        pages_dict = json.load(f)

    questions_dict = segment_questions_from_pages(pages_dict)
    questions_json_path = os.path.join(parsed_dir, "questions.json")

    with open(questions_json_path, 'w', encoding='utf-8') as f:
        json.dump(questions_dict, f, indent=2)

    p_info["phase_status"]["segment"] = "done"
    p_info["updated_at"] = datetime.now(timezone.utc).isoformat()
    ctx["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(context_path, 'w', encoding='utf-8') as f:
        json.dump(ctx, f, indent=2)

    print(f"Segmented paper {paper_id} ({questions_dict['total_questions']} questions) -> {questions_json_path}")
    return questions_json_path
