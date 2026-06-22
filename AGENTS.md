# TOAS Agent Notes

## jj Workflow

- `jj commit` = `jj describe && jj new` — the working copy `@` is empty by default.
- Never do `jj abandon @` — that's wrong. If you want to go back, do `jj edit @-`.
- To verify the last commit: `jj diff --git -r @-`.
- To see the commit itself: `jj show --git @-`.

## Purpose

TOAS is a transcript-oriented operator over append-only durable history.

One practical motivation for the project is to make a locally available but obnoxious model workable by surrounding it with better transcript control, durable history, projection, and repair semantics.

The important split is:
- `session.md` is the user-controlled working transcript
- `events.jsonl` is canonical durable state
- `toas step` accepts transcript state, synchronizes it into history, and resolves one layer of consequence

The system is not a hidden loop.

## Current Model

### Message events

Message events are graph-native history entries with:
- `id`
- `parent`
- `role`
- `content`
- `metadata`

They live in message-event space only.

### Control records

Non-message operator state includes:
- `jump`
- `head`
- `anchor`

### Tool records

Callable message events can produce:
- `tool_request`
- `tool_result`

`RESULT` blocks are projected output, not durable message events.

Explicit user shell shorthand at the frontier, written as a final `$ ...` line, is executed through a separate user-intent path. It still records `tool_request` / `tool_result` facts using the `shell` shape, but it is not subject to the bounded policy of the model-addressable registry `shell` tool.

### Model-call records

Generation can produce:
- `llm_call` records with projected request messages
- success payloads with response content
- failure payloads with explicit error text

## Current CLI Surface

- `toas step`
- `toas daemon [start|stop|status]`
- `toas jump <bind_index>`
- `toas head <head_id>`
- `toas heads`
- `toas transcript [head_id]`
- `toas llm-input [head_id]`
- `toas prompt <kind>/<version>`
- `toas prompts [prefix]`
- `toas history [limit]`
- `toas rebuild [head_id]`

## Runtime Mode Semantics

- `TOAS_RPC_MODE=off`: CLI-pure local execution; no daemon RPC path.
- `TOAS_RPC_MODE=auto` (default): prefer daemon RPC when endpoint is present; fallback to local on RPC errors.
- `TOAS_RPC_MODE=on`: force RPC attempt first for routed commands; fallback remains explicit on RPC failure paths.

Keep the mode boundary explicit in code paths and tests:
- local behavior must remain available and parity-safe
- RPC behavior must preserve stdout/history contracts
- Vim persistent channel should be treated as a transport optimization, not a semantic fork

## Key Invariants

- Never mutate prior history entries.
- Never treat non-message records as part of message-event numbering.
- Editing prior transcript-aligned content means branching, not undo.
- Continuation from a non-tip lineage must use explicit parentage.
- Adjacent user message events are concatenated only at model-input projection time.
- Keep message events, control records, tool records, and model-call records distinct.
- Keep direct user intent distinct from model-addressable capability, even when they share result shapes.

## Task Naming

New task files: `tasks/open/YYMMDD-short-intent.md` — see `tasks/README.md` for the convention and continuity fields (`Filed as:`, `FKA:`, `AKA:`, `Legacy index:`).

## Important Files

- [README.md](README.md)
- [docs/vision.md](docs/vision.md)
- [docs/roadmap.md](docs/roadmap.md)
- [docs/runtime-ownership.md](docs/runtime-ownership.md)
- [docs/runtime-direction.md](docs/runtime-direction.md)
- [src/toas/operator_api.py](src/toas/operator_api.py)
- [src/toas/runtime](src/toas/runtime)
- [src/toas/tools_cluster](src/toas/tools_cluster)
- [src/toas/daemon](src/toas/daemon)
- [src/toas/cli.py](src/toas/cli.py)
- [src/toas/graph.py](src/toas/graph.py)
- [src/toas/llm.py](src/toas/llm.py)
- [src/toas/prompts.py](src/toas/prompts.py)
- [src/toas/step.py](src/toas/step.py)
- [src/toas/tools.py](src/toas/tools.py)
- [src/toas/transcript.py](src/toas/transcript.py)
- [tests](tests)


## Implementation Bias

When extending the system:
- prefer new durable records over sidecar state
- keep the CLI thin
- keep storage concerns in `graph.py`
- keep runtime/operator semantics in `src/toas/runtime/`
- treat `step.py` as a legacy/session-help facade unless the change is explicitly
  compatibility-surface work
- keep model transport in `llm.py`
- keep tool semantics in `src/toas/tools_cluster/`
- treat `tools.py` as the public registry facade, not the default home for new
  tool behavior
- keep daemon/RPC code as transport adapter work rather than semantic ownership
- keep prompts as explicit library material, whether file-backed or dynamically rendered from live runtime state, and never as hidden runtime policy
- use [docs/runtime-ownership.md](docs/runtime-ownership.md) as the routing guide
  when choosing where new code belongs

## Suggested Change Workflow

When the seam is not yet obvious, prefer a short spike first to locate the
real ownership boundary, invariant, or failure mode. Once the seam is clear,
prefer a red/green/refactor cadence:

- write or tighten a targeted failing test
- make the smallest production change that gets back to green
- refactor production code and tests while staying green

This is guidance, not a rigid rule. In practice, "spike, then TDD" is often a
better fit for TOAS than either pure upfront TDD or broad implement-then-test
work, especially when lightweight-model mistakes or exploratory attempts help
surface the actual seam.

## Task/Commit Discipline

- Any repo-modifying work must have an associated task in `tasks/open` (or an explicit task created as part of the same change).
- Any commit that materially achieves ends called for by a task must update that task file in the same commit to stitch task status/progress to the code or docs change.
- `docs/roadmap.md` does not need updates on every commit, but it should be touched whenever a task is opened, closed, or explicitly brought into focus so active planning context stays coherent.

## Verification

Run the suite:

```bash
uv run pytest
```

For focused coverage on a refactor slice, use the targeted helper so a narrow
test run measures only the named coverage sources instead of inheriting the
repo-wide pytest coverage addopts:

```bash
uv run python scripts/targeted_coverage.py \
  --cov toas.runtime.local_request_handler_edges \
  --fail-under 100 \
  --max-missing-files 0 \
  -- tests/test_runtime_local_request_handler_edges.py -q
```
