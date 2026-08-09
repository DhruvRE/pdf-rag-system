"""
Phase 4: Image Extraction + Spatial Question Linking.
Extracts embedded images/diagrams from PDFs, filters out tiny junk label glyphs (< 35px or < 1200 sq pt),
spatially links diagrams to the nearest/containing question bounding box, and saves images under
data/parsed/<class>/<subject>/<year>/<paper_id>/images/q<question_id>_<n>.png.
"""

import os
import json
import fitz
from PIL import Image as PILImage
import io
from datetime import datetime, timezone

from src.config import PROJECT_ROOT, CONTEXT_PATH

# Thresholds to eliminate 17x20px single-letter glyphs (O, P, Q, T, A, B, C, D)
MIN_IMAGE_WIDTH = 35.0
MIN_IMAGE_HEIGHT = 35.0
MIN_IMAGE_AREA = 1200.0


def extract_and_link_images(paper_id: str, root_dir: str = PROJECT_ROOT) -> dict:
    """
    Extracts diagram images for a paper_id, links them to questions in questions.json,
    saves PNG files under images/, and updates .agent/context.json.
    """
    context_path = CONTEXT_PATH if root_dir == PROJECT_ROOT else os.path.join(root_dir, ".agent", "context.json")
    with open(context_path, 'r', encoding='utf-8') as f:

        ctx = json.load(f)

    if paper_id not in ctx["papers"]:
        raise KeyError(f"Paper ID {paper_id} not found in context.json")

    p_info = ctx["papers"][paper_id]
    cls = p_info["class"]
    subject = p_info["subject"]
    year = p_info["year"]
    pdf_abs_path = os.path.join(root_dir, p_info["relative_path"])

    parsed_dir = os.path.join(root_dir, "data", "parsed", cls, subject, year, paper_id)
    questions_json_path = os.path.join(parsed_dir, "questions.json")

    if not os.path.exists(questions_json_path):
        raise FileNotFoundError(f"questions.json missing at {questions_json_path}. Run Phase 3 segment first.")

    with open(questions_json_path, 'r', encoding='utf-8') as f:
        q_data = json.load(f)

    images_dir = os.path.join(parsed_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    doc = fitz.open(pdf_abs_path)
    total_images_linked = 0
    total_images_filtered = 0

    try:
        # Index questions by page
        questions_by_page = {}
        for q in q_data["questions"]:
            p_num = q["page_num"]
            questions_by_page.setdefault(p_num, []).append(q)

        # Process each page
        for page_idx, page in enumerate(doc):
            page_num = page_idx + 1
            page_questions = questions_by_page.get(page_num, [])
            if not page_questions:
                continue

            image_info_list = page.get_image_info(xrefs=True)
            for img_info in image_info_list:
                bbox = img_info["bbox"] # [x0, y0, x1, y1]
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                area = width * height

                # Filter tiny glyphs / letter icons
                if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT or area < MIN_IMAGE_AREA:
                    total_images_filtered += 1
                    continue

                xref = img_info["xref"]
                if xref == 0:
                    continue

                # Extract image pixmap
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                except Exception:
                    continue

                # Find matching question on same page based on bbox overlap / y-distance
                img_y_center = (bbox[1] + bbox[3]) / 2.0
                best_q = None
                min_dist = float('inf')

                for q in page_questions:
                    q_bbox = q["bounding_box"]
                    # If image center falls inside question vertical bounds [q_y0, q_y1]
                    if q_bbox[1] <= img_y_center <= q_bbox[3]:
                        best_q = q
                        break
                    
                    # Otherwise calculate distance to question bounds
                    q_y_center = (q_bbox[1] + q_bbox[3]) / 2.0
                    dist = abs(img_y_center - q_y_center)
                    if dist < min_dist:
                        min_dist = dist
                        best_q = q

                if best_q:
                    q_id = best_q["question_id"]
                    existing_imgs = best_q.setdefault("images", [])
                    img_n = len(existing_imgs) + 1
                    img_filename = f"{q_id}_{img_n}.png"
                    img_rel_path = os.path.join("images", img_filename)
                    img_abs_path = os.path.join(images_dir, img_filename)

                    # Convert & save as PNG using PIL
                    try:
                        pil_img = PILImage.open(io.BytesIO(image_bytes))
                        pil_img.save(img_abs_path, format="PNG")

                        existing_imgs.append({
                            "filename": img_filename,
                            "relative_path": img_rel_path,
                            "bounding_box": [round(b, 2) for b in bbox],
                            "width": round(width, 2),
                            "height": round(height, 2)
                        })
                        total_images_linked += 1
                    except Exception as e:
                        print(f"Error saving image for xref {xref}: {e}")
    finally:
        doc.close()

    # Save updated questions.json
    with open(questions_json_path, 'w', encoding='utf-8') as f:
        json.dump(q_data, f, indent=2)

    # Update context.json
    p_info["phase_status"]["image_link"] = "done"
    p_info["updated_at"] = datetime.now(timezone.utc).isoformat()
    ctx["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(context_path, 'w', encoding='utf-8') as f:
        json.dump(ctx, f, indent=2)

    print(f"Linked {total_images_linked} images (filtered {total_images_filtered} tiny glyphs) for paper {paper_id}")
    return q_data
