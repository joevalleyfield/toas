Filed as: 260829-assistant-candidate-convergence
FKA:
AKA: assistant callable convergence; multi-callable assistant frontier; candidate discovery convergence
Legacy index:

keywords: runtime, implementation, active, correctness, frontier, projection, provenance, config

Parent: `260829-canonical-action-ingress-contract`
Depends on: `260829-user-authority-profile-propagation`
Related: `260803-tool-intent-ingress-separation`; `260803-language-exec-fenced-block-lane`

# Assistant Candidate Discovery Convergence

Route assistant frontiers through the same candidate-group discovery and
arbitration path already used for user frontiers, while preserving assistant
origin, assistant execution policy, explicit step boundaries, and assistant
shell projection behavior.

## Pressure

Assistant messages may contain multiple recognizable callable plans separated
by ordinary prose. The current runtime still extracts one legacy plan for an
assistant frontier, which leads the operator to use `leader-S`/`StepHere` as a
role-changing workaround. That can split the assistant turn or feed the next
model invocation a misleading transcript shape.

## Scope

- make candidate collection and arbitration role-neutral at the runtime seam;
- preserve candidate group and source order across multiple assistant plans;
- execute selected assistant groups with assistant authority and configured
  assistant policy;
- retain the existing assistant shell-block projection and staged-recovery
  behavior where it remains applicable;
- keep `/extract` as a separate manual inspection/adoption surface;
- add focused tests for multiple assistant plans, mixed candidates, selection
  modes, and unchanged assistant turn boundaries.

## Non-Goals

- introducing `ActionRequest` as a runtime type;
- implementing native provider calls, JSON, or executable-fence recognition;
- changing authority policy, shell bounds, or first-failure semantics;
- renaming `yaml_position`, `shell`, or `/extract`;
- creating a hidden execution loop.

## Acceptance

- assistant and user frontiers use the same candidate discovery and arbitration
  semantics for currently supported surfaces;
- an assistant message with multiple callable groups can be selected or
  resolved in order without being rewritten as a user turn;
- assistant-origin requests remain assistant-origin requests in durable and
  projected outcomes;
- existing user arbitration, assistant shell staging, and generation fallback
  tests remain green;
- the task records the focused verification command and any remaining seam.

## Implementation Note

The first slice should reuse the existing assistant plan handler for each
selected group. Candidate discovery may be shared with the user path, but
assistant operator commands and direct-user shell shorthand are not thereby
made assistant candidates.

## Outcome

Implemented the first convergence slice. Assistant frontiers now collect valid
YAML plan groups through the existing candidate collector, apply the configured
`in_order`, `first_wins`, `last_wins`, or `strict` selection behavior, and pass
selected groups through the existing assistant plan handler. Assistant origin,
shell staging, first-failure handling, and explicit frontier transitions remain
owned by that handler; user candidate behavior was not changed.

Verification:

- `./.codex-local/bin/uvt run pytest tests/test_runtime_step_runtime.py -q --no-cov`
- `./.codex-local/bin/uvt run pytest tests/test_runtime_intent_arbitration_edges.py tests/test_step.py -q --no-cov`
- `./.codex-local/bin/uvt run ruff check src/toas/runtime/step_runtime.py tests/test_runtime_step_runtime.py`
- `./.codex-local/bin/uvt run python scripts/targeted_coverage.py --cov toas.runtime.step_runtime --fail-under 100 --max-missing-files 0 -- tests/test_runtime_step_runtime.py -q`

All checks passed (`98`, `270`, lint, and `101` tests at `100%` targeted
coverage). The remaining seam is
provenance/intent-execution metadata for assistant groups; the canonical
`ActionRequest` work should decide that shape rather than this compatibility
slice inventing it.
