# State-transition step contract spike

Status: recommendation from bounded source investigation, updated with the
user's input-boundary decision; production contract and exact envelope syntax
remain unapproved.

Parent: [`260926-state-step-requirements`](../open/260926-state-step-requirements.md)
Task: [`260926-state-step-contract-spike`](../closed/260926-state-step-contract-spike.md)

## Finding

TOAS already has a clean conceptual split between transcript reconciliation,
operator consequence selection, model invocation, capabilities, durable state,
and transport. The same `step` operation should inspect its assembled session
input and recognize state mode only when a self-identifying state envelope is
at the beginning. This keeps one operator and makes the buffer itself reveal
that it is not an ordinary transcript. The recognized envelope routes to a
distinct typed input before transcript parsing. It should reuse model
configuration and capability execution, while keeping state transitions and
observations out of message numbering. State-shaped text later in an ordinary
transcript remains ordinary content; it does not switch modes.

This is a recommended first contract, not an adopted parser grammar or approval
to change production behavior.

## Status ledger

| Behavior/claim | Status |
| --- | --- |
| Local `step` reads and reconciles `session.md` before choosing a consequence | Existing behavior |
| Existing generation projects message lineage, strips control/reasoning, may add lens artifacts, then invokes the provider | Existing behavior |
| Transcript LCP, assistant callable extraction, and immediate consequence execution must not classify state input | Inferred boundary from current ownership and message semantics |
| The same `step` operation detects an explicit versioned state marker at the start of assembled session input, then dispatches before transcript parsing | User decision; exact marker/envelope grammar remains a recommendation |
| A missing state marker means existing ordinary transcript handling; unknown or malformed leading state markers fail closed | Recommended parser behavior |
| User-editable state supports YAML and a Markdown state DSL as initial configured formats, with parse/render round-tripping through canonical JSON | User decision; exact grammars and format setting remain open |
| State inference receives one user-role message containing procedure, state, and latest observation | Deliberate TOAS adaptation informed by the isolated-context experiment; not a general paper requirement |
| Apply a valid state patch before attempting its action | Paper-specified ordering; separate inference and execution calls are a TOAS interaction adaptation |
| Accept and persist a valid state patch immediately; action execution remains a separate explicit decision | User decision; state edits are still append-only branches |
| Identical resubmission is idempotent; interrupted external action is unknown and not retried automatically | Inferred safety contract for repeatability and non-duplicated side effects |
| The first state slice is local-only until a typed transport contract exists | Deliberate TOAS adaptation to current RPC/async payload limits |

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

## Input and request examples — Candidate TOAS adaptation

These are contract examples, not literal syntax. The normal transcript example
is a fresh lineage; an established ordinary session keeps its existing
projected history behavior.

Ordinary `session.md`:

```text
## TOAS:USER

Inspect src/math.py and explain how add works.
```

Normal model input for this fresh lineage:

```json
[{"role":"user","content":"Inspect src/math.py and explain how add works."}]
```

Candidate self-identifying state envelope in the same `session.md` buffer,
shown in three equivalent illustrative encodings. The human-facing buffer
syntax and the model-facing request format are separate choices.

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
buffer formats. Since the user can rewrite the projected state, each format
needs a parser back to canonical JSON and a renderer from canonical JSON;
this is a round-trip contract, not just a one-way display. The format is
identified by the envelope/configuration so parsing never guesses from body
content. Exact grammars and the setting that chooses the format remain open.

The proposed marker is a single exact first nonblank line, followed by one
versioned body encoding. The exact marker, whitespace rules, and whether stdin
can supply the envelope are still for review. `step`
reads and assembles its usual input first, then classifies it: an ordinary transcript proceeds
unchanged; the exact supported state marker selects the state parser; an
unknown or malformed leading `## TOAS:STATE...` marker is an error, never a
fallback to transcript parsing. State input cannot be mixed with role-marked
transcript blocks. Marker-like content later in ordinary content cannot
select state mode and remains subject to the existing transcript marker rules.

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

For this example, the exact application-boundary request for isolated
inference is one user message containing the selected procedure, schema
guidance, current state, and latest observation:

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

The user-controlled buffer is an editable projection. The append-only event
history remains canonical. Use transition IDs and state digests that are
independent of message IDs and message numbering.

1. **Infer:** validate the envelope, base identity/digest, instruction
   revision, and observation identity. Build the isolated user-only request;
   preserve the normal resolved provider/model settings and base-head policy.
2. **Record proposal:** after validating the model output, append one
   `state_transition` fact containing transition ID, parent transition/base
   digest, submitted input digest, instruction ref/digest, accepted state
   snapshot and patch, proposed normalized action or terminal outcome, and
   inference-call reference. Persist the call independently with a
   `transition_id` reference; do not fabricate an assistant message just to
   satisfy current message-linked `llm_call` storage.
3. **Execute:** return the pending action for review. A separate explicit
   execute operation names its `transition_id`; it runs that immutable,
   validated action through existing capability validation, grants, workspace
   restrictions, and executor. Record an append-only action-start fact before
   invoking it, followed by success/failure result facts and the captured
   observation. Do not execute arbitrary commands found in state text.
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

Minimum record family: `state_transition` for accepted snapshot/proposal;
`state_action` (or equivalent start/result records) for explicit approval,
execution identity, and outcome; and an `llm_call` linked by transition ID. A
user observation must be captured in the submitted transition input; tool
observations belong to the action outcome. Add typed append/query/replay helpers
under `graph.py` and focused `graph_*_edges.py` modules. Do not overload message
events or current message-linked `tool_request`/`tool_result` semantics with
state transition IDs.

