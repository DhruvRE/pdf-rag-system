"""
Stage 4 & Stage 5: Two-Pass Structured Parsing, Self-Validation Pass, and Unified CBSE Schema.
Handles:
1. Stage 4: Pass A Extraction into Unified CBSE JSON Schema & Pass B Self-Audit verification.
2. Stage 5: Extraction confidence evaluation, automated review flagging, and VLM diagram verification hooks.
"""

import re
import json
from typing import List, Dict, Optional, Any
from src.parsing.ai_normalizer import is_instruction_header_ai, extract_options_and_stem


class UnifiedSchemaEncoder(json.JSONEncoder):
    """Custom JSON encoder for structured exam schema dataclasses/dicts."""
    def default(self, o):
        if hasattr(o, "__dict__"):
            return o.__dict__
        return super().default(o)


def create_empty_exam_schema(
    subject: str = "mathematics",
    class_level: str = "10",
    year: str = "2024-2025",
    source_file: str = ""
) -> dict:
    """Creates a base instance conforming strictly to the Unified CBSE Exam Schema."""
    return {
        "exam_metadata": {
            "subject": subject,
            "class_level": class_level,
            "year": year,
            "total_marks": 80,
            "duration": "3 Hours",
            "source_file": source_file
        },
        "sections": []
    }


def parse_subquestions_robust(q_body: str) -> list:
    """
    Robust sub-question parser:
    Locates subpart markers (a), (b), (c), (d), (e) or i., ii., iii. inside a question body.
    Handles both standard layout ((a) stem -> options) and scattered layout (stem -> [1] -> (a) -> options).
    Strips page breaks & watermark URLs, and pairs each subpart with its exact prompt text, options, and question type.
    """
    cleaned_body = re.sub(r"<!--\s*PAGE\s*\d+\s*(?:START|END)\s*-->", "", q_body)
    cleaned_body = re.sub(r"(?:\n|^)\s*(?:https?://[^\n]+|\d+\s*/\s*\d+|\b\d+\s*/\s*\d+\b|Page\s*\d+[^\n]*)\s*", "\n", cleaned_body, flags=re.IGNORECASE)
    cleaned_body = re.sub(r"\n\s*\d+\s*/\s*\d+\s*\n", "\n", cleaned_body)
    cleaned_body = re.sub(r"(?:\n|^)\s*numbers\.\s*", "\n", cleaned_body)

    sub_matches = list(re.finditer(r"(?:\n|^)\s*(?:\[\d+\]\s*)?\(([a-eA-E])\)\s*", cleaned_body))
    if not sub_matches:
        sub_matches = list(re.finditer(r"(?:\n|^)\s*(?:\[\d+\]\s*)?(?:\(([i|v|x]+)\)|\b([i|v|x]+)\.)\s*", cleaned_body, re.IGNORECASE))

    if not sub_matches:
        return []

    parent_prompt = cleaned_body[:sub_matches[0].start()].strip()
    parent_lines = [l.strip() for l in parent_prompt.splitlines() if l.strip()]
    
    parent_header = parent_lines[0] if parent_lines else ""
    
    trailing_stem_seg0 = ""
    if len(parent_lines) > 1:
        stem_candidates = [l for l in parent_lines[1:] if not re.match(r"^\s*\[\d+\]\s*$", l) and not is_instruction_header_ai(l)]
        trailing_stem_seg0 = "\n".join(stem_candidates).strip()

    sub_questions = []
    pending_stem = trailing_stem_seg0

    for idx, match in enumerate(sub_matches):
        lbl = (match.group(1) or match.group(2) or "").lower()
        sub_label = f"({lbl})"
        start_pos = match.end()
        end_pos = sub_matches[idx + 1].start() if idx + 1 < len(sub_matches) else len(cleaned_body)
        block_text = cleaned_body[start_pos:end_pos].strip()

        opt_matches = list(re.finditer(r"(?:^|\n)\s*([a-dA-D1-4])[\)\.\:]\s*([^\n]+)", block_text))
        
        sub_opts = []
        stem_before = ""
        stem_after = ""

        if opt_matches:
            opts_start = opt_matches[0].start()
            opts_end = opt_matches[-1].end()
            stem_before = block_text[:opts_start].strip()
            sub_opts = [{"label": om.group(1).upper(), "text": om.group(2).strip()} for om in opt_matches]
            stem_after = block_text[opts_end:].strip()
        else:
            stem_before = block_text
            stem_after = ""

        stem_before = re.sub(r"^\s*\[\d+\]\s*", "", stem_before).strip()
        stem_before = re.sub(r"\s*\[\d+\]\s*$", "", stem_before).strip()
        stem_after = re.sub(r"^\s*\[\d+\]\s*", "", stem_after).strip()
        stem_after = re.sub(r"\s*\[\d+\]\s*$", "", stem_after).strip()

        # Determine actual stem text for this subpart:
        if pending_stem:
            current_stem = pending_stem
            pending_stem = stem_after if stem_after else stem_before
        else:
            current_stem = stem_before
            pending_stem = stem_after

        current_stem = re.sub(r"^\s*\[\d+\]\s*", "", current_stem).strip()

        is_ar = "Assertion" in current_stem and "Reason" in current_stem
        is_fib = "________" in current_stem or "blank" in parent_header.lower()
        is_tf = "true or false" in parent_header.lower() or "true/false" in parent_header.lower() or "state whether" in current_stem.lower()

        if is_ar:
            q_type = "assertion_reason"
        elif is_fib:
            q_type = "fill_in_the_blank"
        elif is_tf:
            q_type = "true_false"
        elif sub_opts:
            q_type = "single_choice_mcq"
        else:
            q_type = "short_answer"

        full_stem = f"{parent_header}\n{current_stem}".strip() if parent_header and parent_header != current_stem else current_stem

        sub_questions.append({
            "label": sub_label,
            "text": full_stem,
            "question_type": q_type,
            "options": sub_opts
        })

    return sub_questions


