Filed as: 260829-canonical-action-ingress-contract
FKA:
AKA: canonical tool intent; action ingress contract; normalized action boundary
Legacy index:

keywords: runtime, decomp, inception, contract, provenance, frontier, tooling

Parent: `260803-tool-intent-ingress-separation`
Depends on: `260829-user-authority-profile-propagation`
Related: `260803-language-exec-fenced-block-lane`; `260412-json-callable-lane-parser-and-policy`; `260530-shell-lane-spawn-semantics`

Implementation follow-ons: `260829-assistant-candidate-convergence`; `260829-compound-tool-request-records`; `260829-action-plan-envelope`; `260829-ordered-frontier-item-stream`

# Canonical Action Ingress Contract

Define the post-recognition boundary shared by structured, native, and direct
user action ingress without requiring a universal TOAS intent ontology or an
immediate replacement for the incumbent normalized plan dictionaries.

## Intent

Specify what an ingress adapter must hand to the runtime, what source and
provenance facts must remain alongside the callable arguments, and how the
recognized action becomes an explicit TOAS step consequence.

## Current Incumbent

`src/toas/graph.py::normalize_tool_plan` already provides a useful shared
starting shape:

```python
[{"tool_name": "read_file", "args": {"path": "README.md"}}]
```

It normalizes callable aliases and optional intention text before capability
validation. This task must first test whether that shape is sufficient for the
next ingress slice. A typed domain object is an option, not an assumed result.

## Evidence-Backed Design Direction

The canonical boundary exposes a narrow action object rather than treating
nested dictionaries as the domain contract. Dictionaries remain useful as wire
and serialization forms, while the canonical object makes the meaningful
invariants discoverable without becoming an active policy object.

The object should begin narrowly, with fields for recognized callable data,
source/provenance, ordered-plan grouping, and the authority context selected for
dispatch. It should not become a universal representation of goal intent,
plan intent, operator objectives, or inferred focus.

The implementation evidence identifies the smallest useful construction
boundary: recognition and arbitration produce the object; authority resolution
consumes it. The design test is not whether a mapping can carry the
information, but whether the boundary keeps callable data, occurrence context,
and effective policy distinct.

## Scope

- define the adapter boundary after recognition/deserialization and before
  authority resolution;
- decide which action fields are semantic inputs versus source/provenance
  metadata;
- keep provider call ids, source spans, ingress lane, and raw diagnostic refs
  out of capability arguments;
- specify ordered-plan position and grouping identity where first-failure or
  staged remainder behavior depends on them;
- define user and assistant frontier transitions, including the fact that
  assistant output alone is not user authority;
- define deterministic arbitration when multiple ingress candidates are
  present in one frontier;
- identify the smallest implementation seam and its focused test corpus.

## Required Contract Questions

1. Can the incumbent normalized list-of-dictionaries represent every currently
   supported action without losing required identity or provenance?
2. If not, what is the smallest adjacent envelope or domain type that adds the
   missing invariant without moving provider fields into tool arguments?
3. Which facts must be durable request metadata, which belong only to
   diagnostics, and which are projection-only?
4. How does each adapter represent recognition failure, ambiguity, and a valid
   action that awaits the user-mediated `step` boundary?
5. No equivalence relation is part of this contract. Shared implementation and
   guardrails protect common semantics; repeated requests remain distinct
   occurrences, and adapters do not compare or deduplicate them as a side
   effect of normalization.

## Evidence Pass: Current Direction

The current code confirms that recognition, normalization, authority, and
execution are already separate concerns even though the hand-off is represented
by dictionaries:

- `normalize_tool_plan` owns callable aliases, argument mapping, shell-command
  normalization, and optional intention text;
- intent arbitration adds source position, candidate order, and a temporary
  candidate id before frontier resolution;
- execution receives the normalized call and applies workspace, grant, and
  timeout policy through shared runners;
- durable `tool_request` records currently retain only the normalized plan and
  related message id;
- result nodes already carry origin role/kind and projection lane separately
  from the tool payload.

The object should therefore sit between normalization/arbitration and authority
resolution. It should not replace durable records or absorb effective policy;

### Adopted object boundary

Use a small canonical `ActionPlan` envelope containing ordered `ToolRequest`
values. The plan carries three groups of context:

```text
ordered requests
  capability name
  validated/normalized arguments
  optional operator-stated intention

source identity
  origin role and ingress lane
  source message/span or provider call identity
  raw-source diagnostic reference when needed

plan identity
  ordered position
  grouping identity for one submitted plan
```

