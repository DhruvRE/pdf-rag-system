"""
Stage 2 & Stage 3: Image Cropping, Bounding-Box Placeholder Mapping, and Storage.
Handles:
1. Stage 2: Extracting image bounding boxes, surrounding captions, page numbers, and generating [IMAGE_PLACEHOLDER_N] tokens.
2. Stage 3: Cropping image regions, saving PNG files to local/cloud storage, and returning rich image manifest dicts.
"""

import os
import fitz
import re
from src.config import PROJECT_ROOT


def get_surrounding_caption(page: fitz.Page, img_bbox: list, context_margin: float = 80.0) -> str:
    """
    Extracts text nearby an image bounding box to serve as spatial context/caption.
    """
    x0, y0, x1, y1 = img_bbox
    rect = fitz.Rect(
        max(0, x0 - context_margin),
        max(0, y0 - context_margin),
        x1 + context_margin,
        y1 + context_margin
    )
    caption_text = page.get_text("text", clip=rect).strip()
    # Clean up multiline breaks into a single caption snippet
    caption = re.sub(r"\s+", " ", caption_text)
    return caption[:200] if caption else "No nearby text found"


def crop_and_map_images(pdf_path: str, output_dir: str) -> dict:
    """
    Stage 2 & 3: Crops figures from PDF, maps them to [IMAGE_PLACEHOLDER_N] with bbox and caption metadata.
    Saves image assets under output_dir/images/.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found at {pdf_path}")

    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    placeholder_manifest = {}
    placeholder_counter = 1

    try:
        for page_idx, page in enumerate(doc):
            page_num = page_idx + 1
            image_info_list = page.get_images(full=True)

            for img_idx, img_info in enumerate(image_info_list):
                xref = img_info[0]
                pix = fitz.Pixmap(doc, xref)

                # Skip tiny icons / bullet point glyphs
                if pix.width < 35 or pix.height < 35:
                    pix = None
                    continue

                # Convert CMYK/RGB if necessary
                if pix.n >= 5:
                    pix = fitz.Pixmap(fitz.csRGB, pix)

                filename = f"img_p{page_num}_{img_idx + 1}.png"
                img_path = os.path.join(images_dir, filename)
                pix.save(img_path)
                pix = None

                # Find image rect bounding box on page
                img_rects = page.get_image_rects(xref)
                if img_rects:
                    r = img_rects[0]
                    bbox = [round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2)]
                else:
                    bbox = [0.0, 0.0, round(page.rect.width, 2), round(page.rect.height, 2)]

                caption = get_surrounding_caption(page, bbox)
                placeholder_key = f"[IMAGE_PLACEHOLDER_{placeholder_counter}]"

                rel_to_proj = os.path.relpath(img_path, PROJECT_ROOT)
                placeholder_manifest[placeholder_key] = {
                    "placeholder": placeholder_key,
                    "filename": filename,
                    "url": rel_to_proj,
                    "relative_path": rel_to_proj,
                    "page": page_num,
                    "bbox": bbox,
                    "width": pix.width if pix else 0,
                    "height": pix.height if pix else 0,
                    "caption_nearby": caption
                }
                placeholder_counter += 1

    finally:
        doc.close()

    return placeholder_manifest