## Continuation, edits, and interruption cases — Recommended TOAS adaptation

| Case | Contract result |
| --- | --- |
| Empty continuation with pending proposal | Show/retain that proposal. It is not approval and does not execute or infer again. |
| Empty continuation with no pending observation | No new inference; report that explicit input/operation is needed. |
| Identical resubmission | Key by base transition/digest, observation ID and content digest, instruction digest, submitted input digest, and operation. Return the existing result instead of generating or executing a duplicate. A deliberate new inference requires a new explicit attempt identity. |
| Edited prior state | Accept only against an explicit known base; append a new branch/input digest. Keep the earlier proposal immutable. An execute request names the exact proposal ID it approves. |
| Missing/invalid consequence (`no action`) | Reject as malformed; preserve accepted state and do not execute. A valid no-tool completion must be an explicit `finish` consequence. |
| Tool failure with known result | Preserve accepted state; append failure outcome and expose it as a new observation. A retry requires a new explicit proposal/approval. |
| Interruption after action-start, before result | Surface outcome as unknown and block automatic retry. Reconcile with the tool/workspace first; append a resolution fact. Exactly-once effects cannot be promised for arbitrary external tools. |
| Malformed/mixed input | If an explicit state marker/mode is selected, invalid version, missing base, or mixed transcript/state content is a hard error. Never fall back to transcript parsing or callable extraction. |
| Finish/no action | Append terminal transition with state snapshot and no pending action. |

The identity rule prevents an unchanged buffer from ambiguously meaning “retry
the model,” “execute again,” or “continue.” The first slice should expose
separate `infer` and `execute <transition_id>` operations. Do not infer approval
from an empty submission.

## Ownership and transport recommendation

| Concern | Owner |
| --- | --- |
| Envelope parsing, state schema, patch merge/validation, request assembly | New focused `runtime/state_transition_input.py` (Model Invocation boundary supplies the isolated request) |
| Select infer vs execute consequence and pending/terminal lifecycle | New focused `runtime/state_transition_runtime.py` (Operator Semantics) |
| Append/query/replay transition and action facts | `graph.py` plus focused graph writer/query helpers (Durable State) |
| Resolve tool/action, grants, scope, and execution | Existing Capabilities and Effective Policy/Authority; only pass normalized requests |
| Provider selection/retries/audit | Existing Model Invocation; extend the call reference for transition identity |
| CLI, operator, daemon/RPC adapters | Thin adapters only; same `step` operation carries/reads the buffer and performs identical detection, or refuses unsupported state input |

For a first slice, retain the `operator_api.step_once` / `toas step` entry
point. After the normal input buffer is read and assembled, classify its
leading discriminator before ordinary transcript parsing and branch to the
state runtime. Leave ordinary transcript handling untouched. Do not route
recognized state input through transcript LCP, assistant YAML extraction, or
`_working_with_transcript_tail_frontier`.

The CLI currently routes ordinary unqualified `step` over RPC when configured;
RPC exposes async step operations, while the in-process operator API wraps the
local synchronous command. Async workers force `TOAS_RPC_MODE=off` internally
but still run transcript semantics. Any route that can read the same buffer
must use identical detection. Until RPC/async can do so, reject a detected
state envelope explicitly; never silently pass it to ordinary transcript
semantics. Existing default/auto/on/off transcript contracts remain unchanged.

## Smallest useful implementation follow-on

Recommended first end-to-end slice: local-only explicit state input; one model
inference; one validated `read_file` action; explicit execute by transition
ID; persisted action result as next observation; second explicit inference;
terminal finish. Use a temporary workspace and scripted model responses first.
This proves isolation, branch identity, durable proposal/result facts, and
reuse of one existing capability without committing to arbitrary command
execution or editor support.

Focused test plan (not run in this investigation):

- parser/version/base/digest, exact schema validation, nested merge/array
  replacement/null deletion/required-field rejection;
- exact one-user-message request with no prior transcript or event-derived
  lens artifacts, while resolving the same configured target and authority
  from the explicit base head;
- existing transcript step request/output parity;
- inference does not execute; explicit action uses current capability
  validation and denial path;
- success and failure produce observations; empty and identical submissions
  are idempotent; edited input branches; interrupted action is unknown and is
  not retried;
- same-step detection selects only the leading supported state marker;
- unknown/malformed leading state markers fail closed, while ordinary
  transcript handling and marker-like content later in a message are preserved;
- RPC modes and async entry points explicitly reject an unsupported detected
  envelope rather than lowering it to transcript input.

Candidate existing coverage anchors: `tests/test_operator_api.py`,
`tests/test_runtime_context_assembly.py`,
`tests/test_model_invocation_contracts.py`,
`tests/test_runtime_session_step_edges.py`,
`tests/test_runtime_session_rotation.py`, and graph record tests. Add focused
state-transition test modules when implementation begins; do not inflate
unrelated suite coverage.

## Open decisions before user-facing adoption

- Exact marker/body grammar, whitespace handling, and whether stdin can carry
  the state envelope. The user has decided that the existing `step` operation
  inspects its input; a separate operator or mode flag is not desired.
- Whether state mode may call every currently advertised capability in the
  first slice or begins with the read-only subset.
- How a durable inference/action record is surfaced in transcript, history,
  `llm-input`, and rebuild projections without becoming a message event.
- When the typed state operation becomes supported over RPC and async paths.
- How state transition controls appear in the buffer or UI while retaining the
  same `step` operation.

No final `session.md` marker grammar, generic state ontology, automatic handoff
authoring, multi-agent coordination, or production implementation is adopted by
this spike. Use these examples to review the choices above before opening a
production implementation task.