def parse_markdown_pass_a(
    markdown_text: str,
    image_manifest: dict,
    subject: str = "mathematics",
    class_level: str = "10",
    year: str = "2024-2025",
    source_file: str = ""
) -> dict:
    """
    Pass A — Extraction: Converts raw/unified markdown text into the Unified CBSE JSON Schema.
    """
    exam = create_empty_exam_schema(subject, class_level, year, source_file)

    # Split markdown by section headers
    section_blocks = re.split(r"(?:\n|^)#\s*(SECTION\s*[A-E]|Section\s*[A-E]|PART\s*[A-E])[^\n]*", markdown_text, flags=re.IGNORECASE)

    if len(section_blocks) <= 1:
        raw_sections = [("SECTION A", markdown_text)]
    else:
        raw_sections = []
        for i in range(1, len(section_blocks), 2):
            sec_name = section_blocks[i].strip().upper()
            sec_content = section_blocks[i + 1] if i + 1 < len(section_blocks) else ""
            raw_sections.append((sec_name, sec_content))

    for sec_id, sec_text in raw_sections:
        section_obj = {
            "section_id": sec_id,
            "instruction": "All questions are compulsory unless internal choice is provided.",
            "mark_scheme": "Refer to individual question mark allocations.",
            "questions": []
        }

        # Split questions by ## Q boundaries
        q_blocks = re.split(r"(?:\n|^)##\s*(Q\.?\s*\d+|\d+\.)", sec_text)

        for j in range(1, len(q_blocks), 2):
            q_num_raw = q_blocks[j].strip()
            clean_digits = re.sub(r"\D", "", q_num_raw)
            q_num = f"Q{clean_digits}"
            q_body = q_blocks[j + 1] if j + 1 < len(q_blocks) else ""

            sub_qs = parse_subquestions_robust(q_body)

            mark_match = re.search(r"(?:\[|\()(\d+)\s*(?:Marks?|marks?|M)?(?:\]|\))", q_body)
            q_marks = int(mark_match.group(1)) if mark_match else 1

            or_parts = re.split(r"\n\s*(?:\[OR\]|\bOR\b)\s*\n", q_body, flags=re.IGNORECASE)
            main_body = or_parts[0].strip()
            alt_body = or_parts[1].strip() if len(or_parts) > 1 else None

            is_ar = "Assertion" in main_body and "Reason" in main_body
            attached_imgs = [ph for ph in image_manifest.keys() if ph in q_body]

            clean_stem, extracted_options = extract_options_and_stem(main_body)
            if not clean_stem:
                clean_stem = main_body

            subpart_obj = {
                "label": None,
                "marks": q_marks,
                "text": clean_stem,
                "options": extracted_options,
                "subparts": sub_qs,
                "correct_answer": None,
                "image_placeholders": attached_imgs,
                "table_data": None,
                "has_or_alternative": alt_body is not None,
                "alternative": None
            }

            if alt_body:
                alt_stem, alt_options = extract_options_and_stem(alt_body)
                subpart_obj["alternative"] = {
                    "label": "OR",
                    "marks": q_marks,
                    "text": alt_stem if alt_stem else alt_body,
                    "options": alt_options,
                    "image_placeholders": [ph for ph in image_manifest.keys() if ph in alt_body]
                }

            q_type = "assertion_reason" if is_ar else ("single_choice_mcq" if len(extracted_options) >= 2 else ("case_study_passage" if sub_qs else "short_answer"))

            question_obj = {
                "question_number": q_num,
                "marks": q_marks,
                "question_type": q_type,
                "selection_rule": {"choose": 1 if alt_body else None, "of": 2 if alt_body else None},
                "stem_text": clean_stem[:300],
                "passage_text": None,
                "subparts": [subpart_obj],
                "topic": None,
                "subtopic": None,
                "raw_source_span": f"## {q_num_raw}\n{q_body.strip()}",
                "extraction_confidence": "high",
                "flagged_for_review": False,
                "flag_reason": None,
                "corrected": False,
                "correction_note": None,
                "needs_manual_review": False,
                "review_reason": None
            }

            section_obj["questions"].append(question_obj)

        if section_obj["questions"]:
            exam["sections"].append(section_obj)

    return exam


