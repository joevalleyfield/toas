Filed as: 261102-windows-crlf-spilled-scratch-blocks
FKA:
AKA: windows crlf scratch files; spilled inert block line endings; double cr lf; blank lines in scratch blocks
Legacy index:

keywords: runtime, windows, crlf, rendering, streaming, scratch, blocks, line-endings

Parent: `261015-windows-compatibility-restoration`
Related: `260515-apply-patch-windows-crlf-hardening`; `260621-windows-shell-launcher-and-path-resolution`

# Normalize Spilled Inert Block Line Endings Across Windows And Posix

Prevent Windows `\r\n` output from double-translating into `\r\r\n` inside
`.toas/scratch/ib_*.txt` files and eliminate downstream phantom blank lines in
`read_file`, state-step block slices, and shell utilities like `tail`.

## Current Reality

When tools with large outputs (such as `pytest`) run on Windows:

1. **Streaming Subprocess Output Lacks Universal Newlines**:
   In `src/toas/tools_cluster/shell_streaming.py`, `run_streaming_subprocess`
   reads raw bytes from `proc.stdout`. On Windows, console programs output
   lines ending in `\r\n`. `_completed_process` decodes raw bytes directly
   (`stdout = b"".join(chunks).decode(...)`) without applying universal newlines
   conversion, leaving raw `\r\n` in `result["stdout"]` (unlike non-streaming
   `subprocess.run(text=True)`).

2. **`Path.write_text` Double-Translates Newlines On Windows**:
   In `src/toas/tools_cluster/rendering.py` (`spill_inert_block` and
   `render_fenced_output`), scratch files are saved via
   `Path.write_text(content, encoding="utf-8")`.
   On Windows, `write_text` defaults to `newline=None`, causing Python's text
   layer to replace every `\n` with `os.linesep` (`\r\n`).
   Because `content` already had `\r\n`, the `\n` becomes `\r\n`, producing
   `\r\r\n` on disk.

3. **Downstream Blank Lines**:
   When downstream readers ingest `.toas/scratch/ib_*.txt`:
   - Universal newlines (`read_text()`) converts `\r\n` to `\n`, leaving the
     leading `\r`. The string in memory has `\r\n`.
   - Python's `splitlines()` treats both `\r` and `\n` as line boundaries:
     `'line 1\r\r\nline 2\r\r\n'.splitlines() -> ['line 1', '', 'line 2', '']`.
   - Every single line is followed by a phantom blank line.
   - Slicing or reading with `$ tail -n 30` or `read_file` yields blocks of
     empty lines, double line numbering, and doubled line counts that trigger
     false threshold spills.

## Scope

- **Subprocess Stream Parity**: In `src/toas/tools_cluster/shell_streaming.py`,
  normalize `stdout` in `_completed_process` with `replace("\r\n", "\n")` so
  completed streaming results match non-streaming `subprocess.run(text=True)`.
- **Inert Block Content Normalization**: In `src/toas/tools_cluster/rendering.py`
  (`render_fenced_output`, `spill_inert_block`, `render_import_block`),
  normalize `content = content.replace("\r\n", "\n").replace("\r", "\n")`
  before hashing for `block_id`, before line counting, and before formatting.
- **Explicit `newline="\n"` on Scratch Writes**: In `rendering.py`, write
  scratch files with `write_text(content, encoding="utf-8", newline="\n")`
  so Python on Windows never performs line ending translation on internal
  scratch caches.
- **Defensive Ingestion**:
  - In `src/toas/tools_cluster/basic_ops.py` (`run_read_file`), normalize any
    stray `\r` before calling `splitlines(keepends=True)`.
  - In `src/toas/runtime/state_step.py`, normalize scratch file content upon read.
- **Cross-Platform Verification**: Add tests verifying that CRLF and `\r\r\n`
  inputs produce clean LF scratch files, correct line counts, and no blank lines
  under `splitlines()` or `read_file`.

## Non-Goals

- Reworking workspace file newline policy: `tool_writes.newline_style` (`auto`,
  `lf`, `crlf`) for user-authored workspace code files remains unchanged.
- Changing live streaming terminal chunk encoding: raw byte delivery to
  streaming subscribers is preserved.

## Acceptance Criteria

- Spilled inert blocks created from CRLF or mixed output contain only `\n`
  line endings on disk across both Windows and POSIX.
- `block_id` generation produces identical SHA-256 hashes for equivalent
  content regardless of whether input used LF or CRLF.
- `read_file` and state reference slicing on spilled scratch files do not
  produce phantom blank lines or doubled line numbering.
- `$ tail -n <N>` on spilled scratch files returns the actual last `<N>` lines
  of content rather than empty blank lines.
- Completed process stdout from `run_streaming_subprocess` has universal
  newlines applied, matching non-streaming execution.
- Targeted tests and full `./scripts/check.sh` pass with 100.00% statement
  coverage.

## Likely Ownership

- `src/toas/tools_cluster/shell_streaming.py`: completed process stdout normalization.
- `src/toas/tools_cluster/rendering.py`: inert block content normalization and scratch writes with `newline="\n"`.
- `src/toas/tools_cluster/basic_ops.py`: defensive reading in `run_read_file`.
- `src/toas/runtime/state_step.py`: defensive reading in state block references.
- `tests/test_tools_rendering.py`, `tests/test_shell_streaming.py`, `tests/test_tools_basic_ops.py`.

## Progress

- 2026-11-02: Task opened after identifying the `b"".join().decode()` streaming
  capture + Windows `Path.write_text(newline=None)` double-translation root
  cause that produces `\r\r\n` in scratch files and empty lines under `splitlines()`
  and `tail`.
