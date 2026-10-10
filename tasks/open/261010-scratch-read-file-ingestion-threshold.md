# Scratch Read File Ingestion Threshold

Filed as: 261010-scratch-read-file-ingestion-threshold
FKA:
AKA: scratch read file spill threshold; avoid recursive scratch spilling; read_file scratch ingestion
Legacy index:

keywords: tools, read_file, rendering, scratch, spill, inception

Parent: `260926-state-step-requirements`
Related: `261009-read-file-eof-truncation-and-soft-bounds`

Status: OPEN; apply 500-line ingestion threshold when read_file targets scratch files without explicit bounds

## Context and Motivation

In state-step dogfood sessions, tools whose output exceeds thresholds spill to `.toas/scratch/<block_id>.txt` with a preview. Instructions advise the model to read the complete file via `read_file` when ingesting spilled outputs.

However, when `read_file` is invoked without explicit `start_line`/`end_line` bounds, the renderer treats the read as unbounded and applies the default 40-line threshold. If the scratch file contains between 41 and 500 lines (e.g. a 47-line directory listing), reading the scratch file spills a second time into another scratch file, trapping the model in a recursive re-spilling loop.

## Intent

When `read_file` targets a scratch file (`.toas/scratch/...`) without explicit line bounds, apply the 500-line bounded ingestion threshold rather than the default 40-line general limit so reading spilled outputs does not trigger recursive re-spills.