QUESTION_TYPES = [
    "single_choice_mcq",
    "assertion_reason",
    "true_false",
    "fill_in_the_blank",
    "match_the_following",
    "multiple_choice_multi",
    "short_answer",
    "long_answer",
    "case_study_passage",
    "diagram_based",
    "numeric_answer"
]


def classify_question_type(
    text: str,
    options: list = None,
    image_placeholders: list = None,
    table_data: Any = None,
    has_or_alternative: bool = False
) -> dict:
    """
    Pass B-1 — Type Classifier: Classifies question/subpart into a closed taxonomy of types and boolean flags.
    """
    options = options or []
    image_placeholders = image_placeholders or []
    text_lower = text.lower()

    # Rule 1: Assertion-Reason check
    if "assertion" in text_lower and "reason" in text_lower:
        primary_type = "assertion_reason"
    # Rule 2: Case study passage check
    elif any(kw in text_lower for kw in ("read the following", "case study", "passage", "based on the above")):
        primary_type = "case_study_passage"
    # Rule 3: Match the following check
    elif "match" in text_lower and ("column" in text_lower or "list" in text_lower):
        primary_type = "match_the_following"
    # Rule 4: Fill in the blank check
    elif "_______" in text or "fill in the blank" in text_lower:
        primary_type = "fill_in_the_blank"
    # Rule 5: True/False check
    elif "true or false" in text_lower or "state whether true" in text_lower:
        primary_type = "true_false"
    # Rule 6: MCQ check
    elif len(options) >= 2:
        primary_type = "single_choice_mcq"
    # Rule 7: Numeric answer check
    elif any(kw in text_lower for kw in ("calculate the value", "find the magnitude", "numerical value")):
        primary_type = "numeric_answer"
    # Rule 8: Long answer / proof check
    elif any(kw in text_lower for kw in ("prove that", "derive", "explain in detail", "describe the mechanism")):
        primary_type = "long_answer"
    else:
        primary_type = "short_answer"

    # Secondary Boolean Flags
    image_keywords = ("the figure", "in the diagram", "shown below", "the graph", "circuit diagram", "see figure", "refer to figure", "in fig")
    text_references_image = any(kw in text_lower for kw in image_keywords)
    has_image_attached = len(image_placeholders) > 0

    requires_image = text_references_image or has_image_attached or primary_type == "diagram_based"
    missing_image_reference = text_references_image and not has_image_attached
    requires_table_data = table_data is not None or primary_type == "match_the_following"

    confidence = "high"
    if missing_image_reference or (primary_type == "assertion_reason" and len(options) != 4):
        confidence = "low"
    elif primary_type == "single_choice_mcq" and len(options) < 4:
        confidence = "medium"

    return {
        "primary_type": primary_type,
        "requires_image": requires_image,
        "requires_table_data": requires_table_data,
        "has_or_alternative": has_or_alternative,
        "missing_image_reference": missing_image_reference,
        "classification_confidence": confidence
    }


