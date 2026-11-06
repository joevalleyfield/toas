Filed as: 261106-content-spillage-refinement
FKA:
AKA: spill preview refinement; head tail spillage; error focus spillage; call time spill threshold; repetitive output elision; dense spill language
Legacy index:

keywords: rendering, tools, spillage, preview, head_tail, error_focus, elision, thresholds, active

Related: `261106-bounded-step-quiescence`; `261020-tool-spill-ephemerality-comment-scoping`; `261010-scratch-read-file-ingestion-threshold`

# Content Spillage Refinement: Dynamic Thresholds, Bookends, Error Focus, and Elision

## Intent

Refine TOAS inert-block content spillage beyond the naive "first $N$ lines"
slice by introducing:
1. Flexible preview strategies (`head_tail` bookends, `head_shuf_tail` striding,
   and anchor-based `error_focus`).
2. Repetitive noise filtering (collapsing consecutive duplicate lines).
3. Call-time threshold overrides and dense specification (allowing operators
   and models to request higher spill thresholds like `>500` or named profiles).

## Context & Motivation

When tool outputs exceed spillage thresholds (default 40 lines / 4,000 bytes),
`spill_inert_block` in `src/toas/tools_cluster/rendering.py` writes the full
payload to `.toas/scratch/<block_id>.txt` and renders an in-transcript preview.

Currently, that preview is hardcoded to `lines[:preview_lines]` (the first 30 lines).
In practice, head-only previews are frequently counter-productive:

1. **Test Runners (`pytest`, `cargo test`, `jest`)**:
   The first 30 lines contain environment headers, platform flags, and passing
   dots. The actual failure summaries, assertion diffs, and stack traces reside
   in the last 20–40 lines. Head-only previews force the agent to execute a
   redundant `read_file` or `tail` step just to see what broke.
2. **Stack Traces & Errors**:
   Python tracebacks place the root exception on the very last line.
3. **Repetitive Garbage**:
   Polling logs, progress spinners, or repetitive warnings often fill the entire
   30-line preview with identical lines, pushing useful context out of view.
4. **Rigid Thresholds**:
   The 40-line threshold cannot be adjusted per call. Even when an operator or
   model knows an output is ~150 lines and wants to see it contiguously, it
   spills prematurely unless a clumsy bash command is used.

## In Scope

### 1. Multi-Mode Preview Extractors

Replace the hardcoded `lines[:preview_lines]` with configurable preview extractors:
- **`head_tail` (Bookends)**:
  Extracts the first $H$ lines (e.g. 10 lines for invocation/context), an omission
  marker `[... K lines omitted; full output in <path> ...]`, and the last $T$
  lines (e.g. 20 lines for failures/summaries). Total lines $\le$ preview budget.
- **`head_shuf_tail` (Strided / Sampled)**:
  Combines head, tail, and representative periodic samples across the middle.
  Ideal for large data listings, tables, or search batches.
- **`error_focus`**:
  Scans the output for known diagnostic anchors:
  `FAILED`, `ERROR`, `Traceback (most recent call last):`, `AssertionError`,
  `panic:`, `fatal:`, `FAIL:`.
  If found, centers the preview around the error site (e.g. 5 lines leading up
  to the error and 25 lines of traceback/details). Falls back to `head_tail` if
  no error markers are present.
- **`head`**:
  Retains classic top-first slicing for rank-ordered search results and doc reads.

### 2. Repetitive Line Elision

- Detect and collapse consecutive identical or near-identical lines before
  slicing previews:
  ```text
  waiting for daemon... [repeated 38 times]
  ```
- Prevents runaway loops or polling spam from consuming the preview budget.

### 3. Call-Time Threshold Overrides & Dense Syntax

Allow the model or operator to customize spillage per invocation:
- **Call-Time Arguments** on `shell`, `shell_script`, `read_file`:
  - `threshold_lines: int` (e.g. `threshold_lines: 500`)
  - `spill_mode: str` (e.g. `spill_mode: "tail"`)
- **Dense Syntax String (`spill`)**:
  - `spill: ">500"` (only spill if exceeding 500 lines)
  - `spill: "tail@300"` (tail preview mode with 300 line threshold)
  - `spill: "test"` (named profile shortcut)
- **Safety Ceiling**:
  Call-time thresholds remain bounded by `DEFAULT_SPILL_SAFETY_BRAKE_LINES`
  (1,000 lines) to prevent accidental context blowouts.

### 4. Configuration Namespace (`config.spill.*`)

Introduce structured spillage configuration in `src/toas/config.py`:
- `spill.default_mode: str = "head_tail"`
- `spill.head_lines: int = 10`
- `spill.tail_lines: int = 20`
- `spill.elide_duplicates: bool = True`
- `spill.threshold_lines: int = 40`
- `spill.profiles: dict[str, SpillProfile]` (predefined profiles like `test`, `raw`, `wide`).
- Interactive slash command: `/config set spill.default_mode head_tail`.

### 5. Clear Fence Annotations

When spillage is non-contiguous (e.g. `head_tail`), format the fence info string
explicitly so models and operators understand the slice structure:
```text
```text toas-output kind=shell block_id=ib_8f2a path=".toas/scratch/ib_8f2a.txt" lines=1..10,480..500 of 500
[first 10 lines]
--- [470 lines omitted; full output in .toas/scratch/ib_8f2a.txt] ---
[last 20 lines]
```
```

## Out of Scope

- Heuristic semantic compression that modifies the content of the spilled
  scratch file (the raw file on disk is ALWAYS 100% faithful and unedited).
- Semantic summarization via secondary LLM calls.

## Acceptance Criteria

1. **`head_tail` Default for Commands**: In `head_tail` mode, an output of 200
   lines displays lines 1–10, an explicit omission divider, and lines 181–200.
2. **Error-Focus Prioritization**: When a command output contains `Traceback` or
   `FAILED`, `error_focus` centers the preview on the failure site rather than
   the command startup banner.
3. **Duplicate Elision**: 50 identical consecutive lines are collapsed into a
   single representative line and a count marker.
4. **Call-Time Threshold Elevation**: Supplying `threshold_lines: 300` or
   `spill: ">300"` on a 250-line `shell` command does not spill, emitting the
   full output within safety brake limits.
5. **Safety Brake Enforcement**: Requesting `threshold_lines: 50000` is safely
   clamped to `DEFAULT_SPILL_SAFETY_BRAKE_LINES` (1,000 lines).
6. **Scratch File Invariant**: `.toas/scratch/<block_id>.txt` contains the exact,
   unmodified, complete byte stream regardless of preview mode or elision.
