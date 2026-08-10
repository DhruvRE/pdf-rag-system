"""
Extraction Quality Benchmark Harness.
Measures structural parsing accuracy, option-splitting correctness, diagram alignment, and stem purity
across all extracted papers in the corpus (separate from RAG vector retrieval metrics).
"""

import os
import sys
import glob
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import PROJECT_ROOT, PARSED_DIR


def evaluate_corpus_extraction_quality(parsed_dir: str = PARSED_DIR) -> dict:
    """
    Scans all parsed structured_draft.json and questions.json files in data/parsed/,
    performing a granular field-by-field structural accuracy audit.
    """
    total_questions = 0
    valid_mcqs = 0
    mcq_4_options_correct = 0

    diagram_referenced_qs = 0
    diagram_attached_correct = 0

    assertion_reason_qs = 0
    assertion_reason_4_opts_correct = 0

    clean_stems_correct = 0
    mutual_exclusivity_correct = 0
    zero_pua_glyphs = 0

    pua_glyph_pattern = r"[\u0b00-\u0bff\u0c00-\u0c7f\uf000-\uf8ff]"

    for qpath in glob.glob(os.path.join(parsed_dir, "*/*/*/*/questions.json")):
        with open(qpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        for q in data.get("questions", []):
            if not q.get("is_valid", True):
                continue

            total_questions += 1
            stem = q.get("raw_text", "")
            opts = q.get("options", [])
            subs = q.get("subparts", [])
            imgs = q.get("images", [])

            # 1. Stem Purity Check (>15 chars & no section header bleed)
            if len(stem.strip()) >= 15 and not ("SECTION –" in stem or "SECTION -" in stem):
                clean_stems_correct += 1

            # 2. Options XOR Subparts Mutual Exclusivity Check
            if (opts and not subs) or (subs and not opts) or (not opts and not subs):
                mutual_exclusivity_correct += 1

            # 3. PUA Font Glyph Check
            import re
            if not re.search(pua_glyph_pattern, stem):
                zero_pua_glyphs += 1

            # 4. MCQ 4-Option Accuracy Check (for questions classified as single_choice_mcq or with options)
            is_mcq = q.get("question_type") == "single_choice_mcq" or len(opts) >= 2
            if is_mcq:
                valid_mcqs += 1
                if len(opts) == 4:
                    mcq_4_options_correct += 1

            # 5. Diagram Alignment Check
            image_kws = ("the figure", "in the diagram", "shown below", "the graph", "circuit diagram", "refer to figure", "in fig")
            if any(kw in stem.lower() for kw in image_kws):
                diagram_referenced_qs += 1
                if len(imgs) > 0:
                    diagram_attached_correct += 1

            # 6. Assertion-Reason Alignment Check
            if "assertion" in stem.lower() and "reason" in stem.lower():
                assertion_reason_qs += 1
                if len(opts) == 4 or (subs and len(subs[0].get("options", [])) == 4):
                    assertion_reason_4_opts_correct += 1

    return {
        "total_questions_audited": total_questions,
        "clean_stem_accuracy": round(clean_stems_correct / max(total_questions, 1) * 100, 2),
        "mutual_exclusivity_accuracy": round(mutual_exclusivity_correct / max(total_questions, 1) * 100, 2),
        "zero_pua_glyph_accuracy": round(zero_pua_glyphs / max(total_questions, 1) * 100, 2),
        "mcq_4_option_accuracy": round(mcq_4_options_correct / max(valid_mcqs, 1) * 100, 2),
        "diagram_attachment_accuracy": round(diagram_attached_correct / max(diagram_referenced_qs, 1) * 100, 2),
        "assertion_reason_accuracy": round(assertion_reason_4_opts_correct / max(assertion_reason_qs, 1) * 100, 2)
    }


class TestExtractionQuality(unittest.TestCase):

    def test_extraction_quality_benchmark(self):
        metrics = evaluate_corpus_extraction_quality()
        
        print("\n=======================================================")
        print("  GRANULAR EXTRACTION QUALITY AUDIT BENCHMARK")
        print("=======================================================")
        print(f"Total Questions Audited:           {metrics['total_questions_audited']}")
        print(f"Stem Purity Accuracy:              {metrics['clean_stem_accuracy']}%")
        print(f"Options XOR Subparts Exclusivity:  {metrics['mutual_exclusivity_accuracy']}%")
        print(f"Zero PUA Glyph Accuracy:           {metrics['zero_pua_glyph_accuracy']}%")
        print(f"MCQ 4-Option Splitting Accuracy:   {metrics['mcq_4_option_accuracy']}%")
        print(f"Diagram Attachment Accuracy:       {metrics['diagram_attachment_accuracy']}%")
        print(f"Assertion-Reason 4-Opt Accuracy:   {metrics['assertion_reason_accuracy']}%")
        print("=======================================================\n")

        self.assertGreaterEqual(metrics["clean_stem_accuracy"], 95.0)
        self.assertGreaterEqual(metrics["mutual_exclusivity_accuracy"], 95.0)
        self.assertGreaterEqual(metrics["zero_pua_glyph_accuracy"], 98.0)


if __name__ == "__main__":
    unittest.main()