def validate_by_type(question: dict, subpart: dict, classification: dict) -> List[dict]:
    """
    Pass B-2 — Type-Aware Validator: Applies deterministic rule checks targeted to the specific primary_type.
    """
    issues = []
    t = classification["primary_type"]
    qn = question.get("question_number", "Unknown")
    opts = subpart.get("options", [])
    placeholders = subpart.get("image_placeholders", [])
    text = subpart.get("text", "")

    # 1. Assertion-Reason Alignment Rules
    if t == "assertion_reason":
        if len(opts) != 4:
            issues.append({
                "question_number": qn,
                "issue": f"assertion_reason question has {len(opts)} options, expected exactly 4",
                "severity": "critical"
            })
        if "assertion" not in text.lower():
            issues.append({
                "question_number": qn,
                "issue": "classified as assertion_reason but no 'Assertion' text found in stem",
                "severity": "critical"
            })

    # 2. Image / Figure Alignment Rules
    if classification["requires_image"] and not placeholders:
        issues.append({
            "question_number": qn,
            "issue": "question references a figure/diagram but has no image_placeholder attached",
            "severity": "critical"
        })

    if classification["missing_image_reference"]:
        issues.append({
            "question_number": qn,
            "issue": "text references a figure/diagram but no image was detected nearby in source PDF",
            "severity": "critical"
        })

    # 3. MCQ Alignment Rules
    if t == "single_choice_mcq":
        if len(opts) < 2:
            issues.append({
                "question_number": qn,
                "issue": f"single_choice_mcq has only {len(opts)} options (expected at least 2)",
                "severity": "critical"
            })

    # 4. True/False Rules
    if t == "true_false":
        if opts and len(opts) != 2:
            issues.append({
                "question_number": qn,
                "issue": f"true_false has {len(opts)} options array (expected 2)",
                "severity": "minor"
            })

    # 5. Match the Following Rules
    if t == "match_the_following" and not subpart.get("table_data"):
        issues.append({
            "question_number": qn,
            "issue": "match_the_following question has no structured column table_data",
            "severity": "minor"
        })

    return issues


def needs_vlm_recheck(issues: List[dict]) -> bool:
    """Returns True if any critical issue requires escalation to VLM visual page re-check."""
    return any(i.get("severity") == "critical" and "image" in i.get("issue", "").lower() for i in issues)


def reconcile_question_against_source(question_obj: dict) -> dict:
    """
    Pass B-0 — General-Purpose Source Reconciliation Pass.
    Directly reconciles extracted JSON structure against raw_source_span.
    Catches OCR splits, mangled option markers like (c ), merged text, and unattached image placeholders.
    """
    raw_span = question_obj.get("raw_source_span", "")
    subparts = question_obj.get("subparts", [])

    if not raw_span or not subparts:
        question_obj["corrected"] = False
        question_obj["correction_note"] = None
        question_obj["needs_manual_review"] = False
        question_obj["review_reason"] = None
        return question_obj

    sub0 = subparts[0]
    opts = sub0.get("options", [])
    text = sub0.get("text", "")

    corrected = False
    correction_note = []
    needs_manual_review = False
    review_reason = None

    # Check 1: Option label distortion check e.g. (c ), c), ( c ) with extra spaces/OCR glitches
    raw_opt_matches = re.findall(r"(?:\(|\b)([a-d])(?:\s*\)|\s*\.)\s*([^(\n]+)", raw_span, re.IGNORECASE)
    if len(raw_opt_matches) >= 2 and len(opts) < len(raw_opt_matches):
        reconciled_opts = []
        for lbl, opt_txt in raw_opt_matches:
            reconciled_opts.append({"label": lbl.lower().strip(), "text": opt_txt.strip()})
        sub0["options"] = reconciled_opts
        corrected = True
        correction_note.append(f"Reconciled {len(reconciled_opts)} options from raw source span (fixed label split/spacing)")

    # Check 2: Unattached image placeholder check vs raw span
    span_imgs = re.findall(r"\[IMAGE_PLACEHOLDER_\d+\]", raw_span)
    assigned_imgs = sub0.get("image_placeholders", [])
    missing_imgs = set(span_imgs) - set(assigned_imgs)
    if missing_imgs:
        sub0["image_placeholders"] = list(set(assigned_imgs).union(missing_imgs))
        corrected = True
        correction_note.append(f"Reconciled missing image placeholders {list(missing_imgs)} from raw source span")

    # Check 3: Check if raw span is severely corrupted/mangled
    if len(text.strip()) < 15 and len(raw_span.strip()) > 30:
        needs_manual_review = True
        review_reason = f"Raw source span exists ({len(raw_span)} chars) but extracted text stem is empty/truncated"

    question_obj["corrected"] = corrected
    question_obj["correction_note"] = "; ".join(correction_note) if correction_note else None
    question_obj["needs_manual_review"] = needs_manual_review
    question_obj["review_reason"] = review_reason

    return question_obj


