# State-transition step contract spike

Status: recommendation updated with the user's transcript/projection
refinement; durable record shape, turn grammar, and projection policies remain
unapproved.

Parent: [`260926-state-step-requirements`](../open/260926-state-step-requirements.md)
Task: [`260926-state-step-contract-spike`](../closed/260926-state-step-contract-spike.md)

## Finding

Keep state-step history transcript-oriented. A state step can produce a full
state turn, a state-diff turn, or a sequence alternating between them; the
ordinary user/assistant turn pattern remains available. Do not make the whole
session enter a separate state mode before transcript parsing.

The human-controlled transcript is authoritative for current working state.
The append-only event log preserves historical records; it is historically
canonical, not operationally authoritative. Replaying an older event must not
silently override a user's current transcript edit. The operator can completely
rewrite the current state in a state turn. A validated model patch is accepted
immediately. Any proposed action remains separately executable under existing
capability and authority rules.

Treat “full state plus every diff,” “states only,” “diffs only,” “key states,”
and “key states plus cumulative diffs since the prior key” as candidate
user-facing transcript views. A key state is a movable display anchor;
shifting it changes which subsequent diffs are shown, not the transcript's
authority or the model's default input. YAML and the Markdown state DSL are the initial
configured human-facing formats; both parse to and render from normalized JSON.

The default LLM projection remains state-only: effective instructions/schema,
the current state object, and one latest logical observation. The user-facing
history projection does not change that packet. Historical observations remain
available to the operator; the model does not automatically receive an
unconsumed-observation queue. A state operation can select exact text from the
compound observation by reference, place it into a state diff, and have the
runtime expand it so the next state packet contains the full text. The source
observation remains retained.

This is a recommended first contract, not an adopted parser grammar or approval
to change production behavior.

## Status ledger

| Behavior/claim | Status |
| --- | --- |
| Local `step` reads and reconciles `session.md` before choosing a consequence | Existing behavior |
| Existing generation projects message lineage, strips control/reasoning, may add lens artifacts, then invokes the provider | Existing behavior |
| State and state-diff turns are typed state-step records, not message events; they may be rendered in user-facing transcript projections | User decision |
| The human-controlled transcript is authoritative for current working state; the event log preserves history but cannot overrule transcript edits | User decision; exact edit/replay interaction remains open |
| State-step and conversation-step remain semantically independent while sharing runtime and model capabilities | User decision; convergence requires significant impetus |
| Introduce state and state-diff records and selectable user-facing projections | User decision; exact record schema and projection controls remain open |
| User-editable state supports YAML and a Markdown state DSL as initial configured formats, with parse/render round-tripping through normalized JSON | User decision; exact grammars and format setting remain open |
| Default LLM projection is effective instructions/schema + current state object + one latest logical observation | User decision aligned with the paper and inspected implementations |
| Prior observations are not automatically accumulated into the default LLM packet | User decision; explicit state operations can move selected observation content into state |
| Observation content is retained as source material; state operations need not echo it as model output text | User decision; exact operation, identity, and storage/provenance shape remain open |
| Apply a valid state patch before attempting its action | Paper-specified ordering; separate inference and execution calls are a TOAS interaction adaptation |
| Accept and persist a valid state patch immediately; action execution remains a separate explicit decision | User decision; state edits are still append-only branches |
| State snapshots, diffs, observations, and actions use shared append-only history machinery and can be rendered as transcript turns | User decision; graph/event schema remains open |
| Offer full, states-only, diffs-only, key-state, and key-state-plus-cumulative-diff user-facing projections | User-proposed projection family; key-state criteria and selection controls remain open |
| Identical resubmission is idempotent; interrupted external action is unknown and not retried automatically | Inferred safety contract for repeatability and non-duplicated side effects |
| RPC/async preserve state-step inputs and selected projections across transports | Requirement; transport implementation details remain open |

## Current runtime trace — Existing behavior

