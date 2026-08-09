# AGENTS.md — PDF Question-Paper RAG/Embedder Project

> Location: this file lives at the **project root**
> (`pdf-rag-embedder/AGENTS.md`), alongside `implementation-plan.md`.
> Antigravity reads workspace rules from the project root automatically —
> do not move it into `.agent/` or `docs/`.

## Project
Scrapes question-paper PDFs, stores them by class/subject/year, then parses,
chunks, embeds (text + images), and dedupes questions across papers for a RAG
system. See `implementation-plan.md` for the full phased build plan — follow
the phase order there; do not skip ahead to a later phase before the current
one's test passes.

## Folder structure (do not deviate)
```
pdf-rag-embedder/
├── AGENTS.md                     # this file — project root
├── implementation-plan.md        # phased build plan
├── docs/pdf-image-rag-knowledge.md
├── .agent/context.json           # shared multi-worker state
├── data/
│   ├── raw_pdfs/<class>/<subject>/<year>/*.pdf
│   ├── parsed/<class>/<subject>/<year>/<paper_id>/
│   │   ├── pages.json            # phase 2 output
│   │   ├── questions.json        # phase 3 output
│   │   └── images/q<question_id>_<n>.png
│   └── vector_store/             # phase 6 output — never hand-edit
├── src/
│   ├── scraper/          # phase 1
│   ├── parsing/           # phase 2
│   ├── segmentation/      # phase 3
│   ├── image_linking/     # phase 4
│   ├── chunking/          # phase 5
│   ├── embedding/         # phase 6
│   ├── dedup/             # phase 7
│   └── retrieval/         # phase 8
├── tests/
│   ├── fixtures/           # small sample PDFs, not the full corpus
│   ├── labeled/            # hand-labeled question boundaries (phase 3 ground truth)
│   ├── eval_queries.json   # phase 8 fixed eval set
│   └── test_<phase_name>.py
└── scripts/run_phase.py    # CLI entrypoint to run one phase at a time
```
Rules:
- Work on one phase = touch only that phase's `src/<phase>/` folder. Don't
  reach into another phase's folder to "fix" something — flag it instead.
- Never write generated output anywhere except under `data/`.
- No new top-level folders/files without updating this structure first.

## Classification schema (source of truth — never invent values)
- class: 1–12
- subject: <fixed enum — list actual subjects here>
- year: format YYYY-YYYY
- difficulty: <Bloom's-taxonomy-tied levels — define here>

If a PDF/question doesn't cleanly map to these, mark it `needs_review` in
`.agent/context.json` instead of guessing a value.

## Chunking rule
One chunk = one question (text + its linked image, if any). Never chunk at
page level — a page can contain multiple unrelated questions.

## Shared context file (READ FIRST, ALWAYS)
Before doing any work, read `.agent/context.json`.
- It is the single source of truth for: which papers/questions have been
  processed, what phase they're at, and what's pending or needs review.
- Do NOT re-scan the full PDF corpus or re-derive state by reading everything —
  that state lives in context.json.
- Before starting work on a paper/phase, claim it: set your worker ID and
  `"in-progress"` on that phase_status entry.
- After finishing, update the entry to `"done"` or `"failed"` (with a reason).
  This is not optional — it's how other workers avoid duplicate work.
- Only edit entries you claimed. Never modify another worker's in-progress
  entries or delete their history.
- If a paper has no entry in context.json, treat it as untouched (phase 1).

## Concurrency
- One worker owns one paper/phase at a time.
- If an entry is `"in-progress"` and its `updated_at` is older than the agreed
  timeout, treat the claim as stale and safe to reclaim — otherwise skip it.

## Output conventions
- Parsed output, extracted images, and embeddings follow the folder layout in
  `implementation-plan.md` Section 2 (`data/parsed/<class>/<subject>/<year>/<paper_id>/`).
- Image filenames: `q<question_id>_<n>.png`.
- `paper_id` is the deterministic join key used everywhere — never regenerate
  it differently in different scripts.

## Testing discipline
Every phase has a defined test in `implementation-plan.md`. A phase is not
"done" until that test passes on the hand-checked sample — report the test
result when marking a phase complete, don't just mark it done silently.