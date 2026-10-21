# Open-set and workboard coherence review

Filed as: 261020-open-set-workboard-review
FKA:
AKA: open backlog story; manual workboard reconciliation
Legacy index:

keywords: docs, governance, historical, maintainability, workboard

Status: CLOSED — 2026-10-20

## Finding

The previous manual board did not describe one coherent current queue. It mixed
June parallelism sequencing, August ingress priorities, a September authority/
config vote, a long closure ledger, and May health checkboxes. State-mode alpha
and branch-policy work were largely absent from its priority narrative.

Concrete drift:

- Session identity and JSON executable fences were presented as next work even
  though their tasks are closed with implementation evidence.
- The relationship roots included closed live-acceptance work.
- Closed config-help, newline-policy, newline-healing, and Vim transport tasks
  were still mentioned as current or new work.
- Release checks were called advisory for lint/types despite the gated script.
- Parallelism was called the immediate design center while the roadmap still
  asked to finish already-completed storage proof/recovery work.
- Basic multi-endpoint/model switching was an unelaborated backlog item even
  after endpoint catalogs, discovery, and model selection landed.
- A repaired speculative tool-kind latch was still an unqualified pain point.

## Disposition

Rewrote manual workboard sections around actual open scope, consolidated
sequencing into one place, and added state/policy/ingress coordination roots.
Preserved the dated operator votes as values and historical context, without
pretending they are a current literal task order. No open task was closed,
assigned, or promoted by this review. The readiness of partially implemented
parents still requires acceptance/artifact comparison; this is an inventory
review, not a claim to have audited every implementation criterion.

Refreshed roadmap direction because its storage-first sequencing was stale,
without adding task tracking to it. Reconciled the architecture coordination
summary and child-status table with current task locations; retained dated
investigation notes as historical evidence.

## Complete open-set map

Each of the 46 open files belongs to exactly one group below. Grouping helps
explain the inventory and does not impose a universal execution order.

### State-mode operation (5)

- [260926-state-step-requirements](../open/260926-state-step-requirements.md)
- [261010-direct-tool-artifact-capture](../open/261010-direct-tool-artifact-capture.md)
- [261010-rolling-tool-failure-memory](../open/261010-rolling-tool-failure-memory.md)
- [261010-state-inference-response-resilience](../open/261010-state-inference-response-resilience.md)
- [261010-state-result-history-sideslip](../open/261010-state-result-history-sideslip.md)

### Policy, authority, and explicit objectives (5)

- [260829-declared-objective-lane](../open/260829-declared-objective-lane.md)
- [260830-exec-grant-policy-matchers](../open/260830-exec-grant-policy-matchers.md)
- [260920-branch-projected-policy-program](../open/260920-branch-projected-policy-program.md)
- [260920-effective-policy-provenance-inspection](../open/260920-effective-policy-provenance-inspection.md)
- [260920-one-shot-control-ingress-disposition](../open/260920-one-shot-control-ingress-disposition.md)

### Execution ingress and source fidelity (6)

- [260803-language-exec-fenced-block-lane](../open/260803-language-exec-fenced-block-lane.md)
- [260803-tool-intent-ingress-separation](../open/260803-tool-intent-ingress-separation.md)
- [260831-language-write-materialization-fences](../open/260831-language-write-materialization-fences.md)
- [260831-transcript-source-reference-operations](../open/260831-transcript-source-reference-operations.md)
- [260901-retry-materialization-adapters](../open/260901-retry-materialization-adapters.md)
- [260907-extraction-execution-boundary](../open/260907-extraction-execution-boundary.md)

### Platform and patch behavior (5)

- [260418-weak-model-safe-apply-patch-contract](../open/260418-weak-model-safe-apply-patch-contract.md)
- [260515-apply-patch-windows-crlf-hardening](../open/260515-apply-patch-windows-crlf-hardening.md)
- [260621-windows-shell-launcher-and-path-resolution](../open/260621-windows-shell-launcher-and-path-resolution.md)
- [261015-windows-compatibility-restoration](../open/261015-windows-compatibility-restoration.md)
- [261017-msys-vim-native-host](../open/261017-msys-vim-native-host.md)

### Operator projections and provenance (6)

- [260806-assistance-provenance-trailers](../open/260806-assistance-provenance-trailers.md)
- [260813-transcript-highlighting-design](../open/260813-transcript-highlighting-design.md)
- [260823-conversation-map-projection](../open/260823-conversation-map-projection.md)
- [260823-intent-tail-focus-trace](../open/260823-intent-tail-focus-trace.md)
- [260823-projection-discoverability](../open/260823-projection-discoverability.md)
- [260825-visible-transcript-turn-ids](../open/260825-visible-transcript-turn-ids.md)

### Architecture, history, and stream observation (7)

- [260614-architecture-follow-through-coordination](../open/260614-architecture-follow-through-coordination.md)
- [260614-legacy-and-fidelity-adapter-precedence](../open/260614-legacy-and-fidelity-adapter-precedence.md)
- [260626-events-jsonl-multiplicity-and-merge-provenance](../open/260626-events-jsonl-multiplicity-and-merge-provenance.md)
- [260626-transcript-parallelism-design-pressures](../open/260626-transcript-parallelism-design-pressures.md)
- [260627-history-affordances-semantic-restaging](../open/260627-history-affordances-semantic-restaging.md)
- [260811-activity-health-telemetry](../open/260811-activity-health-telemetry.md)
- [261011-streaming-mode-env-leak-parent](../open/261011-streaming-mode-env-leak-parent.md)

### Release operation (2)

- [260627-release-helper-tooling](../open/260627-release-helper-tooling.md)
- [260627-release-process-and-weekly-release-lane](../open/260627-release-process-and-weekly-release-lane.md)

### Parked performance, orchestration, and planning experiments (10)

- [260412-transcript-lcp-checkpoint-optimization](../open/260412-transcript-lcp-checkpoint-optimization.md)
- [260428-cross-repo-intent-routing](../open/260428-cross-repo-intent-routing.md)
- [260509-alternative-operator-frontends](../open/260509-alternative-operator-frontends.md)
- [260509-multi-operator-orchestration](../open/260509-multi-operator-orchestration.md)
- [260524-attention-focused-workboard-layout](../open/260524-attention-focused-workboard-layout.md)
- [260524-auto-inferred-task-dependencies](../open/260524-auto-inferred-task-dependencies.md)
- [260524-exploratory-work-representation-model](../open/260524-exploratory-work-representation-model.md)
- [260524-workboard-as-control-surface](../open/260524-workboard-as-control-surface.md)
- [260530-shell-lane-spawn-semantics](../open/260530-shell-lane-spawn-semantics.md)
- [260602-transport-equivalence-certification](../open/260602-transport-equivalence-certification.md)

## Best next decisions

- Compare completed criteria with current behavior for grant matchers, retry
  adapters, and the broad ingress/fence parents before extending them.
- Select one bounded next slice: request composition/resilience needs remaining
  schema/history choices; policy provenance has projection but incomplete
  reduction/presentation; one-shot control needs caller inventory.
- Reconcile launcher/MSYS harness history with current operator evidence and
  retest gVim before diagnosing a current defect. Linux remains unverified here.
- Keep speculative stderr separation, parallelism/provenance, and planning
  automation conditional on a concrete consumer or observed failure.

## Validation

All open files reviewed for intent, lifecycle, relationships and progress;
ambiguous/high-impact parents and the relevant closed-task evidence read in
more detail. The mapping asserts exact coverage with no duplicate membership.
Generated workboard synchronized; local links, live roots, and sync idempotence
checked. Documentation/task changes only; runtime tests were not repeated.