1. `cli.run_step` sends the ordinary unqualified step over RPC when configured
   (`TOAS_RPC_MODE=auto|on`); argument-bearing forms and RPC failures fall back
   to the local route. `operator_api.step_once` is an in-process facade over
   `cli_session_commands.run_step`.
2. The local command reads `session.md`, appends optional stdin/control text,
   reconstructs lineage and the bound session successor in
   `step_context_runtime.build_runtime_context`, then resolves config and
   `GenerationRunner`.
3. `step_runtime._build_run_step_frontier_context` aligns parsed transcript
   nodes with message lineage using LCP/bind rules. `_execute_frontier_consequences`
   classifies the last user/control/assistant frontier. User input normally
   generates an assistant response; callable assistant content may execute in
   that same invocation through the existing plan/execution path.
4. `GenerationRunner.prepare_request` calls
   `resolve_model_invocation`, which projects the working messages, builds a
   context packet, and may add durable lens artifacts. It also resolves model,
   endpoint, and target selection from config, events, and the current working
   transcript. `graph_message_edges.project_llm_input_from_messages` removes
   control-role messages, strips assistant reasoning blocks, and merges
   adjacent user messages. `llm.py` may then lower the messages to
   `single_user_blob`.
5. `persist_step_outputs_runtime` writes message events and attached `llm_call`
   records, then stitches message-linked `tool_request`/`tool_result` records,
   applies result side effects, seals storage if configured, and projects output.

Relevant owners: `operator_api.step_once`; `cli_session_commands.run_step`;
`runtime/step_runtime.py`; `runtime/step_generation_runtime.py`;
`runtime/model_invocation_contracts.py`; `runtime/context_assembly.py`;
`runtime/session_step_edges.py`; `runtime/step_result_runtime.py`; `graph.py`;
`tools_cluster/`. See [runtime ownership](../../docs/runtime-ownership.md).

## Transcript turns, state projections, and request examples — Candidate TOAS adaptation

These are contract examples, not literal syntax. The normal transcript example
is a fresh lineage; an established session continues to be a transcript. The
state examples below are typed turns within that transcript, not a separate
whole-buffer input mode.

Ordinary `session.md`:

```text
## TOAS:USER

Inspect src/math.py and explain how add works.
```

Normal model input for this fresh lineage:

```json
[{"role":"user","content":"Inspect src/math.py and explain how add works."}]
```

Candidate state turn in a transcript. It may occur between ordinary turns or
other state turns. Its body is shown in equivalent illustrative encodings;
the human-facing projection and model-facing request format are separate.

YAML body:

```yaml
## TOAS:STATE/1

kind: toas.state-transition
version: 1
operation: infer
format: yaml
seed_ref: state-seeds/repo-work_v1
base:
  message_head_id: m42
  transition_id: st7
  state_digest: sha256:...
instructions:
  ref: repo-work/v1
  digest: sha256:...
state:
  goal: Understand the add implementation
  progress: []
  next_steps:
    - Read src/math.py
  artifacts: []
  blockers: []
  notes:
    constraints: []
    accepted_decisions: []
    pending_proposals: []
    uncertainties: []
observation:
  id: obs8
  kind: user_input
  content: Inspect src/math.py and explain how add works.
```

Comparable Markdown-based state DSL:

```markdown
## TOAS:STATE/1

### Request
- kind: `toas.state-transition`
- version: 1
- operation: infer
- format: markdown
- seed ref: `state-seeds/repo-work_v1`

### Base
- message head: `m42`
- transition: `st7`
- state digest: `sha256:...`

### Instructions
- ref: `repo-work/v1`
- digest: `sha256:...`

### State
- goal: Understand the add implementation
- progress: (empty)
- next steps:
  - Read `src/math.py`
- artifacts: (empty)
- blockers: (empty)

#### Notes
- constraints: (empty)
- accepted decisions: (empty)
- pending proposals: (empty)
- uncertainties: (empty)

### Observation `obs8` — `user_input`
> Inspect src/math.py and explain how add works.
```

JSON can remain the normalized application/model request even if the editable
buffer uses YAML or the Markdown DSL. Keeping those boundaries separate lets
the user-facing projection favor readability without constraining the model's
wire format.

