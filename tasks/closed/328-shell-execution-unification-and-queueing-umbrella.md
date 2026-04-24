## Goal

Unify shell execution semantics across assistant proposals and user-staged execution, while introducing queue-aware continuation for mixed authorization outcomes.

## Why Now

Shell capability exists in multiple places today (assistant tool-calls, user tail execution, compact command-like forms), but behavior and authorization friction still vary by context and shape. This arc aligns capability, safety, and ergonomics.

## Scope

- establish one internal shell-operation normalization path
- align authorization semantics across all shell entry paths
- add queue/continuation behavior for mixed allow/deny sequences
- support compact and structured proposal forms without semantic drift
- keep user-context execution authoritative and unblockable

## Intended Behavior

- pipes and heredocs work consistently across all shell entry paths
- syntax differences (`operation: shell`, compact command forms, user staged blocks) do not imply different authorization logic
- multi-op sequences run in order with automatic pause/continue at blocked boundaries

## Intended Inputs

- `src/toas/graph.py`
- `src/toas/step.py`
- `src/toas/tools.py`
- `src/toas/transcript.py`
- `README.md` and docs where operator behavior is described

## Intended Outputs

- coherent shell execution and authorization model
- reduced manual extract/re-run loops for mixed-op sequences
- clearer durable traces for queue decisions and continuation

## Constraints

- keep user-context execution as final authority
- no silent policy forks by syntax shape
- preserve existing durable-record invariants

## Non-Goals

- no autonomous user-less execution loop in this arc
- no broad hidden auto-approval semantics

## Done When

- subtasks `329`-`333` are implemented and closed
- behavior parity is test-covered for single-line, multiline, pipe, and heredoc shell flows

## Architecture Notes (Red-Green-Refactor)

Current pain is mostly structure, not capability:
- shell extraction/normalization logic is duplicated across `step.py` and `graph.py`
- shell policy/evaluation is split between bounded tool execution and user-intent execution paths
- proposal syntax concerns (YAML forms, aliases, compact command shape) are mixed with execution concerns

Target separation of concerns:
- `graph.py`: transcript/event parsing and durable record helpers only
- `step.py`: frontier policy and orchestration only
- `tools.py`: execution runtime only
- new shared normalization seam (module-level): parse/normalize shell intent once, consume everywhere

Execution order (strict red-green-refactor):
1. **Red (characterize):** add parity tests for all current shell entry shapes and contexts (assistant/user, tool-plan/command shorthand, multiline/heredoc/pipe).
2. **Green (seam):** introduce a shared shell normalization helper without changing behavior.
3. **Green (adopt):** migrate assistant extraction and user shell extraction to shared helper.
4. **Green (policy split):** centralize context policy decision (`assistant` gated, `user` always allowed) in one step-level path.
5. **Refactor (cleanup):** delete duplicate extraction/parsing code from `step.py` and `graph.py`; keep compatibility aliases (`operation/tool_name`, `arguments/args`, `command/cmd`) behind one normalizer.
6. **Refactor (queue):** layer queue lifecycle on top of unified op model (pending/ran/blocked/skipped/canceled), without reintroducing shape-specific forks.

Design guardrails:
- no syntax-specific policy forks
- no hidden approvals
- durable records remain authoritative for replay/debug
- user-staged execution remains final authority

## Progress

- 2026-04-24: Umbrella completion checkpoint.
- Subtasks `329` and `330` previously landed (normalization + grant policy path alignment).
- Subtask `331` completed with durable replay queue controls (`resume`/`approve`/`skip`/`cancel`) and explicit continuation-flow coverage.
- Subtask `332` completed with compact executable shell projection defaults and explicit verbose extraction path.
- Subtask `333` completed with operation-schema alias normalization plus canonical callable schema documentation updates.

## Status

Closed 2026-04-24.
