"""
Test suite for School-Specific Vector Database & Pattern Lab Integration.
Verifies that:
1. School names are cleanly slugified into dedicated SQLite DB files under data/vector_store/schools/<slug>.db.
2. Questions from multiple papers for the same school are aggregated into that school's DB.
3. Different schools maintain isolated databases.
4. /api/schools reports accurate telemetry and file paths.
5. /api/patterns/analyze extracts pattern blueprints specifically from that school's DB.
6. /api/papers/generate synthesizes questions conforming to the school's blueprint.
"""

import os
import json
import pytest

from src.config import PROJECT_ROOT, VECTOR_STORE_DIR
from src.embedding.embedder import (
    slugify_school,
    get_school_db_path,
    get_vector_store,
    list_all_school_stores,
    LocalVectorStore
)
from src.api.app import (
    get_registered_schools,
    analyze_question_pattern,
    generate_pattern_paper,
    get_generated_pattern_paper,
    PatternAnalyzeRequest,
    PatternGenerateRequest
)


def test_slugify_school_names():
    assert slugify_school("Navodaya") == "navodaya"
    assert slugify_school("Navodaya Vidyalaya") == "navodaya_vidyalaya"
    assert slugify_school("Delhi Public School - R.K. Puram") == "delhi_public_school_rk_puram"
    assert slugify_school("KV #1") == "kv_1"
    assert slugify_school("") == "general"
    assert slugify_school(None) == "general"


def test_school_database_isolation_and_aggregation(tmp_path):
    navodaya_db = os.path.join(tmp_path, "navodaya.db")
    dps_db = os.path.join(tmp_path, "dps.db")

    store_navodaya = LocalVectorStore(db_path=navodaya_db)
    store_navodaya.set_school_meta("name", "Navodaya Vidyalaya")
    store_navodaya.set_school_meta("slug", "navodaya")

    store_dps = LocalVectorStore(db_path=dps_db)
    store_dps.set_school_meta("name", "Delhi Public School")
    store_dps.set_school_meta("slug", "dps")

    # Paper 1 for Navodaya (Maths - 2 questions)
    store_navodaya.upsert(
        ids=["nav_p1_q1", "nav_p1_q2"],
        documents=[
            "Find the zeroes of the quadratic polynomial x^2 + 7x + 10.",
            "If alpha and beta are zeroes of ax^2 + bx + c, evaluate 1/alpha + 1/beta."
        ],
        metadatas=[
            {"school": "Navodaya Vidyalaya", "class": "10", "subject": "mathematics", "question_type": "short_answer", "difficulty": "easy", "section": "Section A"},
            {"school": "Navodaya Vidyalaya", "class": "10", "subject": "mathematics", "question_type": "short_answer", "difficulty": "medium", "section": "Section B"}
        ]
    )

    # Paper 1 for DPS (Science - 1 question)
    store_dps.upsert(
        ids=["dps_p1_q1"],
        documents=["What is the focal length of a concave mirror having radius of curvature 30 cm?"],
        metadatas=[
            {"school": "Delhi Public School", "class": "10", "subject": "physics", "question_type": "multiple_choice", "difficulty": "easy", "section": "Section A"}
        ]
    )

    assert store_navodaya.count() == 2
    assert store_dps.count() == 1

    # Paper 2 for Navodaya (Science - 2 questions, should accumulate into the SAME DB)
    store_navodaya.upsert(
        ids=["nav_p2_q1", "nav_p2_q2"],
        documents=[
            "Why do stars twinkle while planets do not?",
            "State Ohm's law and write its mathematical formulation."
        ],
        metadatas=[
            {"school": "Navodaya Vidyalaya", "class": "10", "subject": "physics", "question_type": "short_answer", "difficulty": "medium", "section": "Section A"},
            {"school": "Navodaya Vidyalaya", "class": "10", "subject": "physics", "question_type": "long_answer", "difficulty": "hard", "section": "Section C"}
        ]
    )

    # Navodaya DB now has 4 questions
    assert store_navodaya.count() == 4
    # DPS DB remains untouched at 1
    assert store_dps.count() == 1