Authority resolution should consume that object and produce or attach a
dispatch context containing requested context, effective authority profile,
workspace/grant policy, and execution settings. The canonical action object
must not claim that requested authority is effective authority.

The existing list-of-dictionaries can remain the serialization boundary while
adapters and durable writers migrate to the object deliberately. The object
should make invalid combinations unrepresentable or reject them at
construction, especially missing capability names, malformed arguments,
conflicting source identity, and ambiguous plan position/grouping.

### Evidence update: current implementation boundary

The first implementation wave confirms the narrow version of this boundary:
`ActionPlan` contains frozen `ToolRequest` values and optional plan-level
context, while `as_normalized_plan()` preserves the incumbent list shape for
execution and storage. Structured YAML/JSON requests retain their callable
payloads; `toolset` is recorded as request metadata rather than inserted into
arguments. Executable fence lanes enter the same normalized path, and Python
runtime/artifact details remain execution arguments/results rather than a new
authority or history type.

This is enough to establish the hand-off boundary. It is not evidence that
every ingress fact must become a field on `ActionPlan`, nor that all durable
records should be migrated immediately.

### Naming decision

`ToolRequest` is the name for one inert callable. It carries capability,
arguments, and optional stated intention; it does not need to repeat frontier
provenance. `ActionPlan` is the surrounding recognized occurrence and carries
origin, ingress, source, and plan-selection context. `CallableAction` is not
needed: “callable” usefully suggests only capability plus arguments. Prior-art
and collision research is deferred until the vocabulary proves consequential.

## Working Field Model

The plan can be rich without becoming active policy. Its fields describe the
recognized occurrence, while each request remains capability-shaped:

| Field | Belongs to | Meaning |
|---|---|---|
| `capability` | ToolRequest | The normalized capability name, such as `read_file`. |
| `arguments` | ToolRequest | The arguments that will be passed to that capability. |
| `stated_intention` | ToolRequest | Optional explanatory text supplied with the request. |
| `origin` | ActionPlan | The semantic role of the frontier that supplied it: user or assistant. |
| `ingress` | ActionPlan | The surface through which it was recognized: YAML, native call, shell, and so on. |
| `source` | ActionPlan | Where the plan came from, such as a transcript location or provider call. |
| `plan_position` | ActionPlan | The plan's place among plans recognized in a frontier. |
| `plan_group` | ActionPlan | The surrounding submitted occurrence, when grouping matters. |

Plan context travels with the plan so downstream code does not have to infer
provenance from the arguments or reconstruct it from raw syntax. Tool requests
remain inert and do not
evaluate anything, deduplicate anything, or grant authority.

The `ToolRequest` is inert data that offers a capability request to the next
stage. It can be inspected, projected, stored, or passed to authority
resolution without executing anything. Capability execution begins only after
the enclosing plan reaches the explicit dispatch and `step` path.

Authority, execution policy, execution status, results, and retry state remain
separate downstream data.

## Status-Quo Field Crosswalk

| Object field | Belongs to | Current source | Current condition |
|---|---|---|---|
| `capability` | ToolRequest | normalized `tool_name` | Already present after `normalize_tool_plan`. |
| `arguments` | ToolRequest | normalized `args` | Already present, with aliases resolved. |
| `stated_intention` | ToolRequest | normalized `intention` | Already present when supplied. |
| `origin` | ActionPlan | frontier role and result-node provenance | Available at resolution, but not carried by the normalized plan itself. |
| `ingress` | ActionPlan | candidate kind or recognizing adapter | Available during arbitration; not carried into the plan. |
| `source` | ActionPlan | frontier message id, source position, or provider call id | Available in surrounding paths, but not attached to the callable payload. |
| `plan_position` | ActionPlan | arbitration `order` | Temporary candidate metadata; not part of the normalized call. |
| `plan_group` | ActionPlan | arbitration `intent_id`/candidate set | Temporary grouping metadata; not part of the normalized call. |

This crosswalk suggests the first plan envelope’s value is primarily
contextual: the capability and arguments already exist, while origin, ingress,
source, and plan context are currently adjacent runtime facts that can be lost
or reconstructed by later stages. The object should gather those facts at the
existing recognition boundary without changing what a capability receives.

## Ingress Ownership Matrix

Each ingress surface contributes recognition-specific facts, then hands the
same kind of inert `ToolRequest` to the shared path:

| Ingress | Recognizer contributes | ToolRequest origin | Shared path begins |
|---|---|---|---|
| Direct-user YAML | deserialized mapping/list and source span | `user` | after `normalize_tool_plan` |
| Assistant YAML | deserialized mapping/list and assistant source span | `assistant` | after `normalize_tool_plan` |
| Direct-user `$` command | command text, parsed argv, source span | `user` | after shell-command normalization |
| JSON callable lane | JSON value and source span | whichever frontier supplied it | after JSON deserialization and shared normalization |
| Executable fence lane | fence metadata, body, and source span | whichever frontier supplied it | after fence recognition and body normalization |
| Native provider call | provider response, call id, and model-call context | `assistant` | after provider-call normalization |

The adapter owns recognition, parsing, and source details. The shared path owns
authority resolution, capability validation, execution, durable request/result
facts, and projection. Slash/operator commands remain a separate operator
command path unless a concrete command is deliberately translated into an
`ToolRequest`.

## Configuration And Arbitration

Configuration currently affects two different stages:

| Stage | Existing settings | Meaning |
|---|---|---|
| Recognition | `extraction.user_shell`, `extraction.operator_command`, `extraction.loose_command_fallback`, `extraction.yaml_position` | Which surfaces and structured candidates are considered. |
| Arbitration | `extraction.intent_arbitration` | What to do when more than one candidate is recognized: execute in textual order, select first, select last, or report ambiguity. |

The proposed flow is:

```text
recognized surfaces
  → ToolRequest values grouped into an ActionPlan
  → configured arbitration
  → selected request(s)
  → authority resolution
  → execution
```

Arbitration is selection, not authority. It should not alter the request’s
origin or make an assistant request user-authoritative.

There is one existing configuration ambiguity to resolve: extraction uses
`yaml_position` to choose a plan, while candidate collection can discover all
valid YAML plans in the frontier before applying `intent_arbitration`. The
current evidence supports treating `yaml_position` as a legacy single-plan
selection/fallback setting. The converged candidate path discovers active
plans and applies `intent_arbitration`; it does not need a new meaning for
`yaml_position`. A rename or replacement is deferred unless a concrete
consumer still needs the distinction exposed.

## Three Selection Surfaces

The current behavior is easier to understand as three separate surfaces:

| Surface | What it does | Typical use |
|---|---|---|
| `step` recognition | Finds executable-looking plans, shell commands, and operator commands in the active frontier. | Normal user or assistant progression. |
| Configured arbitration | Chooses one, all, or none of the recognized candidates according to `intent_arbitration`. | Automatic resolution of a frontier containing multiple candidates. |
| `/extract` | Lists callable candidates from the latest assistant message, then optionally adopts one as a new user turn. | Recovery when an assistant proposal was not selected by normal stepping. |

`/extract` is therefore not simply another spelling of `step` extraction. It is
an operator inspection and adoption surface. Its displayed candidate index is
local to the latest assistant message, and adoption creates a new user
frontier. That explains both its limited everyday use and its memory burden.

The naming pressure is consequently broader than `yaml_position`: the system
needs vocabulary for candidate discovery, automatic frontier arbitration, and
manual assistant-candidate adoption. Existing names may remain compatibility
surfaces until a concrete rename is chosen.

## Convergence Direction

Assistant and user frontiers should converge on the same candidate-discovery
and arbitration model while retaining their different authority profiles.

An assistant frontier may contain several recognizable action requests separated
by prose. Those requests should remain associated with the one assistant
message, retain their source spans and order, and be selected by the same
arbitration configuration used for user candidates. Selection must not require
copying the assistant text into a new user turn.

The resulting distinction is:

```text
same candidate model
  assistant origin → configured assistant authority
  user origin      → intentionally unbounded user authority
```

This removes the need to use leader-S/StepHere as a role-changing workaround.
It also preserves the next model invocation’s turn boundaries: assistant
prose remains assistant prose, while action results remain consequences of
that assistant frontier rather than reformulated user instructions.

Manual `/extract` remains useful for inspection, recovery, or deliberate user
adoption. It is no longer the normal mechanism for selecting among assistant
actions that the regular candidate recognizer can see.

## Arbitration Unit And Configuration

The unit presented to arbitration is an `ActionPlan`: one recognized plan or
one standalone command occurrence. An `ActionPlan` may contain several
`ToolRequest` values. The plan preserves the order of its requests for
execution and first-failure recovery.

