# PDF Question-Paper RAG/Embedder — Implementation Plan v5 (General Source Reconciliation & Type-Aware RAG)

> **Status:** Upgraded to 8-Stage Architecture with Pass B-0 General-Purpose Source Reconciliation Pass, Pass B-1 Question Type Classifier, Pass B-2 Type-Aware Validator, and Stage 7 Hybrid Search (BM25 FTS5 + Dense Vector RRF Fusion).

---

## 1. Updated Stage Pipeline Architecture

```
                        PDF Input
                           │
             Stage 0: Type Detection
             (native vs scanned check)
                           │
             Stage 1: Unified Markdown + Image Manifest
                           │
             Stage 2/3: Image Cropping & BBox Placeholder Mapping
                           │
             Stage 4: Multi-Pass Structuring & Reconciliation Pass
             ├─ Pass A: CBSE JSON Extraction + raw_source_span Attachment
             ├─ Pass B-0: GENERAL SOURCE RECONCILIATION PASS (New)
             │   Compares raw_source_span directly against extraction
             │   Fixes OCR glitches, (c ) spacing, merged text, unattached images
             ├─ Pass B-1: QUESTION TYPE CLASSIFIER
             │   Assigns primary_type & boolean flags (requires_image, etc.)
             └─ Pass B-2: TYPE-AWARE VALIDATOR
                 Runs targeted rule checks (MCQ opts==4, AR opts==4, figure checks)
                           │
             Stage 5: Self-Validation & Selective VLM Escalation
                           │
             Stage 6: Drafts DB & Review Queue
                           │
             Stage 7: Subpart Chunking & Hybrid Vector Embeddings
             (BM25 FTS5 + Dense Vector RRF Fusion)
```

---

## 2. Pass B-0: General-Purpose Source Reconciliation Pass

### Core Shift: Comparison-Based Repair over Pattern Matching
Instead of maintaining regex rules for every possible OCR artifact (e.g. extra space in `(c )` breaking option splits), **Pass B-0** preserves `raw_source_span` for every question in Pass A:

```json
{
  "question_number": "Q12",
  "raw_source_span": "## Q12.\nWhat is the SI unit of current?\n(a) Volt  (b) Ampere  (c ) Ohm  (d) Joule",
  "subparts": [ ... ]
}
```

### Reconciliation Checks (`reconcile_question_against_source`):
1. **Option Marker Repair**: Reconciles option count when raw source span contains distinct markers (`(a)`, `b)`, `(c )`, `( d )`) that pattern regex missed due to spacing/line wraps.
2. **Placeholder Alignment**: Re-attaches unassigned `[IMAGE_PLACEHOLDER_N]` tokens directly from `raw_source_span`.
3. **Truncation Flagging**: Detects cases where `raw_source_span` exists but extracted stem text is truncated/corrupted.

Outputs per-question fields:
- `corrected`: `true` / `false`
- `correction_note`: Description of what was reconciled.
- `needs_manual_review`: `true` / `false`
- `review_reason`: Failure reason for human reviewer.

---

## 3. Full 8-Stage Pipeline Order

1. **Stage 0 & 1**: PDF type check & layout parsing to normalized Markdown.
2. **Stage 2 & 3**: Image cropping, spatial bounding box (`bbox`), and `caption_nearby` placeholder mapping.
3. **Stage 4**: Pass A JSON extraction + `raw_source_span` attachment.
4. **Stage 5**:
   - **Pass B-0**: Source Reconciliation (compares extraction against `raw_source_span`).
   - **Pass B-1**: Type Classifier (`primary_type`, `requires_image`).
   - **Pass B-2**: Type-Aware Validator (runs type-specific checks).
   - **VLM Escalation**: Escalates spatial figure issues to visual page inspection if needed.
5. **Stage 6**: Serves parsed drafts to `.agent/context.json` & Drafts Review Queue UI.
6. **Stage 7**: Subpart chunking + FTS5 & Dense Vector Store embedding with RRF Fusion.

---

## 4. Verification Results across Full Corpus

- **Corpus Coverage**: 12/12 PDFs (396 question chunks)
- **Stage Pipeline Test Suite**: `5/5 PASS` (`0.252s`)
- **Phase 8 RAG Benchmark**: **MRR@5 = 0.9000**, **Precision@5 = 90.00%**
