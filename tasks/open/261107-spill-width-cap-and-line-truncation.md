Filed as: 261107-spill-width-cap-and-line-truncation
FKA:
AKA: line width cap; spill width policy; horizontal truncation; preview width cap; long line elision; byte cap enforcement
Legacy index:

keywords: rendering, tools, spillage, width, truncation, preview, columns, active

Related: `261106-content-spillage-refinement`; `260930-paged-inert-tool-spillover`

# Spill Width Cap and Horizontal Line Truncation Policy

## Intent

Introduce an explicit line width cap and horizontal truncation policy for tool
outputs and spillage previews to prevent single or repetitive long lines (e.g.
minified assets, giant JSON records, base64 data, or wide log lines) from
blowing the model context window.

## Context & Motivation

TOAS inert-block spillage guards against vertical explosion (`threshold_lines`,
default 40) and total payload volume (`threshold_bytes`, default 4,000 bytes) by
writing the full payload to `.toas/scratch/<block_id>.txt` and projecting an
in-transcript preview.

However, the current spillage mechanism only bounds the vertical dimension:
1. **Unbounded Preview Line Width**:
   Once spillage triggers, `extract_spill_preview` in
   `src/toas/tools_cluster/spill_ops.py` selects up to `preview_lines` (default 30)
   using strategies like `head_tail` or `error_focus`. It applies **no width
   boundary whatsoever** to the selected lines. If output contains minified JS,
   single-line JSON arrays, or huge log records that are 5,000 to 50,000 characters
   wide, 30 lines can inject 150,000+ characters straight into the session context.
2. **Byte Threshold Is a Trigger, Not a Cap**:
   `threshold_bytes` triggers the decision to spill, but does not cap the preview
   itself. A 5-line output totaling 80 KB spills to disk, but because 5 lines
   is less than `preview_lines` (30), all 5 giant lines (80 KB) are rendered
   directly into the preview block. The byte threshold therefore fails to protect
   against horizontal context blowouts.
3. **Chaos from Repetitive Long Lines**:
   Even moderate outputs with 20–30 long lines of database dumps, CSV records, or
   trace lines degrade model attention and exhaust token budgets rapidly without
   providing commensurate value.

## In Scope

- **Line Width Clamping & Elision**:
  - Introduce a configurable `max_line_width` (default e.g. 300–500 characters)
    for in-transcript rendered blocks and spill previews.
  - When a line exceeds `max_line_width`, truncate with an explicit, compact
    indicator (e.g. `<prefix>... [N chars truncated]` or middle elision
    `<head>... [N chars omitted]...<tail>`).
- **Preview Byte Safety Backstop**:
  - Enforce an aggregate character/byte cap on the rendered preview block itself
    (e.g. `max_preview_bytes`), guaranteeing that regardless of line count or
    strategy, a spill preview cannot exceed a fixed budget.
- **Configuration & Profiles**:
  - Add `max_line_width` (and `max_preview_bytes`) to `SpillPolicy` and
    `SpillProfile` in `src/toas/config.py`.
  - Expose `spill.max_line_width` and related keys to `toas.toml` and
    `/config set spill.max_line_width <int>`.
  - Update default profiles (`test`, `raw`, `wide`) with appropriate width
    defaults.
- **Durable Full-Fidelity Invariant**:
  - The spilled scratch file written to `.toas/scratch/<block_id>.txt` must
    always preserve 100% of the raw, unclipped bytes and lines. Width truncation
    is strictly a projection-layer concern.

## Out of Scope

- Wrapping lines with synthetic newlines (which alters line numbering and breaks
  range alignments).
- Truncating user-authored transcript input.