Across a frontier, selection then has a simple meaning:

```text
discover action plans
  → order plans by source position
  → apply selection mode
       in_order  = resolve every plan in source order
       first_wins = resolve the first plan only
       last_wins  = resolve the last plan only
       strict     = resolve none and report the ambiguity
```

This applies to both user and assistant frontiers. The selected plan retains
its original origin when it reaches authority resolution.

Configuration should describe these stages separately:

- lane enablement controls which surfaces may produce candidates;
- candidate discovery finds all active candidates in the frontier;
- candidate selection chooses groups using the arbitration mode.

`yaml_position` remains a legacy-shaped compatibility setting for the
single-plan extraction path. It should not be given new semantics merely to
make it agree with candidate discovery. `/extract --index` remains manual
candidate selection over the latest assistant message and is separate from
automatic arbitration.

## Confirmed Call Flow

The accepted flow has two distinct stages:

```text
ingress surface
  → recognize and parse
  → canonical action object
  → authority resolution
  → shared capability validation and execution
  → durable request/result facts
  → projection and next explicit step
```

The canonical action object is the hand-off between recognizing an action and
deciding how that action may execute. It describes the action and its source;
it does not grant authority.

Authority resolution produces a separate dispatch context. A direct-user
frontier selects the intentionally unbounded user profile; an assistant
frontier selects the user-configured assistant policy. Both continue through
shared validation, capability execution, durable recording, and explicit
user-mediated `step` boundaries.

Assistant text alone therefore does not execute. It must be presented at an
assistant frontier and processed by a later step. Explicit user reformulation
or adoption creates a new user frontier and is a new action-origin event.

## Durable Compound Shape

One `tool_request` record is the durable occurrence envelope for the selected
frontier action. A single `ActionPlan` may retain the incumbent list payload:

```json
{
  "kind": "tool_request",
  "related_to": "n42",
  "payload": [
    {"tool_name": "read_file", "args": {"path": "README.md"}}
  ]
}
```

When one frontier selects multiple sibling plans, the same record may use a
compound payload without turning plans into nested plans:

```json
{
  "kind": "tool_request",
  "related_to": "n42",
  "payload": {
    "plans": [
      {"requests": [{"tool_name": "read_file", "args": {"path": "README.md"}}]},
      {"requests": [{"tool_name": "echo", "args": {"text": "done"}}]}
    ]
  }
}
```

The compound envelope represents sibling `ActionPlan` occurrences selected
from one frontier. Each plan owns only its ordered `ToolRequest` values.
Origin, source position, and selection metadata may accompany a plan, but
effective authority, execution status, results, and retry state remain
separate evidence. Existing single-plan payloads remain readable while the
compound form is introduced deliberately.

## Durable Evidence Crosswalk

The implementation evidence supports the following disposition. “Runtime”
does not mean unimportant; it means the fact is available while resolving the
current frontier but is not yet required in the durable request record.

| Fact | Current location | Durable disposition | Reason |
|---|---|---|---|
| Capability name and normalized arguments | `ToolRequest` / payload | Durable now | They are the callable request offered to execution and replay. |
| Stated intention | `ToolRequest` / payload when supplied | Durable now | It is supplied request context, not authority. |
| Frontier message identity | `tool_request.related_to` | Durable now | It anchors the occurrence to transcript lineage. |
| Sibling plan grouping and request order | Compound payload / request order | Durable now | They preserve occurrence boundaries and first-failure semantics. |
| Toolset | Request metadata for structured YAML/JSON | Durable now where applicable | It identifies the registry family without entering callable args. |
| Origin role | Frontier message role and runtime context | Reconstructable for current lanes | The related message remains the source of truth; duplicate storage needs a concrete consumer. |
| Ingress kind | Candidate kind / recognizer | Runtime for now | It supports routing and diagnostics, but current execution and records do not require it. |
| Source span or raw fence location | Recognizer candidate | Runtime/diagnostic for now | The source message and content remain durable; spans are useful for interaction but not yet replay identity. |
| Plan position and selection identity | Arbitration candidate metadata | Runtime for now | They explain current selection but are not execution identity or deduplication keys. |
| Requested authority context | Action/dispatch context | Not request evidence | A request may describe an action, but source syntax must not grant authority. |
| Effective authority and execution policy | Authority resolution / execution | Separate downstream evidence | They describe what was applied rather than what was requested. |
| Attempt, retry, and restaging identity | Result/recovery paths | Separate downstream evidence | They describe lifecycle consequences, not the original callable request. |
| Exit status, stdout, stderr, timeout, and artifact details | Tool result payload/projection | Durable result evidence | They describe execution output and remain distinct from request meaning. |
| Provider call identity and raw provider response | Future native adapter | Deferred | Native calling needs a concrete provider round-trip before these become required fields. |