Equivalent normalized JSON body (not a requirement for the editable buffer):

```json
{
  "kind": "toas.state-transition",
  "version": 1,
  "operation": "infer",
  "base": {
    "message_head_id": "m42",
    "transition_id": "st7",
    "state_digest": "sha256:..."
  },
  "instructions": {"ref": "repo-work/v1", "digest": "sha256:..."},
  "state": {
    "goal": "Understand the add implementation",
    "progress": [],
    "next_steps": ["Read src/math.py"],
    "artifacts": [],
    "blockers": [],
    "notes": {
      "constraints": [],
      "accepted_decisions": [],
      "pending_proposals": [],
      "uncertainties": []
    }
  },
  "observation": {
    "id": "obs8",
    "kind": "user_input",
    "content": "Inspect src/math.py and explain how add works."
  }
}
```

Both YAML and the Markdown DSL should be supported as initial configured
buffer formats. Since the user can rewrite the state turn, each format needs a
parser to normalized JSON and a renderer from normalized JSON;
this is a round-trip contract, not just a one-way display. The format is
identified by the envelope/configuration so parsing never guesses from body
content. Exact grammars and the setting that chooses the format remain open.

Here `## TOAS:STATE/1` illustrates a typed state-step record header, not a
whole-document mode switch. A corresponding versioned state-diff record carries
a patch or transition delta. State and state-diff records are not message
events. They remain semantically independent from conversation-step; the two
may share runtime services and model capabilities, but convergence needs a
significant impetus. User-facing state-step projections render their own state
and state-diff records without merging them into conversation-step semantics.
Exact record schema and turn markers remain open. Unknown versions
should fail clearly without reinterpreting prior history. The operator-facing
view follows the current user-controlled state; historical records do not
replace or overrule it. The LLM request applies its own projection policy.

Candidate user-facing projections over the current transcript and its retained history:

| Projection | Rendered sequence |
| --- | --- |
| Full states and diffs | `state0, diff0→1, state1, diff1→2, state2, ...` |
| States only | `state0, state1, state2, ...` |
| Diffs only | `diff0→1, diff1→2, ...` |
| Key states | `state0, state4, state7, ...` |
| Key states with cumulative diffs | `state0, diffs0→4, state4, diffs4→7, state7, ...` |

The user-facing view can change without rewriting historical records. The
view must still honor the operator's current transcript edits. Key-state
criteria, whether keys are explicit or computed, and how users select/switch
projections remain open.

These are user-facing projection choices. They do not change the default LLM
packet described below: the model still gets effective instructions/schema,
the current transcript state object, and one latest logical observation.

### Latest-observation evidence