def audit_extraction_pass_b(extracted_json: dict, source_markdown: str, image_manifest: dict) -> List[dict]:
    """
    Pass B — Self-Audit: Combines Pass B-0 Source Reconciliation, Pass B-1 classification, Pass B-2 type-aware validation, and structural checks.
    """
    issues = []

    # 1. Audit missing question numbers
    source_q_nums = set(re.findall(r"##\s*(?:Q\.?\s*)?(\d+)", source_markdown))
    extracted_q_nums = set()
    for sec in extracted_json.get("sections", []):
        for q in sec.get("questions", []):
            extracted_q_nums.add(re.sub(r"\D", "", q.get("question_number", "")))

    missing_qs = source_q_nums - extracted_q_nums
    for mq in missing_qs:
        issues.append({
            "question_number": f"Q{mq}",
            "issue": f"Question Q{mq} present in source markdown but missing from JSON structure",
            "severity": "critical"
        })

    # 2. Audit unassigned image placeholders
    manifest_placeholders = set(image_manifest.keys())
    assigned_placeholders = set()
    for sec in extracted_json.get("sections", []):
        for q in sec.get("questions", []):
            for sub in q.get("subparts", []):
                assigned_placeholders.update(sub.get("image_placeholders", []))
                if sub.get("alternative"):
                    assigned_placeholders.update(sub["alternative"].get("image_placeholders", []))

    missing_imgs = manifest_placeholders - assigned_placeholders
    for mi in missing_imgs:
        issues.append({
            "question_number": "General/Unassigned",
            "issue": f"Image placeholder {mi} extracted from PDF but not attached to any question subpart",
            "severity": "minor"
        })

    # 3. Pass B-0 Source Reconciliation & Pass B-1/B-2 Type Classifier/Validator
    for sec in extracted_json.get("sections", []):
        for q in sec.get("questions", []):
            qn = q.get("question_number", "Unknown")
            stem = q.get("stem_text", "")

            # Run Pass B-0 General Source Reconciliation Pass
            reconcile_question_against_source(q)
            if q.get("corrected"):
                issues.append({
                    "question_number": qn,
                    "issue": f"Pass B-0 Source Reconciliation: {q['correction_note']}",
                    "severity": "minor"
                })
            if q.get("needs_manual_review"):
                issues.append({
                    "question_number": qn,
                    "issue": f"Pass B-0 Manual Review Needed: {q['review_reason']}",
                    "severity": "critical"
                })
            
            if len(stem.strip()) < 15:
                issues.append({
                    "question_number": qn,
                    "issue": f"Question {qn} has suspiciously short stem text ('{stem}')",
                    "severity": "critical"
                })

            for sub in q.get("subparts", []):
                classification = classify_question_type(
                    text=sub.get("text", stem),
                    options=sub.get("options", []),
                    image_placeholders=sub.get("image_placeholders", []),
                    table_data=sub.get("table_data"),
                    has_or_alternative=sub.get("has_or_alternative", False)
                )

                # Store classification metadata in subpart & question
                sub["classification"] = classification
                q["question_type"] = classification["primary_type"]
                q["requires_image"] = classification["requires_image"]

                # Run Pass B-2 Type-Aware Validation
                type_issues = validate_by_type(q, sub, classification)
                issues.extend(type_issues)

    return issues


