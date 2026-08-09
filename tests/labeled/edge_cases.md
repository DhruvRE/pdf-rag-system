# Phase 3 Question Segmentation — Edge Cases & False-Positive Checklist

This document tracks known real-world PDF edge cases, false-positive risks, and formatting variations encountered across official board examination question papers.

---

## 1. Documented Edge Cases & Patterns

### 1.1 Section Header Variances
* **Pattern**: `Section-A`, `SECTION A`, `Section A`, `SECTION - E`, `General Instructions`
* **Risk**: Non-standard hyphens (`Section-A`) or spaces (`SECTION - E`) causing section tracking to fail, leaving questions under `HEADER` scope.
* **Fix**: Flexible regex `r"^\s*(?:<b>)?\s*(Section\s*[\-\:\s]*[A-E]|SECTION\s*[\-\:\s]*[A-E])"` with space/hyphen normalization.

### 1.2 Format A: Dot-Notation & Prefix Variations
* **Pattern**: `Q.20.`, `Q13. Assertion (A):`, `Question 1:`
* **Risk**: Dot after Q (`Q.20.`) causing regex to miss question starts or match `20.` as a sub-part.
* **Fix**: Explicit `r"Q\.?\s*(\d{1,3})[\.\:]"` pattern and `Q.` -> `Q` string normalization.

### 1.3 Format B: Plain Numbering
* **Pattern**: `1.`, `2.`, `21.`, `38.`
* **Risk**: Option labels (`A.`, `B.`, `C.`, `D.`) or instruction list items (`1. All questions are compulsory`) misparsed as question starts.
* **Fix**: Ignore instruction numbers occurring under `General Instructions` before `SECTION A`. Explicitly filter single uppercase letter option labels `^[A-D]\.$`.

### 1.4 Format C: Standalone Integer Line Numbers
* **Pattern**: Integer `1`, `2`, `3`, `8` on a line by itself above question text (common in Class 10 Science & Maths papers).
* **Risk**: Page numbers at the top/bottom of pages or table cell numbers triggering false-positive question starts.
* **Fix**: Standalone integer regex `^\s*(\d{1,2})\s*$` requiring the immediate next line to contain non-header question text (> 5 chars, not `Page` or `Marks`).

### 1.5 False-Positive Risks: Graph Axes & Scientific Constants
* **Pattern**: Graph tick mark numbers `7.5`, `8.0`, `8.5` in nuclear binding energy curves or rate constants `k = 2.31x 10-2 molL-1s-1`.
* **Risk**: Floating point numbers or constants (e.g. `3.70`) starting a line matched as new question headers.
* **Fix**: Require `\.(?:\s+|$)` (dot followed by space or newline) so `3.70` is not matched as `3.`.

### 1.6 Right-Margin Mark Values & Fraction Fragments
* **Pattern**: Standalone digits at the right margin (`x0 ≈ 514–537pt`) representing mark allocations (`1`, `2`, `3`, `5` marks); fraction numerators/denominators (`5/2`, `11/9`) split across separate text blocks in multi-column MCQ layouts.
* **Risk**: These get matched as new question starts because they satisfy bare integer rules without an x-position exclusion, creating duplicate IDs (e.g., `Q5`, `Q6`, `Q9` appearing multiple times with garbage fragments).
* **Fix**: Exclude standalone integer matches whose bounding-box `x0` falls in the right-margin band (`x0 > page_width - 90pt`), and require a left-margin constraint (`x0 < 85pt`) before treating a bare number as a question start.

### 1.7 Mid-Paper Subsection Headers
* **Pattern**: `DIRECTION: In question numbers...`, `ASSERTION-REASON BASED QUESTIONS`, `Direction for Q...`
* **Risk**: Question bounding box or question body absorbing the assertion-reason instruction block or choices from the general directions paragraph.
* **Fix**: Include mid-paper subsection headers (`Direction:`, `ASSERTION-REASON`, `Case Study`) in section header triggers, causing the preceding question boundary to terminate immediately before the subsection instructions block.

---

## 2. Verification Checklist for New Papers

Before marking any new paper or dataset phase complete:
- [ ] Confirm no instruction list items (e.g. `1. All questions are compulsory`) are captured as questions.
- [ ] Confirm Assertion-Reason questions (`Q13`..`Q16`) maintain full question body and do not leak `(A)` into MCQ choices or absorb subsection instruction text.
- [ ] Confirm right-margin mark values (`1`, `2`, `3`, `5`) at `x0 > page_width - 90pt` do not trigger duplicate question IDs.
- [ ] Confirm fraction numerators/denominators in multi-column MCQ options do not create stray question fragments.
- [ ] Confirm strict total count matching: `len(question_ids) == len(set(question_ids)) == expected_total_questions`.
