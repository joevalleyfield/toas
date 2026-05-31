# 570: Retire Stateful Branch Selection And Make Step Transcript-Authoritative

## Why

`step` behavior should be simple and invariant: execution is frontier-anchored, and history selection is explicit. Hidden durable branch-selection state (`head`/`jump`/anchor-adjacent flows) introduces alternate execution truth that can diverge from the visible transcript frontier.

## Policy Contract (Docs-First)

1. Frontier authority:
- every `step` invocation resolves from transcript tail/frontier only
- no durable hidden selector (`head`/`jump`/anchor-adjacent state) may redirect execution target away from transcript frontier

2. Replay authority:
- only `/replay` may select callable content from non-frontier history
- `/replay` selection may target any branch/history lineage
- replayed/copied content always lands as new child content directly under current frontier

3. Frontier intent authority:
- only current frontier content (user/assistant/control) may select what executes next
- frontier control intent (for example `/replay ...`) is valid and authoritative for that step
- non-frontier durable control records may annotate provenance, but must not act as ambient execution selectors

4. Parentage authority:
- replay/step parentage is always frontier-child append in message-event space

5. Operator-minimalism:
- transcript operators stay minimal; do not broaden command surface unless needed for replacement parity
- remove legacy node-selection semantics instead of layering additional selection state

## Goal

Make `step` transcript-authoritative for all invocations:
- execution selection always comes from transcript frontier
- `/replay` can select callable content from any history branch (including direct lineage)
- replayed/copied content from history always lands directly under current frontier
- no hidden persistent head pointer influences `step` execution truth
- retire and remove head/jump/anchor-adjacent flows as node-selection mechanisms, replacing their semantics with transcript operators

## Recon Inventory (Current Surface)

### A) Runtime/selection touchpoints
- `src/toas/runtime/step_runtime.py`
  - frontier selection and invariant enforcement
  - divergence/bind parent wiring (`bind_parent`, `divergence_parent`) and debug payload fields
- `src/toas/cli_session_commands.py`
  - `run_step_local` selected-head/bind parent assembly and frontier debug context
- `src/toas/step.py`
  - help/usage projection currently advertising head/jump controls

### B) Durable control-state plumbing
- `src/toas/graph_control_state_edges.py`
- `src/toas/graph_record_writers.py`
- `src/toas/graph.py`
  - control record rendering/lookup (`jump`, `head`, `anchor`)

### C) CLI and operator surfaces encoding legacy selection semantics
- `src/toas/cli_dispatch.py`
- `src/toas/cli_dispatch_ops.py`
- `src/toas/cli.py`
- `src/toas/operator_api.py`
- `src/toas/daemon/local_ops.py`
- projection-target surfaces (`toas transcript [head_id]`, `toas llm-input [head_id]`, `toas rebuild [head_id]`)

### D) Replay/operator command semantics
- `src/toas/runtime/operator_command_extract_replay.py`
- `src/toas/runtime/replay_queue_edges.py`
- `src/toas/runtime/session_step_edges.py`

### E) Docs/prompt surfaces that currently describe legacy stateful selection
- `README.md` (head/jump CLI docs, lineage-selected framing)
- `docs/vision.md` (control records include head/jump/anchor in active model)
- `src/toas/prompts/dynamic/capabilities/overview_v1.txt`
- `docs/roadmap.md` (task framing references)

## Replacement Mapping (Direction)

- Legacy `toas head <id>` selection semantics:
  - remove entirely as execution selector
  - do not retain hidden-state selector semantics under compatibility guards

- `toas jump <index>` hidden bind-selection semantics:
  - remove entirely as step-routing selector
  - replace with transcript edits/operators that make intended frontier explicit in transcript itself

- Anchor-adjacent parentage steering:
  - demote to provenance/diagnostic annotation only (if retained)
  - forbid from modifying step execution target

- Historical callable rerun:
  - route exclusively through `/replay`, with append-under-frontier semantics

