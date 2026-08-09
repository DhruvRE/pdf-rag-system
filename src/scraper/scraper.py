"""
Phase 1 Scraper & Storage Engine.
Orchestrates downloading/generating PDFs into data/raw_pdfs/<class>/<subject>/<year>/,
runs sanity validation checks on each file, and initializes .agent/context.json.
"""

import os
import json
import shutil
import hashlib
from datetime import datetime, timezone
from src.scraper.generator import generate_question_paper_pdf
from src.scraper.sanity import validate_pdf


# Target fixture papers list (12 papers across multiple classes, subjects, years)
FIXTURE_PAPERS = [
    {
        "class": "10",
        "subject": "physics",
        "year": "2023-2024",
        "filename": "class10_physics_2023_2024_paper1.pdf",
        "diagram_type": "circuit"
    },
    {
        "class": "10",
        "subject": "physics",
        "year": "2022-2023",
        "filename": "class10_physics_2022_2023_paper1.pdf",
        "diagram_type": "optics"
    },
    {
        "class": "10",
        "subject": "chemistry",
        "year": "2023-2024",
        "filename": "class10_chemistry_2023_2024_paper1.pdf",
        "diagram_type": None
    },
    {
        "class": "10",
        "subject": "mathematics",
        "year": "2023-2024",
        "filename": "class10_mathematics_2023_2024_paper1.pdf",
        "diagram_type": "geometry"
    },
    {
        "class": "12",
        "subject": "physics",
        "year": "2023-2024",
        "filename": "class12_physics_2023_2024_paper1.pdf",
        "diagram_type": "circuit"
    },
    {
        "class": "12",
        "subject": "physics",
        "year": "2024-2025",
        "filename": "class12_physics_2024_2025_paper1.pdf",
        "diagram_type": None
    },
    {
        "class": "12",
        "subject": "chemistry",
        "year": "2023-2024",
        "filename": "class12_chemistry_2023_2024_paper1.pdf",
        "diagram_type": None
    },
    {
        "class": "12",
        "subject": "mathematics",
        "year": "2023-2024",
        "filename": "class12_mathematics_2023_2024_paper1.pdf",
        "diagram_type": None
    },
    {
        "class": "8",
        "subject": "science",
        "year": "2022-2023",
        "filename": "class8_science_2022_2023_paper1.pdf",
        "diagram_type": "cell"
    },
    {
        "class": "8",
        "subject": "science",
        "year": "2023-2024",
        "filename": "class8_science_2023_2024_paper1.pdf",
        "diagram_type": None
    },
    {
        "class": "8",
        "subject": "mathematics",
        "year": "2023-2024",
        "filename": "class8_mathematics_2023_2024_paper1.pdf",
        "diagram_type": None
    },
    {
        "class": "10",
        "subject": "science",
        "year": "2024-2025",
        "filename": "class10_science_2024_2025_paper1.pdf",
        "diagram_type": None
    }
]


def generate_paper_id(cls: str, subject: str, year: str, filename: str) -> str:
    """Generates a deterministic 12-character paper_id hash key."""
    key = f"{cls}_{subject}_{year}_{filename}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[:12]


from src.config import PROJECT_ROOT
from src.scraper.downloader import download_real_pdfs


def run_phase1_scraper(root_dir: str = PROJECT_ROOT) -> dict:
    """
    Executes Phase 1 using real downloaded PDFs from official internet repositories.
    """
    return download_real_pdfs(root_dir=root_dir)



if __name__ == "__main__":
    run_phase1_scraper()
