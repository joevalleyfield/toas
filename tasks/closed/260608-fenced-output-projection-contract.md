# Fenced output projection contract

Filed as: 678-fenced-output-projection-contract
FKA:
AKA: fenced outputs; output blocks; inert wrapping
Legacy index: 678
keywords: projection, hardening, historical, correctness, fence, output, provenance, inert, transcript, contract

Investigate and define a broader transcript projection contract for non-conversation output blocks so projected content is visibly bounded, provenance-bearing, and safe to restep.

## Why

`510` covers imported file/content blocks, but the same family of problems appears anywhere TOAS projects non-conversation payloads into the transcript: tool results, command output, prompt/help surfaces, graph/projection views, imported context, and future derived artifacts.

Closed work already fixed several narrow failures:
- `443` established inert region semantics for help/example output.
- `476` added inert wrapping for risky `RESULT` content at the projection boundary.
- `480` made leaf prompt render output inert by default.
- `556` restored user-scope marker clarity for streamed tool-result projections.

Those fixes are valuable but local. The broader concept is a consistent "fences around outputs" policy: any transcript-projected payload that is not ordinary conversation should declare its boundary, source, potency, and intended parser affordances instead of relying on ad hoc readable text.

## Problem Statement

Current projection safety is split across result rendering, inert wrapping, import-shape ideas, Vim streaming formatting, and command/help special cases. That makes it easy for new output surfaces to:
- accidentally project slash-like, shell-like, YAML-like, or path-like content as live frontier intent;
- lose source/scope clarity when streamed or replayed through a different surface;
- use fences as visual formatting without a durable meaning for potency or provenance;
- make future reload/diff/writeback tooling parse transcript text brittlely.

## In Scope

- Inventory transcript-projected output classes and their current boundary shapes:
  - `RESULT` blocks from tool/user-shell/slash consequences
  - help, prompt, config, graph, history, and transcript views
  - imported/context file blocks (`510`)
  - streaming `projection_delta` surfaces
  - future derived/context/lens artifacts
- Define a small projection metadata vocabulary:
  - source/provenance
  - output kind
  - path or subject identity when applicable
  - potency (`active`, `inert`, `example`, `data`)
  - renderer/parser expectations
- Define when output should be fenced, inert-fenced, language-fenced, or left unfenced.
- Define fence sizing/escaping rules that safely contain embedded fences.
- Decide whether the contract is purely transcript text, durable metadata on transient/result nodes, envelope metadata, or a layered combination.
- Split implementation into focused follow-ons once the contract is clear.

## Out of Scope

- A broad renderer rewrite in the first investigation pass.
- Full import reload/diff/writeback tooling; keep that in `510` or follow-ons.
- Changing user-authored transcript intent semantics.
- Blanket inert wrapping of all output regardless of readability or intended activity.

## Candidate Contract Direction

Use explicit fenced blocks for payload-like output, with metadata in a stable header/comment line or structured info string, for example:

```text
```toas-output kind=file source=fs path=src/toas/step.py potency=data
...
```
```

For human-facing status summaries, short unfenced output may remain acceptable when it cannot arm intent and does not need identity/provenance. For examples, help text, prompt leaf content, and tool-rendered code/commands, prefer inert fences or an explicit `potency=example|inert` marker.

## Acceptance Criteria

- A written contract identifies every current output projection class and assigns a boundary/provenance/potency policy.
- `510` is either confirmed as the imported-content implementation slice under this umbrella or revised with a clearer dependency.
- At least one deterministic regression captures the historical restep failure mode where projected output is reinterpreted as operator intent.
- Follow-on implementation tasks are opened for concrete renderer changes if the investigation finds gaps.
- Roadmap/workboard surfaces distinguish the broad output-fence contract from the narrower imported-block task.

## Related

- `443` command-plane authoring and projection shape controls
- `476` inert wrapping policy for result projections and restep safety
- `480` prompt leaf render inertness
- `510` fenced import blocks with language/path/provenance shape
- `556` tool result user-scope marker projection gap
- `663` transport contract guardrails and projection boundary lock

## Progress

- **2026-06-08**: Renamed task to `260608-fenced-output-projection-contract.md` to follow the new task ID naming scheme. Implemented robust `toas-output` and `potency=inert` recognition inside `_is_inert_fence_start` and updated `strip_inert_regions` in `shell_intent.py` to track backtick counts for nested code fences.
- **2026-06-08**: Updated the test assertions in `tests/test_tools_rendering.py`, `tests/test_tools.py`, and `tests/test_step.py` to match the new fenced output blocks with `toas-output` metadata. Added new tests in `tests/test_shell_intent.py` to cover `toas-output` default inertness, explicit active potency overrides, and nested/escaping code fence scenarios. Completed all acceptance criteria and closed the task.

