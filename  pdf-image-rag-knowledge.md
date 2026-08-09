# Knowledge Reference: PDF Text/Image Alignment for RAG

Source concept: "Parsing PDFs for Image Retrieval in the RAG Framework" (Medium,
Nvmukesh). This doc summarizes the underlying technique in plain terms and notes
where it needs adapting for question papers specifically.

---

## 1. The Core Problem

When a PDF has both text and images (a diagram next to a question, a chart next
to a paragraph), a plain text-only RAG pipeline throws the images away. To
retrieve them meaningfully, you need to preserve **which image belongs to which
piece of text** all the way through extraction → chunking → embedding →
storage, so a single retrieval query can pull back both together.

## 2. How the Reference Approach Works (page-level)

1. **Open the PDF** with a parsing library that gives access to both text and
   embedded images per page (e.g. PyMuPDF/`fitz`, or `pdfplumber`).
2. **Treat each page as one unit.** For every page: pull the full text, pull
   any embedded images.
3. **Extract and store images separately** — save each image as a file
   (locally or in cloud storage), and record its path/URL.
4. **Attach images to the page's text as metadata.** The text becomes the
   embeddable content; the image path(s) ride along as metadata rather than
   being embedded themselves.
5. **Embed the text** with a text embedding model and store it in a vector DB,
   with the image paths attached to that same record.
6. **At query time**, a similarity search on the text returns matching
   records — and because the image paths are attached as metadata, you get
   the associated images back for free, without a separate image search.

The key design choice here is **granularity = one page = one retrievable
unit**, and **linking = "whatever images are on this page belong to this
page's text"** (positional proximity by page, not by finer position).

## 3. Where This Approach Breaks for Question Papers

- **Multiple questions per page.** If a page has Q4, Q5, and Q6, and Q5 has a
  diagram, page-level linking will associate that diagram with Q4 and Q6's
  text too — wrong retrieval, wrong dedup comparisons, wrong metadata.
- **No true positional linking.** The reference approach links "image ∈ page"
  not "image ∈ question." It doesn't use bounding-box coordinates to figure
  out which image is physically closest to which text block.
- **Image itself isn't embedded**, only referenced by path. Fine for basic
  text-triggers-image retrieval, but if you want to search *by* image
  content (e.g. "find questions with a similar circuit diagram") or use a
  VLM to reason about the diagram, you need the image content embedded or
  captioned, not just linked as a file path.
- **No dedup logic** — the reference approach is purely about retrieval, not
  about identifying that "this is the same question as one from 2 years ago."

## 4. What to Carry Over vs Change

| Reference approach | Your project needs |
|---|---|
| Chunk = 1 page | Chunk = 1 question |
| Image linked by "same page" | Image linked by bounding-box proximity to the specific question region |
| Image stored as file path only | Image path stored **and** image content embedded/captioned (Qwen-VL) for visual retrieval |
| Text embedded, image passive metadata | Text embedded + image embedded/captioned, both joined by `question_id` |
| No duplicate detection | Cosine-similarity comparison across question embeddings, VLM confirms borderline cases |

## 5. Practical Takeaways to Reuse Directly

- Extracting text and images together in a single pass over the PDF (rather
  than two separate passes) keeps them naturally associated before you lose
  the positional context — do this in Phase 2/4 of the implementation plan.
- Storing images as separate files with a path reference in your DB (rather
  than storing raw image bytes in the vector DB) keeps the DB lean — reuse
  this pattern, just make the reference `question_id`-based instead of
  `page`-based.
- Treating "parse → chunk → embed → store" as separable stages (rather than
  one monolithic script) is what makes your phase-by-phase testing plan
  possible in the first place — this modularity is worth keeping even though
  the granularity changes.

## 6. Where This Fits in the Implementation Plan

This doc informs **Phase 2 (raw parsing bench)** and **Phase 4 (image
extraction + question linking)** in `implementation-plan.md`. Read those two
phases alongside this doc — the difference from the reference approach is
entirely about *granularity* (question vs. page), not about the general
shape of the pipeline.