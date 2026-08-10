"""
Unit & Integration Test Suite for the 8-Stage Architecture Pipeline.
Verifies Stage 0 (detector), Stage 1 (markdown), Stage 2/3 (mapper), Stage 4/5 (structured_parser), and Stage 7 (chunker).
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import unittest

from src.config import PROJECT_ROOT
from src.parsing.detector import detect_pdf_type, extract_native_structure, generate_unified_markdown
from src.image_linking.mapper import crop_and_map_images
from src.segmentation.structured_parser import (
    parse_markdown_pass_a,
    audit_extraction_pass_b,
    evaluate_confidence_and_flags
)
from src.chunking.chunker import create_question_chunks


class Test8StageArchitecture(unittest.TestCase):

    def setUp(self):
        self.sample_pdf = os.path.join(PROJECT_ROOT, "tests", "fixtures", "class10_mathematics_2024_2025_sqp.pdf")
        self.tmp_output_dir = os.path.join(PROJECT_ROOT, "data", "parsed", "test_sample")
        os.makedirs(self.tmp_output_dir, exist_ok=True)

    def test_stage_0_pdf_type_detection(self):
        pdf_type = detect_pdf_type(self.sample_pdf)
        self.assertIn(pdf_type, ["native", "scanned"])
        print(f"\n[Stage 0 PASS] Detected PDF type for sample: '{pdf_type}'")

    def test_stage_1_unified_markdown_extraction(self):
        blocks = extract_native_structure(self.sample_pdf)
        self.assertGreater(len(blocks), 0)
        self.assertIn("text", blocks[0])
        self.assertIn("bbox", blocks[0])

        md_dict = generate_unified_markdown(self.sample_pdf)
        self.assertIn("markdown", md_dict)
        self.assertGreater(len(md_dict["markdown"]), 100)
        print(f"\n[Stage 1 PASS] Extracted {len(blocks)} layout blocks & unified markdown.")

    def test_stage_2_and_3_image_mapping(self):
        manifest = crop_and_map_images(self.sample_pdf, self.tmp_output_dir)
        self.assertIsInstance(manifest, dict)
        if manifest:
            first_key = list(manifest.keys())[0]
            self.assertTrue(first_key.startswith("[IMAGE_PLACEHOLDER_"))
            self.assertIn("bbox", manifest[first_key])
            self.assertIn("caption_nearby", manifest[first_key])
        print(f"\n[Stage 2 & 3 PASS] Extracted & mapped {len(manifest)} image placeholders with bboxes.")

    def test_stage_4_and_5_two_pass_parsing(self):
        md_dict = generate_unified_markdown(self.sample_pdf)
        manifest = crop_and_map_images(self.sample_pdf, self.tmp_output_dir)

        pass_a_json = parse_markdown_pass_a(
            md_dict["markdown"],
            manifest,
            subject="mathematics",
            class_level="10",
            year="2024-2025",
            source_file="class10_mathematics_2024_2025_sqp.pdf"
        )
        self.assertIn("exam_metadata", pass_a_json)
        self.assertIn("sections", pass_a_json)

        issues = audit_extraction_pass_b(pass_a_json, md_dict["markdown"], manifest)
        self.assertIsInstance(issues, list)

        validated_json = evaluate_confidence_and_flags(pass_a_json, issues)
        self.assertIn("sections", validated_json)
        print(f"\n[Stage 4 & 5 PASS] Generated unified CBSE schema & audited {len(issues)} self-validation issues.")

    def test_stage_7_subpart_chunking(self):
        dummy_questions = {
            "paper_id": "test_paper_123",
            "class": "10",
            "subject": "mathematics",
            "year": "2024-2025",
            "questions": [
                {
                    "question_id": "q1",
                    "question_number": "Q1",
                    "section": "SECTION A",
                    "raw_text": "Solve the quadratic equation x^2 - 5x + 6 = 0.",
                    "options": ["(a) 2, 3", "(b) -2, -3", "(c) 1, 6", "(d) -1, -6"],
                    "is_valid": True
                }
            ]
        }
        chunks = create_question_chunks(dummy_questions)
        self.assertEqual(chunks["total_chunks"], 1)
        self.assertEqual(chunks["chunks"][0]["class"], "10")
        self.assertEqual(chunks["chunks"][0]["subject"], "mathematics")
        print(f"\n[Stage 7 PASS] Created metadata-enriched chunks.")


if __name__ == "__main__":
    unittest.main()
