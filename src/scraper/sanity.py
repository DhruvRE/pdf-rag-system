"""
Sanity and corruption checker for scraped PDFs.
Validates that PDF files are readable, non-empty, and unencrypted.
"""

import os
import fitz  # PyMuPDF


def validate_pdf(filepath: str) -> tuple[bool, str, int]:
    """
    Validates a PDF file.

    Returns:
        (is_valid, error_message, page_count)
    """
    if not os.path.exists(filepath):
        return False, f"File does not exist: {filepath}", 0

    if os.path.getsize(filepath) == 0:
        return False, f"File is zero bytes: {filepath}", 0

    try:
        doc = fitz.open(filepath)
        if doc.is_encrypted:
            doc.close()
            return False, "PDF is password-protected/encrypted", 0

        page_count = len(doc)
        if page_count == 0:
            doc.close()
            return False, "PDF has 0 pages", 0

        # Try rendering/accessing the first page to ensure rendering engine won't crash
        first_page = doc[0]
        _ = first_page.get_text()

        doc.close()
        return True, "OK", page_count
    except Exception as e:
        return False, f"Corrupted or invalid PDF: {str(e)}", 0
