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
semantics, the cross-lane equivalence contract, the native/text/harness
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

### Native calling and equivalence validation

Native provider support is a later ingress adapter, not the starting point.
The parent task's native work should split only after these are stable enough:

1. the authority-selection seam;
2. the canonical post-recognition shape or an explicit decision to retain the
   incumbent normalized dictionaries;
3. the one-layer `step` transition for a tool-call frontier; and
4. the durable request/result identity needed for a later provider result.

**260602-transport-equivalence-certification** is validation, not architecture.
It should be activated only when at least two meaningful ingress or transport
paths exist whose shared behavior is worth certifying. It may eventually be
closed as unnecessary if contract-level parity remains sufficient.

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

Run cross-lane conformance and transport-equivalence scenarios once there are
multiple active lanes. Strengthen durable-history integrity before adding
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

The next meaningful action is therefore a documentation checkpoint under the
canonical ingress task: update the contract from the completed implementation
evidence, especially the distinction between inert request data, plan context,
authority context, and durable occurrence metadata. Open another implementation
follow-on only after its invariant, owner, and focused test story are clear.
