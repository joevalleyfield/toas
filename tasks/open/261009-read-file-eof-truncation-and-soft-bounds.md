# Read-File Clean EOF Truncation and Soft Line Bounds

Filed as: 261009-read-file-eof-truncation-and-soft-bounds
FKA:
AKA: read_file end_line beyond file length; read_file clamp to EOF; read_file soft bounds; read_file empty slice
Legacy index:

keywords: tools, read_file, ergonomics, contract, usability

Parent: `260926-state-step-requirements`
Related: `261008-state-spill-ingestion-and-artifact-references`

Status: OPEN; implement read_file clean EOF truncation and soft line bounds

## Context

In state-step session runs (observed concretely in `session-20261007-1946-state-seed.md`, Turn 6), the model attempted to read a spilled file listing with:
```yaml
pending_tools:
- tool_name: read_file
  args:
    path: .toas/scratch/ib_479396b18eb5ca83.txt
    start_line: 1
    end_line: 50
```
Because the scratch file had 47 lines, `read_file` failed with:
`[FAILED] tool 0 (read_file): end_line 50 is beyond file length 47`

This forced the model to waste an entire subsequent turn re-issuing `read_file` with `end_line: 47`.

In `src/toas/tools_cluster/basic_ops.py` (lines 208-210), `read_file` already clamps to EOF when `max_lines` is specified (`effective_end = min(effective_end, len(lines))`), but explicitly raises a `RuntimeError` when `end_line > len(lines)` without `max_lines`. Furthermore, when `start_line > len(lines)` (or when reading from an empty file), `read_file` raises an error instead of failing soft.

For a read operation, reading past EOF is a standard occurrence (analogous to Python slicing `lines[0:50]`, `head -n 50`, or `sed -n '1,50p'`). Raising hard errors on bounds overshoots creates unnecessary model friction and turn churn.

## Objectives

1. **Clean EOF Truncation**:
   - When `end_line > len(lines)` and `effective_start <= len(lines)`:
     Truncate cleanly to EOF (`effective_end = len(lines)`).
     Return lines up to EOF without error.
     Report the actual bounds read in `summary` (`f"{path}:{effective_start}-{len(lines)}"`).
2. **Soft Bounds on Out-of-Range Start / Empty Files**:
   - When `effective_start > len(lines)` (or on an empty file):
     Do not raise `RuntimeError`. Return `ok: True`, `content: ""`, `display_content: ""`, and report the actual bounds and line count in `summary`, e.g. `f"{path}:{effective_start}-{effective_end} (0 lines; file has {len(lines)} lines)"`.
3. **Preserve Hard Errors for True Contract Violations**:
   - Continue raising `RuntimeError` for invalid arguments: `start_line < 1`, `end_line < start_line`, non-integer line arguments, non-existent files, and directory paths.
4. **Validation and Coverage**:
   - Update tests in `tests/test_tools_basic_ops.py` and `tests/test_tools_registry.py`.
   - Maintain 100.00% statement coverage across all modified modules.
