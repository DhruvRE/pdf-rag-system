import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from src.scraper.scraper import run_phase1_scraper
from src.parsing.parser import parse_paper
from src.segmentation.segmenter import segment_paper
from src.image_linking.extractor import extract_and_link_images
from src.chunking.chunker import chunk_paper
from src.embedding.embedder import embed_paper_chunks
from src.dedup.deduplicator import run_deduplication
from src.retrieval.retriever import retrieve_questions, format_rag_context


def main():
    parser = argparse.ArgumentParser(description="PDF Question-Paper RAG Phase Runner")
    parser.add_argument(
        "--phase",
        type=int,
        required=True,
        help="Phase number to run (1: Scraper, 2: Parsing, 3: Segmentation, 4: Image Linking, 5: Chunking, 6: Embedding, 7: Deduplication, 8: Retrieval)"
    )
    parser.add_argument(
        "--paper_id",
        type=str,
        default=None,
        help="Optional paper_id to run Phase 2..6 against"
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Optional search query string for Phase 8 RAG retrieval"
    )
    args = parser.parse_args()

    if args.phase == 1:
        print("=== Running Phase 1: Scraper + Storage ===")
        results = run_phase1_scraper()
        if results["failed"] > 0:
            print(f"Phase 1 completed with errors: {results['failed']} papers failed validation.")
            sys.exit(1)
        else:
            print(f"Phase 1 SUCCESS: All {results['valid']} papers scraped and validated.")
            sys.exit(0)
    elif args.phase == 2:
        print("=== Running Phase 2: Raw Parsing Bench ===")
        import json
        with open(".agent/context.json", "r") as f:
            ctx = json.load(f)
        
        target_papers = [args.paper_id] if args.paper_id else list(ctx["papers"].keys())[:3]
        skipped = 0
        for pid in target_papers:
            result = parse_paper(pid)
            if result == "":
                skipped += 1
        print(f"Phase 2 SUCCESS: Parsed {len(target_papers)-skipped} papers into pages.json. Skipped {skipped} non-English PDFs.")
        sys.exit(0)
    elif args.phase == 3:
        print("=== Running Phase 3: Question-Boundary Detection ===")
        import json
        with open(".agent/context.json", "r") as f:
            ctx = json.load(f)
        
        target_paper = args.paper_id if args.paper_id else list(ctx["papers"].keys())[0]
        result = parse_paper(target_paper)
        if result == "":
            print(f"SKIPPED (non-English): {target_paper}")
            sys.exit(0)
        q_path = segment_paper(target_paper)
        print(f"Phase 3 SUCCESS: Segmented paper {target_paper} into questions.json at {q_path}.")
        sys.exit(0)
    elif args.phase == 4:
        print("=== Running Phase 4: Image Extraction + Question Linking ===")
        import json
        with open(".agent/context.json", "r") as f:
            ctx = json.load(f)
        
        target_papers = [args.paper_id] if args.paper_id else list(ctx["papers"].keys())
        skipped = 0
        for pid in target_papers:
            result = parse_paper(pid)
            if result == "":
                skipped += 1
                continue
            segment_paper(pid)
            extract_and_link_images(pid)
        print(f"Phase 4 SUCCESS: Linked images across {len(target_papers)-skipped} papers. Skipped {skipped} non-English PDFs.")
        sys.exit(0)
    elif args.phase == 5:
        print("=== Running Phase 5: Question Chunking ===")
        import json
        with open(".agent/context.json", "r") as f:
            ctx = json.load(f)
        
        target_papers = [args.paper_id] if args.paper_id else list(ctx["papers"].keys())
        skipped = 0
        for pid in target_papers:
            result = parse_paper(pid)
            if result == "":
                skipped += 1
                continue
            segment_paper(pid)
            extract_and_link_images(pid)
            chunk_paper(pid)
        print(f"Phase 5 SUCCESS: Chunked {len(target_papers)-skipped} papers into chunks.json. Skipped {skipped} non-English PDFs.")
        sys.exit(0)
    elif args.phase == 6:
        print("=== Running Phase 6: Embedding + Vector Store ===")
        import json
        with open(".agent/context.json", "r") as f:
            ctx = json.load(f)
        
        target_papers = [args.paper_id] if args.paper_id else list(ctx["papers"].keys())
        total_chunks_embedded = 0
        skipped = 0
        for pid in target_papers:
            result = parse_paper(pid)
            if result == "":
                skipped += 1
                continue
            segment_paper(pid)
            extract_and_link_images(pid)
            chunk_paper(pid)
            res = embed_paper_chunks(pid)
            total_chunks_embedded += res["total_embedded"]
        print(f"Phase 6 SUCCESS: Embedded {total_chunks_embedded} question chunks across {len(target_papers)-skipped} papers into ChromaDB. Skipped {skipped} non-English PDFs.")
        sys.exit(0)

    elif args.phase == 7:
        print("=== Running Phase 7: Duplicate / Near-Duplicate Detection ===")
        res = run_deduplication(similarity_threshold=0.85)
        print(f"Phase 7 SUCCESS: Found {res['total_duplicates_found']} duplicate/near-duplicate pairs across papers.")
        sys.exit(0)
    elif args.phase == 8:
        print("=== Running Phase 8: RAG Retrieval + Eval Harness ===")
        q = args.query or "Which of the following gives the middle most observation of the data?"
        results = retrieve_questions(q, top_k=3)
        context = format_rag_context(results)
        print(f"\n--- RAG Retrieval Output for Query: '{q}' ---\n")
        print(context)
        print(f"\nPhase 8 SUCCESS: Retrieved {len(results)} top matching chunks.")
        sys.exit(0)
    else:
        print(f"Phase {args.phase} is not yet implemented.")
        sys.exit(1)


if __name__ == "__main__":
    main()
