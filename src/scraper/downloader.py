"""
Real PDF Scraper & Downloader for official question paper PDFs.
Downloads actual question paper PDFs from official educational repositories (CBSE),
validates them with sanity checks, and stores them under data/raw_pdfs/<class>/<subject>/<year>/.
"""

import os
import ssl
import json
import urllib.request
import shutil
import hashlib
from datetime import datetime, timezone
from src.scraper.sanity import validate_pdf

from src.config import PROJECT_ROOT, CONTEXT_PATH


REAL_PDF_SOURCES = [
    # Class 12 Physics
    { "class": "12", "subject": "physics", "year": "2024-2025", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2024_25/Physics-SQP.pdf", "filename": "class12_physics_2024_2025_sqp.pdf" },
    { "class": "12", "subject": "physics", "year": "2023-2024", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2023_24/Physics-SQP.pdf", "filename": "class12_physics_2023_2024_sqp.pdf" },
    { "class": "12", "subject": "physics", "year": "2022-2023", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2022_23/Physics-SQP.pdf", "filename": "class12_physics_2022_2023_sqp.pdf" },

    # Class 12 Chemistry
    { "class": "12", "subject": "chemistry", "year": "2024-2025", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2024_25/Chemistry-SQP.pdf", "filename": "class12_chemistry_2024_2025_sqp.pdf" },
    { "class": "12", "subject": "chemistry", "year": "2023-2024", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2023_24/Chemistry-SQP.pdf", "filename": "class12_chemistry_2023_2024_sqp.pdf" },
    { "class": "12", "subject": "chemistry", "year": "2022-2023", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2022_23/Chemistry-SQP.pdf", "filename": "class12_chemistry_2022_2023_sqp.pdf" },

    # Class 12 Mathematics
    { "class": "12", "subject": "mathematics", "year": "2024-2025", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2024_25/Maths-SQP.pdf", "filename": "class12_mathematics_2024_2025_sqp.pdf" },
    { "class": "12", "subject": "mathematics", "year": "2022-2023", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2022_23/Maths-SQP.pdf", "filename": "class12_mathematics_2022_2023_sqp.pdf" },

    # Class 12 Biology
    { "class": "12", "subject": "biology", "year": "2024-2025", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2024_25/Biology-SQP.pdf", "filename": "class12_biology_2024_2025_sqp.pdf" },
    { "class": "12", "subject": "biology", "year": "2023-2024", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2023_24/Biology-SQP.pdf", "filename": "class12_biology_2023_2024_sqp.pdf" },
    { "class": "12", "subject": "biology", "year": "2022-2023", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2022_23/Biology-SQP.pdf", "filename": "class12_biology_2022_2023_sqp.pdf" },

    # Class 12 Computer Science & Physical Education
    { "class": "12", "subject": "computer_science", "year": "2024-2025", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2024_25/ComputerScience-SQP.pdf", "filename": "class12_computer_science_2024_2025_sqp.pdf" },
    { "class": "12", "subject": "computer_science", "year": "2023-2024", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2023_24/ComputerScience-SQP.pdf", "filename": "class12_computer_science_2023_2024_sqp.pdf" },
    { "class": "12", "subject": "physical_education", "year": "2024-2025", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2024_25/PhysicalEducation-SQP.pdf", "filename": "class12_physical_education_2024_2025_sqp.pdf" },

    # Class 12 Commerce
    { "class": "12", "subject": "accountancy", "year": "2024-2025", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2024_25/Accountancy-SQP.pdf", "filename": "class12_accountancy_2024_2025_sqp.pdf" },
    { "class": "12", "subject": "economics", "year": "2024-2025", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2024_25/Economics-SQP.pdf", "filename": "class12_economics_2024_2025_sqp.pdf" },
    { "class": "12", "subject": "business_studies", "year": "2024-2025", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassXII_2024_25/BusinessStudies-SQP.pdf", "filename": "class12_business_studies_2024_2025_sqp.pdf" },

    # Class 10 Science & Mathematics
    { "class": "10", "subject": "science", "year": "2024-2025", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassX_2024_25/Science-SQP.pdf", "filename": "class10_science_2024_2025_sqp.pdf" },
    { "class": "10", "subject": "science", "year": "2023-2024", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassX_2023_24/Science-SQP.pdf", "filename": "class10_science_2023_2024_sqp.pdf" },
    { "class": "10", "subject": "physics", "year": "2022-2023", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassX_2022_23/Science-SQP.pdf", "filename": "class10_science_2022_2023_sqp.pdf" },
    { "class": "10", "subject": "mathematics", "year": "2024-2025", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassX_2024_25/MathsStandard-SQP.pdf", "filename": "class10_mathematics_2024_2025_sqp.pdf" },
    { "class": "10", "subject": "mathematics", "year": "2023-2024", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassX_2023_24/MathsStandard-SQP.pdf", "filename": "class10_mathematics_2023_2024_sqp.pdf" },
    { "class": "10", "subject": "mathematics", "year": "2022-2023", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassX_2022_23/MathsStandard-SQP.pdf", "filename": "class10_mathematics_2022_2023_sqp.pdf" },
    { "class": "10", "subject": "social_science", "year": "2024-2025", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassX_2024_25/SocialScience-SQP.pdf", "filename": "class10_social_science_2024_2025_sqp.pdf" },
    { "class": "10", "subject": "social_science", "year": "2023-2024", "url": "https://cbseacademic.nic.in/web_material/SQP/ClassX_2023_24/SocialScience-SQP.pdf", "filename": "class10_social_science_2023_2024_sqp.pdf" }
]


def generate_paper_id(cls: str, subject: str, year: str, filename: str) -> str:
    """Generates a deterministic 12-character paper_id hash key."""
    key = f"{cls}_{subject}_{year}_{filename}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[:12]


def download_real_pdfs(root_dir: str = PROJECT_ROOT) -> dict:
    """
    Downloads real PDF question papers from official sources, checks corruption/sanity,
    stores them under data/raw_pdfs/<class>/<subject>/<year>/ and updates .agent/context.json.
    """
    raw_pdfs_base = os.path.join(root_dir, "data", "raw_pdfs")
    fixtures_base = os.path.join(root_dir, "tests", "fixtures")
    context_path = CONTEXT_PATH if root_dir == PROJECT_ROOT else os.path.join(root_dir, ".agent", "context.json")


    os.makedirs(raw_pdfs_base, exist_ok=True)
    os.makedirs(fixtures_base, exist_ok=True)

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    results = {
        "total": len(REAL_PDF_SOURCES),
        "valid": 0,
        "failed": 0,
        "papers": {}
    }

    papers_context = {}

    for item in REAL_PDF_SOURCES:
        cls = item["class"]
        subject = item["subject"]
        year = item["year"]
        fname = item["filename"]
        url = item["url"]

        rel_dir = os.path.join(cls, subject, year)
        target_dir = os.path.join(raw_pdfs_base, rel_dir)
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, fname)

        print(f"Downloading real PDF from {url} ...")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'})
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
                pdf_bytes = resp.read()
            with open(target_path, 'wb') as f:
                f.write(pdf_bytes)
        except Exception as e:
            print(f"Error downloading {url}: {e}")

        # Copy to tests/fixtures/
        fixture_path = os.path.join(fixtures_base, fname)
        if os.path.exists(target_path):
            shutil.copy2(target_path, fixture_path)

        # Sanity validation check
        is_valid, err_msg, page_count = validate_pdf(target_path)

        # Check for images in PDF
        import fitz
        has_images = False
        if is_valid:
            doc = fitz.open(target_path)
            has_images = any(len(p.get_images()) > 0 for p in doc)
            doc.close()

        paper_id = generate_paper_id(cls, subject, year, fname)
        rel_path = os.path.join("data", "raw_pdfs", rel_dir, fname)

        status_entry = {
            "paper_id": paper_id,
            "class": cls,
            "subject": subject,
            "year": year,
            "filename": fname,
            "url": url,
            "relative_path": rel_path,
            "fixture_path": os.path.join("tests", "fixtures", fname),
            "page_count": page_count,
            "has_images": has_images,
            "phase_status": {
                "scrape": "done" if is_valid else "failed",
                "parse": "pending",
                "segment": "pending",
                "image_link": "pending",
                "chunk": "pending",
                "embed": "pending",
                "dedup": "pending"
            },
            "worker": None,
            "needs_review": not is_valid,
            "error_reason": None if is_valid else err_msg,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        papers_context[paper_id] = status_entry

        if is_valid:
            results["valid"] += 1
            print(f" -> OK ({page_count} pages, has_images={has_images}) Saved to {rel_path}")
        else:
            results["failed"] += 1
            print(f" -> FAILED sanity check: {err_msg}")

        results["papers"][paper_id] = status_entry

    context_data = {
        "schema_version": 1,
        "current_phase": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "papers": papers_context
    }

    with open(context_path, 'w', encoding='utf-8') as f:
        json.dump(context_data, f, indent=2)

    print(f"\nReal PDF Scraper complete: {results['valid']}/{results['total']} papers downloaded & validated.")
    return results


if __name__ == "__main__":
    download_real_pdfs()
