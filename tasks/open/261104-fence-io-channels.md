Filed as: 261104-fence-io-channels
FKA:
AKA: fence io channels; fence stdin stdout stderr; stream redirection fences; fence artifact capture; fence piping; state artifact fence io
Legacy index:

keywords: runtime, fences, execution, io, piping, streams, artifacts, state, scratch, capture

Parent: `260803-language-exec-fenced-block-lane`
Related: `260831-language-write-materialization-fences`; `261010-direct-tool-artifact-capture`; `260926-state-step-requirements`; `260831-transcript-source-reference-operations`

# Fence I/O Channels And Artifact Redirection

## Intent

Define standard input and output redirection channels on language-native fences.
Enable executable and materialization fences to accept input from prior blocks
or files (`stdin=...`) and capture stdout/stderr directly into scratch blocks
or state-mode artifacts (`out=...`, `err=...`) without requiring nested shells,
heredocs, or external wrapper scripts.

## Motivation

Language-native execution fences (`python exec`, `bash exec`) and write fences
(`python write path=... exec`) provide clean authoring semantics. However,
passing non-trivial input data into a script or capturing large output currently
pressures operators and models to either:
1. Nest shell scripts and heredocs inside the code block;
2. Manually author file reads and writes inside the script body; or
3. Dump large terminal output back into the transcript context, inflating tokens.

By declaring I/O channels directly on the fence info line, fences compose
cleanly with durable scratch blocks (`ib_...`) and state-mode artifacts
(`state.artifacts`).

## Illustrative Syntax

### 1. Direct Scratch-to-Script Stdin Piping

````markdown
```python exec stdin=ib_data123
import sys, json

data = json.load(sys.stdin)
print(f"Processed {len(data)} records")
```
````

Pipes the content of scratch block `ib_data123` (or file path) into `sys.stdin`.

### 2. Output Capture into State Artifacts

````markdown
```bash exec out=artifacts/build.log err=artifacts/build.err
cargo build --release
```
````

In state mode, redirects process stdout and stderr directly into state-tree
artifacts, keeping the working transcript compact while preserving the build
logs for inspection or subsequent tools.

### 3. Scratch Block Generation

````markdown
```python exec out=scratch
import json
print(json.dumps({"status": "ready", "items": [1, 2, 3]}))
```
````

Emits the output directly as an inert scratch block with a generated stable ID
(e.g., `ib_...`), ready for downstream fences to ingest via `stdin=ib_...`.

### 4. Composition with Write Materialization

````markdown
```python write path=scripts/transform.py exec stdin=data.csv out=data.json
import sys, csv, json

reader = csv.DictReader(sys.stdin)
json.dump(list(reader), sys.stdout)
```
````

Materializes `transform.py` to the workspace, executes it with `data.csv` on
stdin, and captures stdout into `data.json`.

## Core Requirements

1. **Fence Activation Attributes**:
   - `classify_fence_activation` recognizes allowed I/O attributes:
     - `stdin`: specifies source path, scratch block ID (`ib_...`), or reference.
     - `out`: specifies destination path, state artifact key, or `scratch` keyword.
     - `err`: specifies stderr destination path, state artifact key, or `scratch`.
     - `append_out` / `append_err`: boolean flags (default false / overwrite).

2. **Resolution and Feeding (`stdin`)**:
   - When `stdin` is a scratch block ID (`ib_...`), resolves against
     `.toas/scratch/<id>.txt` or transcript state.
   - When `stdin` is a workspace file path, reads content from disk.
   - Passes the resolved input to the underlying tool request (e.g. `input`
     argument in `python_script`, `shell_script`, `interpreter_script`).

3. **Capture and Redirection (`out` / `err`)**:
   - When `out` or `err` targets an artifact:
     - In state mode: records directly into the state tree artifacts dictionary.
     - In standard mode: writes to workspace path or creates `.toas/scratch/<id>.txt`.
   - Result projections report concise status lines with artifact/scratch
     identifiers rather than inlining large raw streams into context.

4. **Provenance & Determinism**:
   - Retain full source-fence provenance on derived requests.
   - Fail closed if a declared `stdin` source cannot be resolved or is missing.

## Non-Goals

- Implementing general multi-process piping topologies (`|`) in a single fence turn.
- Bidirectional interactive PTY streams.
- Replacing language runtime contracts.

## Acceptance Criteria

- `classify_fence_activation` parses and validates `stdin`, `out`, `err`,
  `append_out`, and `append_err` attributes.
- Tool runners (`shell_script`, `python_script`, `powershell_script`,
  `interpreter_script`) accept and wire `stdin` input.
- Execution results with `out` and `err` capture streams into targeted
  artifacts/scratch blocks and project compact outcome summaries.
- State-mode integration bridges fence output capture into `state.artifacts`.
- Test suite achieves 100.00% statement coverage across all modified and new files.