The primary paper defines each request as procedure, current state, and the
latest environment observation, and explicitly excludes previous observations
from later calls ([SKILL.state, §3 and Algorithm 1](../../docs/references/skill-state/paper.md)).
The checked [Pi implementation](https://github.com/toadharvard/pi-skill-state-runtime)
maps the observation to the newest user input or latest external tool-result
batch; the tool-result batch becomes the next and only observation. Its
observation character cap is optional and defaults to retaining the full latest
observation. The [minimal implementation](https://github.com/kissishka/skill-state-minimal)
also accepts one observation per `step()` and sets no hard size limit. The
[skillstate implementation](https://github.com/vitkuz573/skillstate) describes
the same P/state/latest-observation packet.

This supports one latest logical observation as the default, not an implicit
queue of all unconsumed observations. It does not prescribe a hard size cap;
the paper's prompt-size expression still includes observation size. TOAS should
retain original observations for operator inspection and only include the
selected latest observation in the ordinary state-only packet. The precise
definition of a logical observation when multiple user/tool events arrive
before inference remains open.

### Observation-to-state operations — Candidate TOAS adaptation

Let the agent select any text in the compound observation and place it into a
state diff by reference, without emitting the text again. The runtime resolves
the reference while applying the diff, so the next state packet contains the
full text. Keep the source observation available and retain provenance from
the inserted state value back to its source. This saves completion/write
tokens; it does not erase the cost of reading the text, and the full value may
increase future state-packet input.

The observation is addressable as a tree: a path selects a higher-level
component, then a familiar text selector can identify a span within it. Paths,
markers, word counts, and awk/sed-like selectors are candidates to explore;
the exact addressing syntax and ambiguity behavior remain open. Runtime byte
offsets are an implementation detail, not an agent-facing requirement.

Keep state-local operations permission-free when they only transform state or
material already supplied in the observation. Operations that inspect the
external environment use existing observational/read capabilities and their
permissions. Operations that change the environment use existing write or
execution capabilities and their permissions. Model-fit profiles may narrow
which available capabilities are advertised, but do not change authorization.

The state operation's schema/path restrictions and provenance shape remain
open. Whether it supports only exact spans initially or also more complex
extraction is a follow-on question.

Example state-diff turn in the Markdown DSL:

```markdown
## TOAS:STATE_DIFF/1

### Transition
- id: st8
- parent: st7
- base digest: `sha256:...`
- status: accepted

### Patch
- progress:
  - Read src/math.py; add returns a + b.
- next_steps: (empty)

### Consequence
- kind: action
- tool: read_file
- path: src/math.py
```

The YAML DSL would carry the same transition, patch, and consequence fields.
The accepted full state can be rendered as the next state turn or reconstructed
from the prior state plus this diff; which form the durable log stores is open.

### Initial state seed — Candidate TOAS adaptation

An initial state request has no prior transition base. It names the seed asset
and editable-buffer format explicitly:

```markdown
## TOAS:STATE/1

### Request
- kind: toas.state-transition
- version: 1
- operation: initialize
- format: markdown
- seed_ref: state-seeds/repo-work_v1

### Observation obs1 — user_input
> Understand the add implementation in src/math.py.
```

For YAML, the same request body uses `format: yaml` and the equivalent
`seed_ref: state-seeds/repo-work_v1` field. Resolve `seed_ref` through the
existing versioned prompt-asset reference/loading system; require a
state-seed-specific metadata category and validate the loaded seed against the
state schema. Record the normalized ref, asset digest, and resolved seed in
the initial transition so later asset edits cannot silently change history.
The seed supplies initial state values and schema defaults; the user's
observation supplies current goal and context. Missing, wrong-category, or
invalid seed assets are hard errors. Prompt composition for model instructions
can remain a separate prompt asset reference.

The default state-only packet for this example contains the effective
procedure/schema, current state, and latest logical observation. The following
single-user-message packaging is illustrative; exact role packaging remains
open:

```json
[{"role":"user","content":"Procedure (repo-work/v1): Help inspect the requested repository file. Propose one read_file action, or finish if the goal is already met. Never claim a tool result before it is observed.\n\nResponse schema: Return exactly one JSON object with state_patch (sparse object) and consequence. consequence is either {kind: action, tool_name: read_file, arguments: {path: relative_path}} or {kind: finish}. Do not execute the action in this inference.\n\nCurrent state (base transition st7): {goal: Understand the add implementation, progress: [], next_steps: [Read src/math.py], artifacts: [], blockers: [], notes: {constraints: [], accepted_decisions: [], pending_proposals: [], uncertainties: []}}\n\nLatest observation obs8 (user_input): Inspect src/math.py and explain how add works."}]
```

For this state request, the builder must not add prior transcript messages or
history-derived lens artifacts. Model/config selection, grants, workspace
scope, and other authority inputs are resolved separately against the
explicit base head and effective configuration. Capture this message list at
the TOAS model-invocation boundary; provider-side injected prompts and any
transport re-rendering are outside that boundary and must not be mistaken for
the application request.

Candidate model response:

```json
{
  "state_patch": {"progress": ["Read src/math.py; add returns a + b."], "next_steps": []},
  "consequence": {"kind": "action", "tool_name": "read_file", "arguments": {"path": "src/math.py"}}
}
```

An alternative terminal response is
`{"state_patch":{"progress":["Goal answered."],"next_steps":[]},"consequence":{"kind":"finish"}}`.
The response is one validated JSON object: exactly one action or terminal
consequence, never both. A patch alone must not cause execution.

Expected durable facts for the action example, expressed as candidate records:

```jsonl
{"kind":"state_transition","payload":{"transition_id":"st8","parent_transition_id":"st7","base_state_digest":"sha256:...","input_digest":"sha256:...","format":"markdown","seed_ref":"state-seeds/repo-work_v1","seed_digest":"sha256:...","observation_id":"obs8","instruction_ref":"repo-work/v1","instruction_digest":"sha256:...","state_patch":{"progress":["Read src/math.py; add returns a + b."],"next_steps":[]},"state_after":{"goal":"Understand the add implementation","progress":["Read src/math.py; add returns a + b."],"next_steps":[],"artifacts":[],"blockers":[],"notes":{"constraints":[],"accepted_decisions":[],"pending_proposals":[],"uncertainties":[]}},"consequence":{"kind":"action","tool_name":"read_file","arguments":{"path":"src/math.py"}},"patch_status":"accepted","action_status":"awaiting_approval"}}
{"kind":"llm_call","payload":{"transition_id":"st8","requested_model":"...","response_model":"...","usage":{}}}
{"kind":"state_action","payload":{"attempt_id":"act1","transition_id":"st8","status":"started","request_digest":"sha256:..."}}
{"kind":"state_action","payload":{"attempt_id":"act1","transition_id":"st8","status":"succeeded","observation_id":"obs9","observation":{"kind":"tool_result","content":"def add(a, b): return a + b"}}}
```

These event kinds/shapes are proposed, not existing graph record contracts.
Patch acceptance is recorded immediately with the transition. Any action
approval and action-start are separate durable facts; the operation result is
the next observation, not a message event.

## State and patch semantics — Recommended TOAS adaptation

Recommended first schema: required top-level `goal`, `progress`, `next_steps`,
`artifacts`, `blockers`, and `notes`. `notes` has the experiment's four named
arrays. Enforce object/array/string types and bounded serialized size before
accepting a transition. Reject unknown top-level fields in version 1 so typos
do not silently become state. This is deliberately smaller than a general SWE
state schema.

| Patch | Result |
| --- | --- |
| `{"notes":{"uncertainties":["Need inspect call sites"]}}` | Recursively merge the nested object; retain other note arrays |
| `{"next_steps":["Read tests"]}` | Replace the complete array |
| `{"artifacts":null}` | Attempt to delete a required field; full validation rejects the candidate |
| `{"notes":{"accepted_decisions":null}}` | Attempt to delete a required nested array; full validation rejects the candidate |
| `{"goal":17}` or malformed JSON | Reject; preserve the last accepted state and do not run the consequence |

Adopt recursive mapping merge, scalar/array replacement, and null deletion;
validate the whole candidate state after merge. Keep a patch and the resulting
snapshot for replay/audit. Invalid output creates an error observation but does
not mutate the accepted snapshot. Do not automatically ask the model to repair
schema output inside the same operator call; a correction is a new explicit
inference.

## Transition lifecycle and durable facts

The current transcript is the operator-controlled working surface, not merely
a projection of historical records. The append-only event log records what
was previously submitted or executed; it does not decide current working
state. State snapshots and diffs may carry stable IDs and digests as typed
state-step records, separate from message events. User edits that
replace a full state change the working transcript while prior records remain
historical; no replay may silently reinstate the old state.

1. **Infer:** select the latest state and observation turns under the active
   projection, validate their schema/base/digests, and build the model request.
   The projection may be a single isolated user message or a role-preserving
   transcript; this is an explicit projection choice. Preserve normal
   provider/model settings and effective authority.
2. **Record accepted transition:** after validating model output, append the
   state diff and resulting full state snapshot immediately, with stable IDs,
   parent/base digest, input digest, seed/instruction refs and digests, and
   inference-call reference. Append the proposed action/terminal consequence
   as part of that result. Invalid output emits an error/observation and does
   not advance accepted state. Exact record/event shape remains open.
3. **Execute:** return the pending action for review. A separate explicit
   execute operation names its transition; it runs that immutable, validated
   action through existing capability validation, grants, workspace
   restrictions, and executor. Record append-only action-start and
   success/failure outcome facts with the captured observation. Do not execute
   arbitrary commands found in state text.
4. **Continue:** the next inference names the action result as its latest
   observation. One call performs one inference or one explicit action
   execution, never a hidden execute-and-infer loop.

The proposed state patch is accepted and promoted when the validated model
response is recorded, before its action runs. There is no separate
accept/reject step for a valid state patch. A failed action does not roll back
that state; its failure becomes the next observation. The paper specifies patch-before-action
ordering; keeping inference and execution as separate explicit calls is a TOAS
interaction adaptation that retains review time. Rejected/invalid proposals do
not advance state. User edits make a new input branch from a named base; they do
not rewrite prior transition facts.

Candidate record family: state snapshot/diff turns or equivalent typed log
records; action-start/outcome records; and an `llm_call` linked to the
transition. A user observation is a transcript turn; tool observations belong
to the action outcome and can also be projected as turns. Extend append,
query, replay, and projection helpers under `graph.py` and focused
`graph_*_edges.py` modules. Keep the exact relationship to existing
message-linked `tool_request`/`tool_result` records open for the contract spike.

## Continuation, edits, and interruption cases — Recommended TOAS adaptation

| Case | Contract result |
| --- | --- |
| Empty continuation with pending proposal | Show/retain that proposal. It is not approval and does not execute or infer again. |
| Empty continuation with no pending observation | No new inference; report that explicit input/operation is needed. |
| Identical resubmission | Key by base transition/digest, observation ID and content digest, instruction digest, submitted input digest, and operation. Return the existing result instead of generating or executing a duplicate. A deliberate new inference requires a new explicit attempt identity. |
| Edited prior state | Accept only against an explicit known base; append a new branch/input digest. Keep earlier transition facts immutable. The user's complete rewrite is a new state turn/snapshot, not a patch to old history. An execute request names the exact proposal ID it approves. |
| Missing/invalid consequence (`no action`) | Reject as malformed; preserve accepted state and do not execute. A valid no-tool completion must be an explicit `finish` consequence. |
| Tool failure with known result | Preserve accepted state; append failure outcome and expose it as a new observation. A retry requires a new explicit proposal/approval. |
| Interruption after action-start, before result | Surface outcome as unknown and block automatic retry. Reconcile with the tool/workspace first; append a resolution fact. Exactly-once effects cannot be promised for arbitrary external tools. |
| Malformed state turn | Reject invalid version/schema/base clearly; preserve prior events and do not reinterpret the rest of the transcript as a different mode. |
| Finish/no action | Append terminal transition with state snapshot and no pending action. |

The identity rule prevents an unchanged buffer from ambiguously meaning “retry
the model,” “execute again,” or “continue.” The first slice should expose
separate `infer` and `execute <transition_id>` operations. Do not infer approval
from an empty submission.

## Ownership and transport recommendation

| Concern | Owner |
| --- | --- |
| State/state-diff record parsing, canonical state normalization, YAML/Markdown round-trip | Focused state-step boundary; records stay separate from message events |
| Select the state-step LLM packet and assemble the request | Model Invocation boundary plus a focused state-step input builder |
| Select infer vs execute consequence and pending/terminal lifecycle | Focused state-transition runtime (Operator Semantics) |
| Append/query state and action facts | Existing history machinery in `graph.py` plus focused graph helpers |
| Resolve tool/action, grants, scope, and execution | Existing Capabilities and Effective Policy/Authority; only pass normalized requests |
| Provider selection/retries/audit | Existing Model Invocation; extend the call reference for transition identity |
| CLI, operator, daemon/RPC adapters | Thin adapters; expose state-step separately from conversation-step while reusing runtime and model services |

Keep state-step semantically separate from the `operator_api.step_once` /
`toas step` conversation-step path. Parse typed state and state-diff records
through a state-step boundary, then build the configured LLM packet using
shared model/runtime capabilities. Do not route state records through ordinary
assistant callable extraction. Any future convergence needs significant
impetus.

The CLI currently routes ordinary unqualified `step` over RPC when configured;
RPC exposes async step operations, while the in-process operator API wraps the
local synchronous command. Async workers force `TOAS_RPC_MODE=off` internally
but still run transcript semantics. RPC and async routes must preserve
state-step semantics and projection selection. Existing default/auto/on/off
transport contracts remain unchanged; add a separate state-step operation over
the shared transport/runtime seams.

## Smallest useful implementation follow-on

Recommended first end-to-end slice: add typed state and state-diff records to
the state-step working transcript/history; support YAML and Markdown round-trip;
offer full state-plus-diff and states-only projections; run one inference that accepts a
patch immediately; execute one validated `read_file` action explicitly; add
the result as an observation turn; then continue inference. Use scripted model
responses first. This proves branch identity, event-log replay, projection
selection, and reuse of an existing capability without arbitrary command
execution.

Focused test plan (not run in this investigation):

- state/state-diff turn parse/render round-trip for YAML and Markdown;
- full-state rewrites append snapshots/branches without mutating prior events;
- each projection mode produces the expected sequence, including key states
  with cumulative diffs;
- model request captures the selected projection, and switching projections
  does not mutate event history;
- valid model patches append accepted state immediately; invalid patches do
  not advance state;
- inference does not execute; explicit action uses current capability
  validation and denial path;
- success/failure produce observation turns; retries are idempotent;
  interrupted actions remain unknown and are not retried;
- existing ordinary transcript step request/output parity;
- RPC modes and async entry points preserve typed-turn projection semantics.

Candidate existing coverage anchors: `tests/test_operator_api.py`,
`tests/test_runtime_context_assembly.py`,
`tests/test_model_invocation_contracts.py`,
`tests/test_runtime_session_step_edges.py`,
`tests/test_runtime_session_rotation.py`, and graph record tests. Add focused
state-transition test modules when implementation begins; do not inflate
unrelated suite coverage.

## Open decisions before user-facing adoption

- How the state-step working transcript is stored and edited while preserving
  its semantic separation from conversation-step.
- Exact typed record schema and state-step projection syntax.
- Key-state criteria and whether users can pin key states, configure rules, or
  use computed significance.
- Projection-selection controls and persistence scope (per request, session,
  or configuration).
- Whether state workflows may call every currently advertised capability in the
  first slice or begins with a smaller subset of existing environment-facing
  capabilities. State-local operations remain permission-free.
- How inference/action records appear consistently in transcript, history,
  `llm-input`, and rebuild projections across the candidate turn/log shapes.
- How the projection choice is carried over RPC and async paths.

## Deferred follow-on fragments — not ready for implementation

- **Observation addressing and state operations:** Experiment with observation
  tree paths and familiar selectors such as markers, word counts, and
  awk/sed-like addressing. The target behavior is exact text selection by
  reference, runtime expansion into the state diff, and retained source
  provenance. Decide the initial selector subset, failure behavior, and schema
  constraints after experiments.
- **Per-model capability profiles:** Build designed, on-demand benchmarks that
  measure which runtime capability forms each actually returned model handles
  best. Use results to advertise an evidence-backed subset; retain the full
  runtime capability set and existing permission checks. Record model identity
  and benchmark/runtime versions so profiles can be refreshed when they change.
- **State-step adoption details:** Define key-state selection and projection
  controls, YAML/Markdown grammar and format selection, seed assets, the initial
  environment-facing capability subset, and RPC/async support. Keep state-step
  semantically independent from conversation-step.

No final `session.md` turn grammar, generic state ontology, automatic handoff
authoring, multi-agent coordination, or production implementation is adopted by
this spike. Use these examples to review the choices above before opening a
production implementation task.
