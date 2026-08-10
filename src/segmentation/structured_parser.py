"""
Stage 4 & Stage 5: Two-Pass Structured Parsing, Self-Validation Pass, and Unified CBSE Schema.
Handles:
1. Stage 4: Pass A Extraction into Unified CBSE JSON Schema & Pass B Self-Audit verification.
2. Stage 5: Extraction confidence evaluation, automated review flagging, and VLM diagram verification hooks.
"""

import re
import json
from typing import List, Dict, Optional, Any


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
        # Single implicit section
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

            # Extract marks indicator like [1], (2 Marks), etc.
            mark_match = re.search(r"(?:\[|\()(\d+)\s*(?:Marks?|marks?|M)?(?:\]|\))", q_body)
            q_marks = int(mark_match.group(1)) if mark_match else 1

            # Detect Assertion-Reason
            is_ar = "Assertion" in q_body and "Reason" in q_body
            is_mcq = bool(re.search(r"\(a\).+\(b\).+\(c\).+\(d\)", q_body, re.DOTALL)) and not is_ar
            q_type = "assertion_reason" if is_ar else ("mcq" if is_mcq else "short_answer")

            # Extract image placeholders attached to this question
            attached_imgs = [ph for ph in image_manifest.keys() if ph in q_body]

            # Detect OR internal choice alternative
            or_parts = re.split(r"\n\s*(?:\[OR\]|\bOR\b)\s*\n", q_body, flags=re.IGNORECASE)
            main_body = or_parts[0].strip()
            alt_body = or_parts[1].strip() if len(or_parts) > 1 else None

            # Build subparts
            subpart_obj = {
                "label": None,
                "marks": q_marks,
                "text": main_body,
                "options": [],
                "correct_answer": None,
                "image_placeholders": attached_imgs,
                "table_data": None,
                "has_or_alternative": alt_body is not None,
                "alternative": None
            }

            if is_mcq:
                # Extract choices
                opts = []
                opt_matches = re.findall(r"\(([a-d])\)\s*([^(\n]+)", main_body, re.IGNORECASE)
                for lbl, txt in opt_matches:
                    opts.append({"label": lbl.lower(), "text": txt.strip()})
                subpart_obj["options"] = opts

            if is_ar:
                subpart_obj["options"] = [
                    {"label": "a", "text": "Both Assertion (A) and Reason (R) are true and Reason (R) is correct explanation."},
                    {"label": "b", "text": "Both Assertion (A) and Reason (R) are true but Reason (R) is NOT correct explanation."},
                    {"label": "c", "text": "Assertion (A) is true but Reason (R) is false."},
                    {"label": "d", "text": "Assertion (A) is false but Reason (R) is true."}
                ]

            if alt_body:
                subpart_obj["alternative"] = {
                    "label": "OR",
                    "marks": q_marks,
                    "text": alt_body,
                    "options": [],
                    "image_placeholders": [ph for ph in image_manifest.keys() if ph in alt_body]
                }

            question_obj = {
                "question_number": q_num,
                "marks": q_marks,
                "question_type": q_type,
                "selection_rule": {"choose": 1 if alt_body else None, "of": 2 if alt_body else None},
                "stem_text": main_body[:300],
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