def test_api_schools_endpoint():
    # Insert test data into Navodaya school store
    nav_store = get_vector_store(school="navodaya")
    nav_store.upsert(
        ids=["test_nav_q1", "test_nav_q2"],
        documents=[
            "Solve for x: 2x + 3 = 11.",
            "Define photosynthesis and state its chemical reaction."
        ],
        metadatas=[
            {"school": "Navodaya Vidyalaya", "class": "10", "subject": "mathematics", "question_type": "short_answer", "difficulty": "easy", "section": "A"},
            {"school": "Navodaya Vidyalaya", "class": "10", "subject": "biology", "question_type": "short_answer", "difficulty": "medium", "section": "B"}
        ]
    )

    data = get_registered_schools()
    assert data["status"] == "success"
    schools = data["schools"]

    # Verify navodaya is listed with questions
    nav_entry = next((s for s in schools if s["id"] == "navodaya"), None)
    assert nav_entry is not None
    assert nav_entry["question_count"] >= 2
    assert nav_entry["has_db"] is True
    assert nav_entry["db_file"] == "navodaya.db"


def test_api_pattern_analyze_and_generate_flow():
    # Seed Navodaya questions
    nav_store = get_vector_store(school="navodaya")
    nav_store.upsert(
        ids=["seed_nav_q1", "seed_nav_q2", "seed_nav_q3"],
        documents=[
            "Calculate the arithmetic mean of the first 10 prime numbers.",
            "The ratio of incomes of two persons is 9:7 and their expenditures are 4:3. Find their incomes.",
            "Prove that sqrt(5) is an irrational number."
        ],
        metadatas=[
            {"school": "Navodaya Vidyalaya", "class": "10", "subject": "mathematics", "question_type": "multiple_choice", "difficulty": "easy", "section": "Section A"},
            {"school": "Navodaya Vidyalaya", "class": "10", "subject": "mathematics", "question_type": "short_answer", "difficulty": "medium", "section": "Section B"},
            {"school": "Navodaya Vidyalaya", "class": "10", "subject": "mathematics", "question_type": "long_answer", "difficulty": "hard", "section": "Section C"}
        ]
    )

    # 1. Analyze Navodaya pattern
    analyze_req = PatternAnalyzeRequest(
        pattern_name="Navodaya Math Pattern",
        school="navodaya",
        class_level="10",
        subject="mathematics"
    )
    analyze_data = analyze_question_pattern(analyze_req)
    assert analyze_data["status"] == "success"
    assert analyze_data["school"] == "navodaya"
    pattern_id = analyze_data["pattern_id"]
    blueprint = analyze_data["blueprint"]

    assert blueprint["sample_count"] >= 3
    assert "multiple_choice" in blueprint["question_type_distribution"]

    # 2. Generate original paper adhering to Navodaya pattern
    gen_req = PatternGenerateRequest(
        pattern_id=pattern_id,
        school="navodaya",
        class_level="10",
        subject="mathematics",
        topic="Polynomials",
        difficulty="medium",
        question_count=3
    )
    gen_data = generate_pattern_paper(gen_req)
    assert gen_data["status"] == "success"
    assert gen_data["school"] == "navodaya"
    assert len(gen_data["paper"]["questions"]) == 3

    # Check that each generated question has solutions and question type
    for q in gen_data["paper"]["questions"]:
        assert "question_text" in q
        assert "solution" in q
        assert len(q["solution"]) > 10

    # 3. Retrieve generated paper from DB
    paper_id = gen_data["paper_id"]
    retrieved = get_generated_pattern_paper(paper_id=paper_id, school="navodaya")
    assert retrieved["status"] == "success"
    assert retrieved["paper"]["paper_id"] == paper_id