def evaluate_confidence_and_flags(extracted_json: dict, audit_issues: List[dict]) -> dict:
    """
    Stage 5: Applies Pass B audit findings to update extraction_confidence and flagged_for_review.
    """
    issues_by_q = {}
    for issue in audit_issues:
        qn = issue["question_number"]
        issues_by_q.setdefault(qn, []).append(issue)

    for sec in extracted_json.get("sections", []):
        for q in sec.get("questions", []):
            qn = q.get("question_number", "")
            q_issues = issues_by_q.get(qn, [])

            if any(i["severity"] == "critical" for i in q_issues):
                q["extraction_confidence"] = "low"
                q["flagged_for_review"] = True
                q["flag_reason"] = "; ".join(i["issue"] for i in q_issues if i["severity"] == "critical")
            elif q_issues:
                q["extraction_confidence"] = "medium"
                q["flagged_for_review"] = True
                q["flag_reason"] = "; ".join(i["issue"] for i in q_issues)
            else:
                q["extraction_confidence"] = "high"
                q["flagged_for_review"] = False
                q["flag_reason"] = None

    return extracted_json


def extract_json_from_ai_text(text: str) -> dict:
    if not text:
        return {}
    # Strip <think>...</think> blocks from reasoning models
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    try:
        return json.loads(text)
    except Exception:
        return {}


def ai_arrange_and_validate_questions(extracted_json: dict, max_questions: int = 10) -> dict:
    """
    Stage 5B: AI Pipeline Chunk Validator & Auto-Arranger.
    Uses local Ollama (qwen3-vl:30b) to automatically arrange subparts, stem text, MCQ options,
    and validate/correct math/LaTeX equations for questions requiring structural alignment.
    """
    import urllib.request

    processed = 0
    for sec in extracted_json.get("sections", []):
        for q in sec.get("questions", []):
            if q.get("flagged_for_review") or q.get("extraction_confidence") in ("medium", "low"):
                if processed >= max_questions:
                    break
                qn = q.get("question_number", "Q?")
                stem = q.get("stem_text", "")
                raw_options = [opt.get("text", "") if isinstance(opt, dict) else str(opt) for opt in q.get("options", [])]
                
                prompt = (
                    f"You are an expert CBSE exam proofreader and question formatter.\n"
                    f"Format Question {qn}:\n"
                    f"Raw Question Text: {stem}\n"
                    f"Raw Options: {raw_options}\n\n"
                    f"Return ONLY a valid JSON object with keys:\n"
                    f"- \"clean_stem\": Cleaned stem with math in MathJax $...$.\n"
                    f"- \"options\": List of 4 objects with \"label\" (A, B, C, D) and \"text\".\n"
                    f"- \"subparts\": List of sub-question text strings if present, else empty list.\n"
                )

                req_payload = {
                    "model": "qwen3.5:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_ctx": 4096}
                }

                try:
                    req_data = json.dumps(req_payload).encode("utf-8")
                    req = urllib.request.Request(
                        "http://localhost:11434/api/generate",
                        data=req_data,
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=300) as response:
                        res_body = response.read().decode("utf-8")
                        res_json = json.loads(res_body)
                        ai_out = extract_json_from_ai_text(res_json.get("response", ""))

                        if ai_out.get("clean_stem"):
                            q["stem_text"] = ai_out["clean_stem"]
                        if ai_out.get("options") and isinstance(ai_out["options"], list) and len(ai_out["options"]) >= 2:
                            q["options"] = ai_out["options"]
                        if ai_out.get("subparts") and isinstance(ai_out["subparts"], list):
                            q["subparts"] = ai_out["subparts"]

                        q["ai_validated"] = True
                        q["corrected"] = True
                        q["flagged_for_review"] = False
                        q["extraction_confidence"] = "high"
                        q["flag_reason"] = "Auto-arranged & validated by AI Pipeline Engine"
                        processed += 1
                except Exception as e:
                    print(f"AI Auto-Validation bypassed for offline run ({qn}): {e}")
                    break

    return extracted_json
