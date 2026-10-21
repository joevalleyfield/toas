# Scratch Read File Ingestion Threshold

Filed as: 261010-scratch-read-file-ingestion-threshold
FKA:
AKA: scratch read file spill threshold; avoid recursive scratch spilling; read_file scratch ingestion
Legacy index:

keywords: tools, read_file, rendering, scratch, spill, historical

Parent: `260926-state-step-requirements`
Related: `261009-read-file-eof-truncation-and-soft-bounds`

Status: CLOSED — 2026-10-20

## Context and Motivation

In state-step dogfood sessions, tools whose output exceeds thresholds spill to `.toas/scratch/<block_id>.txt` with a preview. Instructions advise the model to read the complete file via `read_file` when ingesting spilled outputs.

However, when `read_file` is invoked without explicit `start_line`/`end_line` bounds, the renderer treats the read as unbounded and applies the default 40-line threshold. If the scratch file contains between 41 and 500 lines (e.g. a 47-line directory listing), reading the scratch file spills a second time into another scratch file, trapping the model in a recursive re-spilling loop.

## Intent

When `read_file` targets a scratch file (`.toas/scratch/...`) without explicit line bounds, apply the 500-line bounded ingestion threshold rather than the default 40-line general limit so reading spilled outputs does not trigger recursive re-spills.

## Completion — 2026-10-20

The existing bounded-read logic did not cover unbounded scratch reads. Added
resolved-path containment against the active scratch directory (including
custom scratch directories), applying the existing 500-line/50 KB ingestion
limits without changing ordinary read thresholds. Sibling directories do not
receive the exception. Oversized scratch content still spills.

Regression tests first reproduced spills at 41 and 500 lines. Tests now cover
41/500/501 lines, ordinary and similarly named sibling paths, absolute custom
scratch paths, and either side of the byte limit. Inspected actual rendering
from a 47-line scratch file: all lines appear in one importable block with no
spill preview or repeated ingestion instructions.

Verification: `.codex-local/bin/uvt run bash scripts/check.sh` — 3,595 passed,
nine skipped, 17 deselected; 100.00% statement coverage. All 17 acceptance
scenarios, Ruff and mypy passed on macOS.
