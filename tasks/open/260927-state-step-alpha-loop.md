Filed as: 260927-state-step-alpha-loop
FKA:
AKA: integrated state-step alpha; state-step vertical slice
Legacy index:

keywords: runtime, implementation, active, contract, transcript, graph, capabilities, projection

Parent: `260926-state-step-requirements`
Related: `260926-state-step-contract-spike`; `260926-state-experiment-harness`; `260926-state-experiment-plan-tools`; `260927-state-step-history-projections`; `260928-state-user-control-turn-lifecycle`

# Implement The Integrated State-Step Alpha Loop

Implement a local, user-stepped state workflow through TOAS's normal runtime, durable history, model invocation, and capability paths, while keeping state-step semantics independent from conversation-step.

## Current Reality

The existing local `step` path in `cli_session_commands.run_step` reads the
editable session transcript, constructs conversation lineage, calls the
conversation runtime, and persists message events plus model-call and
message-linked tool records. `GenerationRunner` and
`resolve_model_invocation` provide reusable provider/config/request services.
The default tool lane accepts a normalized batch and executes it sequentially
through `tools_cluster`; tool requests/results currently correlate to message
IDs. `graph.py` already stores non-message control and tool records, but has no
state-step record family or query/projection path.

The current transcript parser and step semantics are message-oriented. State
and state-diff turns must remain typed state-step records, not message events.
The human-edited transcript determines the current working state; durable
records preserve history but cannot overwrite a user's current edit.

## Desired Reality

An operator can seed an initial state, edit it to define a goal and initial
observation, and use the normal `step` affordance to advance an integrated
state-step workflow:

1. Inference receives a state-only packet containing effective instructions
   and schema, the selected current state, and one latest compound observation.
   Instructions advertise the available TOAS batch-tool lane and explain its
   alignment with state-step. The model response uses the JSON lane and carries
   a state patch plus a batch of tool requests, or a terminal outcome.
2. The runtime validates and applies an accepted patch immediately, preserving
   the current user-edited state as the operational authority, and records the
   requested batch as pending without executing it during inference.
3. A subsequent explicit `step` advances the pending batch through existing
   TOAS capability and permission checks. Tool outcomes are recorded and become
   components of the next compound observation.
4. USER/CONTROL turns retain their normal editable transcript and execution
   lifecycle. With a state horizon, eligible user material and embedded
   results enter the next state inference as observations; the state packet
   replaces transcript projection only at inference time. The workflow then
   repeats without a hidden execute-and-infer loop.

The initial human-facing state formats are configured YAML and Markdown state
DSL, both parsing to and rendering from a normalized JSON state representation.
State, state-diff, observation, transition, tool request, and tool result facts
remain distinct from message-event numbering. The model's default packet stays
state-only regardless of the user-facing transcript projection.

## Runtime Mapping And Ownership

- **Surface and operator entry:** `operator_api.step_once` and
  `cli_session_commands.run_step` are the current local entry points. Add a
  typed state-step route at the operator/runtime seam; keep CLI and daemon
  adapters thin. Do not make conversation-step parse state turns as messages.
- **Editable transcript and projection:** transcript/session-file edges own
  reading and writing the user's working transcript. Add focused typed-turn
  parsing/rendering for state and state-diff turns and the initial YAML and
  Markdown encodings. Editing the current state changes the working projection
  and creates history when stepped; no journal-tip reducer may silently replace
  that edit. Advanced key-state and cumulative-diff selection is out of scope.
- **State-step consequence selection:** give state-step its own runtime phase
  selection for “request inference” versus “run pending batch.” Reuse the
  existing model invocation services, but build the request from the selected
  state and one compound observation rather than `shape_messages_for_packet`
  over message lineage.
- **Durable State:** `graph.py` and focused graph helpers own append/query of
  typed state-step records. Existing `tool_request` and `tool_result` writers
  are correlated by message ID, so the implementation must preserve tool
  provenance against the state transition without fabricating a message event.
  Choose the smallest record envelopes that support current-state projection,
  pending-batch recovery, and linking tool outcomes to the proposal that
  requested them. Do not make the event journal operationally authoritative
  over the user-edited transcript.
- **Model Invocation:** `GenerationRunner` and
  `resolve_model_invocation` own provider settings, retries, normalization, and
  model-call audit today. Reuse these services through an explicit state packet
  boundary and retain the requested/returned model distinction in call evidence.
- **Capabilities:** normalize the JSON batch and pass it through existing
  capability validation, permissions, execution, cancellation/failure handling,
  and result rendering. Never execute proposed external calls as part of
  inference. Local own-state/observation operations may be considered only if
  required for the minimal loop; reference selectors and general state-edit
  tools remain follow-on work.
- **Authority and recovery:** preserve accepted state when a tool fails. Repeated
  steps must not silently duplicate completed side effects; an interrupted
  external action with unknown outcome must not be automatically retried.

## Refinement Allowed During Implementation

Use the contract parent, the dated contract recommendation, experiment traces,
the paper, and existing TOAS precedent to settle details as their owning seams
become concrete. The task does not require a fully specified record schema or
patch grammar before implementation starts. Record choices and rationale here
and in focused tests as they are made. At minimum, settle:

- typed state-turn markers and the minimal round-trip representation for YAML
  and Markdown;
- minimal state, observation, transition, and pending/running/completed tool
  record envelopes and their correlation/provenance;
- JSON response fields, validation, sparse-patch behavior, and terminal outcome;
- exact `step` phase behavior and recovery/idempotency boundaries;
- how the initial seed and effective instructions/schema are resolved without
  hiding runtime policy in prompt assets.