## Scope

1. Define policy/contract (docs first):
- codify frontier-authoritative `step` semantics and explicit `/replay` historical selection semantics
- codify removal of head/jump/anchor-adjacent node-selection behavior (no deprecation lane, no guard-backed compatibility mode)
- prefer a minimal transcript-operator set; do not expand operator surface unless required for replacement parity

2. Implementation reconnaissance:
- inventory all code paths where head/jump/anchor influence node selection, execution parentage, or step routing
- map tests/docs that encode legacy semantics
- produce replacement mapping from legacy semantics to transcript-operator equivalents

3. Projection-target compatibility:
- rendering/projection up to a specific node remains supported (explicit target argument)
- targeted projection must be read/render-only; there is no hidden selection state to mutate
- running targeted projection must not redirect subsequent `step` execution away from transcript frontier

4. Implementation slicing decision:
- split into focused subtasks if reconnaissance reveals broad surface area
- otherwise land as a single contained implementation

## Slicing Recommendation (Post-Recon)

Surface area is broad enough to justify focused slices:
1. Contract/docs slice (authoritative semantics + CLI/help text updates)
2. Runtime selection slice (`step_runtime` + `run_step_local` parentage cleanup)
3. CLI/operator deprecation/removal slice (`head`/`jump`/anchor-adjacent command semantics)
4. Replay semantics hardening slice (explicit append-under-frontier assertions)
5. Test migration slice (unit + acceptance updates from selected-head assumptions to frontier-authoritative assertions)

If slice boundaries prove too heavy in-flight, collapse (2)-(4) into one implementation change while keeping (1) and (5) explicit.

## Non-Goals

- changing durable event-history model
- removing explicit replay functionality
- redesigning transcript format
- broadening transcript-operator surface beyond minimal replacement need

## Initial Validation

- repeated truncate/restore + step loops remain frontier-driven
- `/replay` from any branch lands replayed content under current frontier
- no hidden head/jump state can redirect step execution away from transcript frontier

## Completion Notes

Implemented and validated:

1. Frontier authority and parentage:
- `step` execution no longer consumes hidden `head`/`jump` selector state
- frontier/LCP-driven reconciliation remains the sole execution-routing mechanism
- replay/step append semantics remain frontier-child in message-event space

2. Replay authority:
- non-frontier callable selection authority is restricted to explicit `/replay`
- replayed/copied historical callable content lands under current frontier

3. Legacy selector removal:
- removed CLI and daemon mutation surfaces for `jump`/`head`
- retained `heads` as read-only inspection surface
- removed selector mutation APIs and record writers (`jump_to_index`, `select_head`, `write_jump_record`, `write_head_record`)
- removed selector accessor APIs (`active_head_id`, `active_bind_index`) and rewired callsites

4. Docs parity:
- removed active `jump/head` command claims from user-facing docs
- aligned contract text on frontier-authoritative step semantics and read-only projection targeting

5. Test migration:
- migrated selector-era tests/fixtures away from `jump/head` execution semantics
- replaced remaining fixture residue with active non-message record shapes (`anchor`, etc.)

Validation evidence:
- `UV_CACHE_DIR=/private/tmp/uv-cache uv run pytest tests/test_step.py tests/test_runtime_step_runtime.py tests/test_runtime_operator_command_handlers.py tests/test_cli.py tests/test_daemon.py tests/test_graph.py tests/test_graph_control_state_edges.py tests/test_graph_index_edges.py -q --no-cov`
- Result: `674 passed, 1 xfailed`

Task outcome:
- Done. Contract now matches implementation: no hidden selector state can redirect `step`; execution truth is transcript frontier plus explicit `/replay`.

Post-close follow-on note:
- 2026-05-30: Added `docs/execution-model.md` as a compact execution-authority reference to keep transcript-operational vs graph-observational primacy explicit during future large refactors.
