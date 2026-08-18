"""
scripts/fix_relative_paths.py — Cleans all hardcoded absolute paths in parsed JSON files
and normalizes them to be 100% relative to PROJECT_ROOT.
"""

import os
import json
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PARSED_DIR = os.path.join(PROJECT_ROOT, "data", "parsed")


def clean_path(path_str: str) -> str:
    """Converts absolute project paths to clean relative paths."""
    if not isinstance(path_str, str):
        return path_str
    
    # Strip any leading absolute workspace path
    if PROJECT_ROOT in path_str:
        rel = os.path.relpath(path_str, PROJECT_ROOT)
        return rel
    
    # Replace any hardcoded /home/.../pdf-rag-project/ prefix
    cleaned = re.sub(r"^/.*?/pdf-rag-project/", "", path_str)
    return cleaned


def fix_all_parsed_json_files():
    fixed_manifests = 0
    fixed_chunks = 0

    for root, dirs, files in os.walk(DATA_PARSED_DIR):
        for fname in files:
            if fname == "image_manifest.json":
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    updated = False
                    for k, v in data.items():
                        if isinstance(v, dict):
                            if "url" in v and isinstance(v["url"], str) and (PROJECT_ROOT in v["url"] or v["url"].startswith("/home")):
                                v["url"] = clean_path(v["url"])
                                updated = True
                            if "relative_path" in v and isinstance(v["relative_path"], str) and (PROJECT_ROOT in v["relative_path"] or v["relative_path"].startswith("/home")):
                                v["relative_path"] = clean_path(v["relative_path"])
                                updated = True

                    if updated:
                        with open(fpath, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                        fixed_manifests += 1
                except Exception as e:
                    print(f"Error processing {fpath}: {e}")

            elif fname in ("chunks.json", "questions.json", "structured_draft.json"):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()

                    if PROJECT_ROOT in content or "/home/harish" in content:
                        cleaned_content = re.sub(r"/home/harish/dhruv-work/pdf-rag-project/?", "", content)
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(cleaned_content)
                        fixed_chunks += 1
                except Exception as e:
                    print(f"Error processing {fpath}: {e}")

    print(f"Cleaned absolute paths in {fixed_manifests} image_manifest.json files and {fixed_chunks} JSON files.")


if __name__ == "__main__":
    fix_all_parsed_json_files()