Do not reopen settled semantics without evidence: state-step is separate from
conversation-step; the operator-controlled transcript is authoritative for
current working state; the default LLM packet contains one latest compound
observation; a valid patch applies before any proposed batch runs; and tools
run only on a later explicit step through existing permissions.

## Acceptance Criteria

- A fresh local state-step can be seeded, edited to add a goal and observation,
  and stepped into inference without creating state turns as message events.
- The model request contains effective state instructions/schema, a tool
  advertisement and alignment blurb, the current state, and one latest
  compound observation; it does not include accumulated prior observations by
  default.
- A valid JSON response applies its patch and records its multi-call proposal
  as pending. Invalid responses produce an actionable failure without
  overwriting the accepted state.
- A later explicit step executes the pending calls using the existing
  capability and permission behavior. Success, failure, cancellation, and
  indeterminate outcomes are associated with the requesting transition;
  results appear in the next compound observation, and accepted state is not
  rolled back.
- The operator can edit state and observation between steps. YAML and Markdown
  state representations round-trip through normalized JSON for the supported
  slice, while message-event numbering and existing conversation-step behavior
  remain unchanged.
- Restart/re-step behavior does not silently repeat a completed side effect or
  automatically retry an unknown external outcome.
- Focused tests cover parser/render round-trips, durable append/query,
  state-only request construction, response validation/patch application,
  phase transitions, tool provenance and execution, failure/recovery, and
  ordinary conversation compatibility.
- Runtime semantics live in focused runtime/graph/capability owners; CLI and
  transport code remain adapters. No parallel disposable harness is introduced.

## Allowed Write Surfaces

- Focused state-step runtime, graph, transcript/projection, prompt/request, and
  capability integration modules required by the local alpha path.
- Focused tests for the acceptance criteria above.
- This task, its requirements parent, the state-step contract recommendation
  only when implementation evidence corrects it, and generated workboard
  sections.

## Exclusions

- Provider-native tool-call lane or default-lane redesign.
- Model-specific capability profiling or benchmark selection.
- Observation-reference addressing, marker/word-count selectors, or
  awk/sed-like state operations.
- Advanced user-facing projections such as key-state selection and cumulative
  diff views.
- General seed catalogs, arbitrary grammar configuration, dynamic instruction
  mutation, RPC/async/Vim transport support, or a general SWE state schema.
- Replaying state diffs to reconstruct snapshots or rewriting descendant
  parentage when an earlier state is edited.

## Completion Evidence

- Focused tests and full verification required by the implementation slice pass.
- A local end-to-end trace demonstrates seed/edit -> inference -> accepted
  state plus pending batch -> explicit execution -> compound observation with
  tool outcomes -> next inference, and confirms that no message events were
  fabricated for state turns.
- The parent and workboard reflect implementation evidence and any remaining
  follow-ons.

## Implementation Decisions (2026-09-27)

- Typed editable turns use `## TOAS:STATE/1` for a full state and
  `## TOAS:STATE-DIFF/1` for a sparse patch. YAML is the plain form; Markdown
  uses the same normalized YAML body in a fenced block. The parser selects the
  latest state turn, keeps surrounding conversation text intact, and regular
  `step` routes state semantics only when the transcript frontier is a typed
  state turn.
- `toas state-seed [--yaml|--markdown]` appends an initial state with a blank
  goal, preserving existing conversation content. A second seed is rejected
  when a typed state turn already exists.
- Inference replies have `state_patch` (object), `tool_calls` (array of
  `{tool_name, args}` objects), and optional `outcome` (`continue` or
  `complete`). Recursive sparse merge accepts patches immediately; `null`
  deletes a key. A terminal outcome cannot include calls.
- The minimum durable family is `state_transition`, `state_diff`,
  `state_snapshot`, `state_observation`, `state_tool_request`, and
  `state_tool_result`. These records use transition IDs and never consume
  message-event IDs. Model-call evidence stays on the transition and preserves
  requested and returned model identities.
- The request boundary supplies effective instructions, response shape, the
  runtime registry tool advertisement, current state, and one compound
  observation. Generation uses the normal provider resolution/retry/audit
  service with explicit request messages, bypassing conversation projection.
- The state-step projection formula is documented in `docs/llm-notes.md`. A
  rejected response now leaves a failed transition with the exact request
  packet, raw response when available, model-call evidence, and validation
  error, so malformed generations remain diagnosable.
- `toas step --preview` reads the current typed state turn and prints the same
  `request_messages` used for inference without calling a model or advancing
  state-step. It reports the phase when the next step would execute tools or
  stop at a terminal state.
- A pending transition runs only on a later `step`. It is marked `running`
  before capability execution; if a later step finds it still running, it
  records `indeterminate` and does not retry. Failed, cancelled, and
  indeterminate capability outcomes retain accepted state and transition
  provenance. The next inference combines the operator observation with those
  results.

## Verification Record

- Follow-on `260927-state-step-history-projections` addresses the user-facing
  state-history views considered by the contract. Its first slice appends
  successive full state turns (states-only) instead of replacing the current
  frontier; the other four selectable projections remain follow-on work.

- The state runtime and CLI route have focused coverage for parser/render
  round-trips, record separation, sparse patching, state-only request
  construction, terminal outcomes, tool execution, failure recovery, and
  ordinary transcript preservation.
- A local injected-model trace seeds and edits state, accepts a patch and
  pending batch, executes the real TOAS `echo` capability on a later step, and
  presents the result to the following inference; no message events are
  fabricated.
- Full-suite verification remains open: sandbox restrictions prevent local
  `uv` subprocess cache access and socket binding. The run reached 3,299
  passing tests and 27 failures, mostly in those restricted smoke/integration
  paths; two legacy `experiments/state_execution.py` assertions also fail and
  are outside this task's production runtime surface.

Claimed for implementation on 2026-09-27.

Status: Active.
