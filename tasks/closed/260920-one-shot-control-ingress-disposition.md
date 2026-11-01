Filed as: 260920-one-shot-control-ingress-disposition
FKA:
AKA: --control disposition; injected control; ephemeral control ingress
Legacy index:

keywords: design, active, transcript, control, policy, lineage, cli, compatibility

Parent: `260920-branch-projected-policy-program`
Related: `260920-lcp-direct-policy-deltas`; `260920-lcp-policy-reevaluation-contract`; `260920-transcript-control-state-contract`

# Decide the Fate of One-Shot Control Ingress

Determine whether `toas step --control` remains a useful operator-facing
convenience, becomes transcript-materializing, is restricted to transient
queries, or is retired so no non-functional transcript-control vestige remains.

## Current Reality

`toas step --control <slash-command>` and
`operator_api.step_once(control=...)` append a `TOAS:CONTROL` turn only to the
in-memory input for one step. The command is materialized as a durable control
message, but its text is not written to `session.md`. This is an external
CLI/API surface, not merely an acceptance-test harness helper.

Consequently, a subsequent transcript/LCP reconstruction cannot see the
control source. Existing endpoint/config workflows relied on its
history-forward durable side effects; the Phase-1 policy slice preserves that
compatibility behavior for this ingress.

## Desired Reality

Every lasting policy-changing control has an intelligible source and replay
story. A branch-forward transcript policy reducer must not rely on a control
that is absent from the reconstructed transcript. If a one-shot ingress stays,
its semantics and utility must be explicit rather than an accidental exception.

## Questions and candidate dispositions

1. Materialize the supplied control into the selected working transcript before
   stepping. It then behaves like ordinary authored `TOAS:CONTROL` content and
   receives normal LCP/branch semantics.
2. Retain it only for explicitly transient read-only/query operations. It
   cannot write policy-changing durable state.
3. Retire `--control` and direct callers to edit the transcript or use a
   purpose-built query command.
4. Establish a distinct, durable non-transcript command lane only if it has a
   demonstrated operator need and its history/policy semantics can be made
   truthful. This is not a default direction.

## Risks

- Keeping current behavior leaves policy-changing history with a source that
  cannot be replayed from the user-controlled transcript.
- Automatically writing every one-shot command into `session.md` may surprise
  callers who expected an inspection action without transcript mutation.
- Removing the surface without surveying callers could break editor, daemon,
  or automation workflows.

## Selected Disposition: Ephemeral Queries & Materialized Policy Mutations

Adopt a dual-disposition model based on command semantics:
1. **Transient Queries are Ephemeral**:
   Commands that produce only inspection/projection nodes (`/help`, `/config show`, `/session show`, `/models`, etc.) leave both `session.md` and `events.jsonl` untouched. Output is emitted to stdout/callbacks without recording a durable message event or altering the transcript. LCP is unaffected.
2. **Policy Mutations are Injected (Materialized)**:
   Commands that produce durable state records (`/config set`, `/config endpoint ...`, `/model select`, `/shell add`, `/cd`, `/workspace`, `/run`) materialize `## TOAS:CONTROL\n\n{command}\n` into `session.md` before/at persistence time.
   `events.jsonl` records the corresponding message node and policy record. `session.md` and `events.jsonl` stay in 1:1 lockstep.
3. **Elimination of History Hack**:
   Remove the `not injected_control` check in `src/toas/runtime/step_runtime.py` and delete the `injected_control` plumbing across `step()`, `run_step()`, and kwargs wrappers.

## Acceptance Criteria

- Transient query commands executed via `--control` (or `operator_api.step_once(control=...)`) emit output without appending to `session.md` and without appending message nodes to `events.jsonl`.
- State-mutating commands executed via `--control` append the `TOAS:CONTROL` turn to `session.md` and write corresponding events to `events.jsonl`.
- Subsequent steps on the branch naturally reduce policy from direct declarations in `session.md` without false rewrite detection.
- `injected_control` parameter is removed from `step()`, `run_step()`, and `step_runtime.py`.
- Targeted and full test suites pass at 100.00% statement coverage.

## Progress

- Completed caller inventory across CLI, daemon, Vim, and test suites.
- Confirmed dual-disposition design: ephemeral transient queries, materialized policy mutations.
- Implemented `has_durable_mutation` and dual persistence in `src/toas/runtime/step_result_runtime.py` and `src/toas/cli_session_commands.py`.
- Removed `injected_control` parameter and runtime hack from `src/toas/runtime/step_runtime.py`, `src/toas/step.py`, and `src/toas/cli_session_commands.py`.
- Verified targeted unit tests in `test_runtime_step_result_runtime.py`, `test_cli_session_commands.py`, and `test_cli.py`.
- Verified full test suite and 100.00% statement coverage via `./scripts/check.sh`.
- Performed end-to-end artifact and behavior inspection for ephemeral queries and mutating controls.

## Completion Evidence

- Direct end-to-end execution of `toas step --control "/help cli"` verifies output projection with zero writes to `session.md` or `events.jsonl`.
- Direct end-to-end execution of `toas step --control "/shell add rg"` verifies materialization to `session.md`, durable `control` message event, and `policy_override` event in `events.jsonl`.
- Direct subsequent `toas step` execution verifies that no false branch rewrite occurs and policy state persists cleanly.
- Full `./scripts/check.sh` passes at 100.00% statement coverage across all 155 source files (3,658 unit tests + 17 acceptance tests, ruff clean, mypy clean).

Status: Closed.
