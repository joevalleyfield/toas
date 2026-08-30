# Action-Intent Cluster: Classification And Sequence

## Purpose

Classify the existing open issues around action recognition, tool calling,
execution, durable evidence, and resolution so implementation follows the
actual dependency structure rather than the order in which issues were
written.

This is a planning note. It does not close, rewrite, or reprioritize tasks by
itself.

## Classification

### Core contract and ingress boundary

**260803-tool-intent-ingress-separation** is the requirements parent for the
cluster. It owns the boundary between ingress adapters and shared runtime
semantics, the shared-path guardrails, the native/text/harness
separation, and the evidence required before bounded children are opened.

**260803-language-exec-fenced-block-lane** is the requirements parent for
executable fence recognition, activation, arbitration, projection, and staged
recovery. It is an ingress-surface design, not a second execution model.

**260412-json-callable-lane-parser-and-policy** is a conditional serialization
corollary of the executable-fence work. It should remain parked until the
shared scanner and structured-callable boundary exist, then enter the same
normalizer and policy path as YAML.

**260829-user-authority-profile-propagation** is the first concrete runtime
slice. It addresses an existing authority-selection defect without requiring
the final canonical domain object or native provider support.

### Execution seam and capability behavior

**260530-shell-lane-spawn-semantics** is an execution hardening follow-on. It
should follow or accompany the authority-profile slice, because spawn behavior
must be shared while policy differences remain explicit.

**260621-windows-shell-launcher-and-path-resolution** is a platform-specific
verification/fix slice. It is valuable, but does not define the general
authority or ingress model; it can proceed independently when a Windows host
is available.

The existing `shell` name is a vocabulary pressure, not a prerequisite. A
rename should wait for a concrete migration decision and should not be mixed
into authority propagation.

### Durable evidence and resolution support

**260626-events-jsonl-multiplicity-and-merge-provenance** and its dependent
history-integrity tasks concern the durable substrate needed for richer
branching, merging, and history reuse. They are not prerequisites for the
first single-lineage action path, but they become a gate before native call
identity, parallel action plans, or history-based restaging are expanded.

**260627-fail-closed-history-query-hardening** and
**260627-history-surface-corruption-semantics** should be sequenced with that
durable-history track. They protect the evidence substrate; they do not own
action recognition or execution policy.

**260627-history-affordances-semantic-restaging** is exploratory until a real
operator use case identifies one bounded restaging affordance. Existing
first-failure recovery can remain the execution owner in the meantime.

### Native calling and guardrail validation

Native provider support is a later ingress adapter, not the starting point.
The parent task's native work should split only after these are stable enough:

1. the authority-selection seam;
2. the canonical post-recognition shape or an explicit decision to retain the
   incumbent normalized dictionaries;
3. the one-layer `step` transition for a tool-call frontier; and
4. the durable request/result identity needed for a later provider result.

**260602-transport-equivalence-certification** is a separate transport concern,
not an action-architecture prerequisite. It should be activated only when a
concrete transport failure or independently implemented adapter makes stronger
comparison worthwhile. Shared implementation and boundary guardrails remain
the primary protection here.

### Projection, focus, and operator context

**260823-intent-tail-focus-trace**, **260823-conversation-map-projection**, and
**260823-projection-discoverability** are adjacent projection work. They may
consume action evidence, but none should define action authority or block the
execution path.

**260829-declared-objective-lane** is orthogonal context vocabulary. Its
explicit operator-maintained objective must remain distinct from action intent
and should not be made a prerequisite for tool ingress.

**260813-transcript-highlighting-design** and
**260825-visible-transcript-turn-ids** are presentation/discoverability support;
they can proceed when a concrete consumer needs them.

### Operational, governance, and broader architecture

**260811-activity-health-telemetry** is operational support for diagnosing
stalls. It is useful after execution paths have real health observations, but
it should not become a semantic owner of execution or terminality.

**260806-assistance-provenance-trailers** is governance and commit/history
provenance. It is related to evidence, but does not belong in the action
normalization prerequisite path.

**260614-legacy-and-fidelity-adapter-precedence** is a cross-cutting adapter
vocabulary task. Activate it when a concrete result or stream adapter exposes
conflicting truth, rather than using it to pre-design every ingress lane.

**260509-multi-operator-orchestration**, **260626-transcript-parallelism-design-
pressures**, **260428-cross-repo-intent-routing**, and transcript checkpoint
optimization are broader architecture explorations. They should remain
outside the first action-intent implementation sequence.

## Proposed Sequence

### 0. Planning checkpoint — complete

- retain the local goal/plan/action vocabulary as an analytical lens only;
- distinguish declared objectives from recognized action requests;
- preserve direct-user unbounded authority and user-configurable assistant
  policy;
- preserve existing normalized plans and durable record families;
- commit the current planning baseline.

### 1. Establish the authority seam — complete