This crosswalk resolves the immediate question without requiring a richer
durable action object. `ActionPlan` gathers context during recognition and
arbitration; durable writers should add a field only when a specific replay,
audit, or provider round-trip cannot be expressed through the existing message
link, request payload, metadata, and result records.

## Boundaries

- direct-user action selects the intentionally unbounded user profile;
- assistant action selects the user-configured assistant policy;
- authority is resolved after ingress and is never granted by source syntax,
  provider metadata, or a requested context field;
- adapters parse and normalize only; they do not execute, schedule retries,
  write durable results, or create hidden loops;
- explicit `step` remains the boundary at which the recognized consequence is
  resolved.

## Guardrails For Future Work

These are architectural guardrails, not a second test framework or a demand
for symmetry between ingress lanes. They preserve the useful shape of the
system when this design is revisited from memory:

- An ingress adapter may recognize, parse, normalize, and diagnose; it may not
  execute a capability, select effective authority, write results, or create a
  hidden follow-up step.
- All recognized callable lanes enter the shared capability validation and
  execution path. A new lane must not grow a parallel executor because its
  syntax or provider is different.
- `ToolRequest` remains inert capability-plus-arguments data. Provenance,
  authority, policy, lifecycle, and result facts do not enter callable args.
- `ActionPlan` carries recognition context; it does not grant authority or
  turn requested authority into effective authority.
- Direct-user and assistant origins remain distinct authority inputs. User
  adoption/restaging creates an explicit new user frontier rather than
  laundering assistant content.
- Direct-user execution remains intentionally unbounded by default; assistant
  execution remains governed by the user-configurable assistant policy.
- One `step` resolves one explicit layer of consequence. Adding a native or
  language lane must not introduce an implicit execution loop.
- Durable request records preserve requested callable meaning and occurrence
  linkage. Results preserve execution outcomes. Neither is replaced by a
  compact projection.
- Projections, diagnostics, harness observations, and inferred focus are
  never execution authority and must remain inert when copied or replayed.
- Add durable identity or metadata only when an actual replay, audit, retry,
  or provider round-trip cannot be expressed by the existing relationships.
- Tests should enforce these boundaries at the shared seams; they need not
  prove that independently implemented lanes are semantically equivalent.

## Non-Goals

- implementing native provider calling;
- adding more executable-language lanes beyond the implemented first wave;
- implementing `toas-tool` call-expression syntax;
- replacing all normalized dictionaries with a class hierarchy;
- redesigning durable record families;
- changing capability validation or first-failure execution semantics;
- making goal, plan, and action intent universal runtime record types.

## Done When

- a canonical action boundary is documented with valid, invalid, ambiguous,
  and awaiting-step examples;
- an ingress ownership matrix covers direct user, YAML, JSON, executable
  fences, and native provider calls;
- provenance and authority fields are explicitly separated from capability
  arguments;
- mixed-candidate arbitration and frontier transitions are deterministic;
- the decision to retain, wrap, or replace the incumbent normalized shape is
  explicit;
- any implementation follow-on has one owner, bounded write surfaces, and a
  focused test story.

## Current Status

This remains a requirements child, but the first implementation evidence now
exists: authority propagation, ordered candidate arbitration, the narrow
`ActionPlan` envelope, compound request records, structured toolset metadata,
and executable fence lanes are all implemented and verified. The contract
has now been revised against those seams. The durable-versus-runtime question
is provisionally resolved by the crosswalk above. Native provider identity and
broader history migration remain gated on a concrete consumer rather than on
completeness of the object model.

## Current Next Step

Use the crosswalk to inspect one concrete future consumer at a time. Open a
bounded follow-on only if a specific replay, audit, or provider-identity
invariant is currently lost by the existing message link, request payload,
metadata, or result records.

Until such a consumer appears, this task is a documentation and routing
reference rather than an invitation to migrate every dictionary or add a new
ingress lane. Native provider identity, broader durable metadata, and stronger
history/replay semantics remain deferred decisions, not missing pieces of the
current action path.
