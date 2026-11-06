Filed as: 261106-apply-patch-atomicity-and-healing
FKA:
AKA: apply_patch atomic execution; apply_patch indentation healing; partial patch restaging; patch diagnostics
Legacy index:

keywords: tooling, apply_patch, atomicity, diagnostics, indentation-healing, recovery

Parent: `260418-weak-model-safe-apply-patch-contract`
Related: `261105-apply-patch-indent-leniency-and-diff-diagnostics`

# apply_patch Atomicity, Indentation Healing, and Transparent Diagnostics

## Intent

Harden `apply_patch` against YAML-induced formatting errors by adding automatic
indentation healing for malformed hunks, and introduce controllable atomicity
(pre-validation of all hunks before writing) with transparent diagnostics and
safe recovery staging for unapplied chunks.

## Context & Motivation

When models generate `apply_patch` operations inside YAML literal scalar blocks
(`patch: |` or `patch: |2`), formatting discrepancies frequently occur:
1. **Outer / Delimiter Indentation**: Indentation on patch markers (`*** Begin Patch`,
   `*** Update File:`, `@@`) causes immediate parser rejection or causes `@@`
   to be misidentified as a context line.
2. **Hunk Marker Column Offsets**: Indented diff markers (`  -`, `  +`, `   `)
   shift the prefix character away from column 0, causing the parser to treat
   add/remove lines as context lines starting with spaces.
3. **Non-Uniform Context Indentation**: When stripped lines match a single
   unique site in the target file, differing indentation ratios (e.g. 2-space
   model indentation vs. 4-space file indentation) cause strict line-by-line
   delta matching to fail even when the context is semantically unambiguous.

Furthermore, `run_apply_patch` currently mutates files on disk sequentially as
it iterates through hunks. When hunk $k$ of an $N$-hunk patch fails:
- Hunks $1 \dots k-1$ remain written to disk.
- The tool raises an exception, causing the plan recovery mechanism
  (`_append_plan_recovery_consequence`) to stage the **entire** original patch
  for retry.
- When retried, hunk 1 fails because it was already applied, creating a
  confusing failure loop.

## In Scope

- **Automatic Hunk Indentation Healing**:
  - Tolerate leading whitespace on patch delimiters and hunk headers (`*** ...`, `@@`).
  - Normalize chunk lines when diff markers (` `, `+`, `-`) are uniformly indented.
  - Reconcile hunk indentation against target file lines when stripped chunk lines
    match a single unique window in the target file.
- **Controllable Atomicity**:
  - Support `atomic: bool = True` (default `True` in `arguments`, configurable via
    `config.tool_writes.patch_atomic`).
  - In atomic mode: pre-validate and compute all file modifications in memory
    across all hunks before touching disk. If any hunk fails, write 0 files to disk.
  - In non-atomic mode: allow valid hunks to apply while accurately recording
    applied, failed, and skipped hunks.
- **Transparent Diagnostics**:
  - Distinctly report which hunks/chunks succeeded, which hunk failed (with context
    diff), which were skipped, and which files were written.
- **Safe Recovery Pruning**:
  - In non-atomic execution, if partial application occurs before failure, prune
    already-applied hunks from the staged recovery turn so only unapplied (failed
    and skipped) hunks are retried.

## Out of Scope

- Heuristic fuzzy line matching beyond indentation normalization.
- Replacing the patch envelope format with an alternative diff protocol.

## Acceptance Criteria

1. Patch parsing tolerates leading whitespace on boundary headers (`*** Begin Patch`,
   `*** Update File:`, `@@`, etc.) and detects diff markers (`+`, `-`, ` `) indented
   by YAML block indentation.
2. When stripped lines of an update chunk uniquely match a single window in the
   target file, the hunk's indentation is automatically reconciled.
3. In atomic mode (`atomic: true`, default), failure in any hunk prevents all
   file mutations on disk, reporting clean failure diagnostics.
4. In non-atomic mode (`atomic: false`), applied hunks are recorded, skipped hunks
   are explicitly marked, and any staged recovery plan omits already-applied hunks.
5. All new behavior is tested with 100.00% statement coverage under `./scripts/check.sh`.