**260829-user-authority-profile-propagation** is complete. Direct-user
structured actions now use the intentionally unbounded user profile while
assistant actions retain the configured assistant policy. The effective
profile is selected at the existing dispatch boundary without a second
capability executor.

This slice answers the most immediate status-quo defect and gives later lanes
a concrete authority interface to target.

### 2. Close execution-specific drift — conditional

Use the authority seam to finish the smallest relevant parts of
**260530-shell-lane-spawn-semantics** and, when possible,
**260621-windows-shell-launcher-and-path-resolution**, but only when a concrete
spawn or platform failure justifies the slice. These remain execution
hardening, not prerequisites for the current contract work.

### 3. Fix the ingress boundary — current checkpoint

Reconcile **260803-tool-intent-ingress-separation** and
**260829-canonical-action-ingress-contract** with the completed evidence. The
repository now has a narrow `ActionPlan` envelope, inert `ToolRequest` values,
ordered candidate arbitration, compound request records, and explicit
toolset metadata while capability payloads remain unchanged. The remaining
work is to decide which contextual facts must travel at this boundary and
whether any incumbent setting, especially `yaml_position`, needs a bounded
compatibility follow-on.

#### Canonical ingress checkpoint

The evidence pass now resolves the immediate boundary questions. The canonical
handoff is a narrow `ActionPlan` envelope containing ordered, inert
`ToolRequest` values. A `ToolRequest` contains normalized capability data,
arguments, and optional stated intention. The enclosing plan may carry origin,
ingress, source, plan position, and grouping context. Neither object grants
authority or carries effective execution policy.

The incumbent normalized list-of-dictionaries remains a valid serialization and
execution boundary. The envelope is an adjacent domain boundary, not a demand
for immediate migration or a new class hierarchy. Durable request records and
result records remain separate occurrence and outcome evidence; provenance or
policy fields do not move into callable arguments merely for convenience.

The accepted call flow is:

```text
recognize and parse
  → ActionPlan / ToolRequest
  → configured candidate arbitration
  → authority resolution
  → shared validation and execution
  → durable request/result facts
  → inert projection and next explicit step
```

User and assistant frontiers use the same recognition and arbitration model,
but retain distinct authority inputs. Direct-user action is intentionally
unbounded; assistant action follows the user-configurable assistant policy.
Assistant text alone does not execute, and explicit adoption creates a new user
frontier rather than laundering assistant origin.

The action contract does not define semantic equivalence. Requests are not
compared or deduplicated as a consequence of normalization; repeated requests
remain distinct occurrences. Shared implementation and seam guardrails provide
the relevant consistency without introducing an equivalence evaluator.

The current configuration distinction is also settled provisionally:
`yaml_position` remains legacy single-plan compatibility vocabulary. Candidate
discovery and configured arbitration are the converged path; no new meaning or
rename is warranted without a concrete consumer. `/extract` remains a manual
inspection/adoption surface, separate from automatic `step` arbitration.

Future ingress adapters must recognize, normalize, and diagnose only. They
must enter shared authority, validation, execution, durable-evidence, and
projection paths, preserve explicit `step` boundaries, and avoid hidden loops.
Native provider identity, broader durable metadata, parallel plans, and
history restaging remain deferred until a concrete replay, audit, provider, or
operator use case cannot be expressed by the existing relationships.

### 4. Add text ingress corollaries selectively — first wave complete

The first executable-fence wave is complete: shared scanning and activation,
Bash, JSON structured fences, unsupported-language diagnostics, toolset
provenance, and Python execution all use the shared normalization, authority,
execution, durable-fact, and projection path. Further language lanes and
`toas-tool` syntax remain separate future children.

### 5. Add native provider ingress — deferred

Do not split native request advertisement, response normalization, tool-call-
only handling, mixed-output arbitration, or result projection until the
canonical step-state and durable result-identity decisions are stable.

### 6. Certify and expand evidence

Apply shared-path guardrails to each new adapter and strengthen durable-history
integrity before adding
parallel action plans, native identity-heavy flows, or history restaging.

### 7. Consume the evidence through projections

Only after a concrete consumer appears, advance focus traces, maps,
discoverability, highlighting, working-memory, or restaging. These are views
over action evidence, not alternate sources of execution truth.

## Gates And Deferrals

Do not open implementation children for native calling, broad canonical-object
replacement, parallel orchestration, or history restaging yet. Each requires
one additional decision or observed use case:

- native calling: a stable step-state and result-identity contract;
- canonical object replacement: an invariant the incumbent dictionaries cannot
  express without repeated adapters or ambiguity;
- parallel orchestration: a concrete merge/provenance consumer;
- history restaging: a recurring operator job with a crisp distinction between
  staging prior intent and executing it now.

The canonical-ingress documentation checkpoint is complete. Close that child
task with this note as its durable design reference. Open another
implementation follow-on only after its invariant, owner, and focused test
story are clear.
