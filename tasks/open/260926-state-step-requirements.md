Filed as: 260926-state-step-requirements
FKA:
AKA: state-transition step; SKILL.state implementation straw man; repo-work state
Legacy index:

keywords: runtime, investigation, active, contract, projection, frontier, provenance
Depends on: `260926-state-simulation-checkpoint`
Related: `260926-state-step-contract-spike`; `260926-state-experiment-harness`; `260926-state-experiment-plan-tools`; `260803-session-rotation-lifecycle`; `260927-state-step-history-projections`; `260928-state-user-control-turn-lifecycle`

# State-Transition Step: Requirements And Implementation Straw Man

Status: ACTIVE requirements parent; integrated alpha direction and runtime
ownership map recorded; focused implementation child is ready

## Objective

Develop a reviewable implementation contract for an explicitly state-shaped
working surface handled by a state-step operation integrated with TOAS runtime,
model, history, and capability services. Keep state-step semantically
independent from conversation-step. This parent owns requirements and
decisions, not production implementation.

## Inputs And Status

- [Paper](../../docs/references/skill-state/paper.md) and
  [provenance](../../docs/references/skill-state/README.md).
- [Buffer exploration](../../docs/notes/2026-09-26-state-transition-buffers.md).
- [Simulation guide](../../docs/notes/2026-09-26-state-simulation.md) and
  [checkpoint](../../docs/notes/2026-09-26-state-simulation.yaml).
- [Ownership map](../../docs/runtime-ownership.md).

Accepted direction: the user edits an initial seeded state to define the goal
and may supply initial observation material. The LLM receives a state-only
packet with effective instructions/schema, the selected horizon state, and one
compound observation. Instructions include the available TOAS batch-tool
advertisement and a state-step alignment blurb. The model returns a JSON object
with a state patch and a batch of tool requests, or a terminal outcome. The
runtime accepts and applies a valid patch immediately, records requested tools
as pending, and runs a batch only when the user steps it through existing
capability and permission paths. Tool results become components of the next
compound observation. Users may edit current state and observations between
steps. State-step and conversation-step remain independent while sharing
runtime/model capabilities. Exact response and record schemas remain open.

The checkpoint stays a dated simulation artifact. This parent records the
accepted alpha direction; it does not quietly turn that YAML into runtime
configuration.
Prior uncommitted work is the related paper intake and simulation checkpoint;
no unrelated edits were found during planning intake.

## Smallest Useful Vertical Slice (Agreed Direction)

A seed provides the initial state shape and defaults before a goal exists. The
user edits the state to add a goal and may add observations, then steps the
state-step runtime. The LLM receives the selected horizon, one compound
observation, effective instructions/schema, advertised tools, and the
alignment blurb. It returns a JSON state patch and a batch of tool requests or
a terminal outcome. The runtime applies the patch and records the pending
batch. The user may edit state/observation or step to execute the batch through
existing capabilities and permissions. Tool requests/results are recorded;
results become components of the next compound observation. The next step
continues from the resulting horizon. There is no hidden execute-and-infer loop.

This is an integrated alpha path using shared TOAS runtime and capability
services, not a parallel disposable harness. It is not a benchmark
reproduction.

## Draft Objects And Behavior

| Object | Straw-man responsibility | Decision still needed |
| --- | --- | --- |
| State-step user-facing projections | Render typed state snapshots, diffs, and observations in state-step views | Exact record schema and turn grammar; semantic separation is settled |
| Instructions | Effective state procedure/schema, available-tool advertisement, and state-step alignment blurb | Exact instruction composition and provider-message packaging |
| Current state | goal, progress, next_steps, artifacts, blockers, structured notes | Required fields, bounds, artifact shape, deletion rules |
| Compound observation | User material and batched tool results represented as addressable components | Exact component envelope and durable links; one compound observation goes to each inference |
| Model proposal | JSON state patch plus a batch of tools, or explicit terminal outcome | Exact response schema, merge and validation details |
| Transition | Identifies selected horizon, proposal, pending batch, tool outcomes, and accepted state | Durable record types, IDs, parentage, and interruption recovery |
| State-step projection | Full states/diffs, states only, diffs only, key states, or key states with cumulative diffs | Key-state criteria, selection controls, and persistence scope |

The turn and projection labels are conceptual, not adopted parser syntax. The
notes structure is accepted for the experiment, not yet a complete validator
contract. Free-form YAML must not accidentally become executable tool intent.

### State Update And Action Timing

The paper applies the patch before executing tools. A valid patch is accepted
and recorded immediately, while the proposed batch remains pending until the
user steps to execute it. Tool failures do not roll back accepted state; their
outcomes enter the next compound observation. User edits add state/observation
history rather than changing earlier records.

Tentative merge semantics: recursive mapping merge, scalar/array replacement,
null deletion, validation of the entire resulting state. These are proposed
choices for unspecified details, not confirmed author implementation. Required
fields and valid null-valued data need an explicit treatment before adoption.

### Continuation And Identity

The runtime phase determines what `step` advances: request inference when ready,
or present/run a pending batch when one is waiting. A step with no new user
text is not new evidence, a completion claim, or implicit permission for an
external effect. Preserve identity and deduplication so a repeated step cannot
silently repeat a side effect. If a tool outcome is unknown after interruption,
do not silently retry it.

State and state-diff records are not message events and state-step does not use
conversation-step's text-LCP semantics. Exact record identity and horizon
selection are implementation details to resolve without rewriting earlier
records.

## Current Code Evidence And Candidate Owners

| Observed seam | Implication for planning |
| --- | --- |
| `src/toas/runtime/step_runtime.py::_build_run_step_frontier_context` parses the conversation transcript and constructs a `ReconciliationHandoff` | Define a distinct state-step input/horizon boundary while reusing runtime services |
| `src/toas/runtime/context_assembly.py::shape_messages_for_packet` returns packet messages when no lens artifacts exist | Reuse Model Invocation services while building the state-only packet from the selected horizon and compound observation |
| `src/toas/runtime/model_invocation_contracts.py::resolve_model_invocation` resolves provider settings from working context and events | Preserve model configuration/authority independently of omitted conversational context; record user-only versus other role packaging |
| `src/toas/runtime/session_step_edges.py::persist_messages_and_llm_calls` associates model-call records with materialized messages | Decide how model-call identity links to typed state turns or event-log records |
| `src/toas/runtime/frontier_resolution.py` handles callable-plan extraction and source preservation | Reuse capability semantics through explicit normalized intent, not arbitrary state YAML scanning |
| `src/toas/operator_api.py::step_once` is the conversation-step seam | Keep adapters thin; define a distinct state-step operation while reusing runtime and model capabilities |

Candidate ownership: representation parsing in a focused state-step boundary;
horizon selection and transitions in state-step Operator Semantics; append and
query under shared Durable State (`graph.py` and focused helpers); request
construction under Model Invocation; tool execution under existing
Capabilities; state views and fresh-buffer rendering under Projection And
Rendering. Exact module additions are for runtime mapping.

Compare existing successor continuation before adding a second surface lifecycle.
Keep daemon/host/Vim as adapters. The first local slice must not silently route
state buffers through unsupported RPC transcript semantics; follow-on planning
must name capability detection, explicit refusal, or supported routing.

## Acceptance Matrix For The Eventual Slice

| Scenario | Required observable result |
| --- | --- |
| Ordinary transcript input | Existing alignment, authority, history and stdout behavior preserved |
| State/state-diff records | Appended and viewed in state-step history, distinct from conversation message events |
| LLM packet | Uses selected horizon, one compound observation, effective instructions/schema, tool advertisement, and alignment blurb |
| Sparse patch | Unchanged fields survive; nested merge, array replacement and deletion match the chosen contract |
| Invalid output | Prior accepted state unchanged; actionable error; retries bounded and observable |
| Model proposal | JSON object contains state patch plus a multi-tool batch, or a terminal outcome |
| Pending batch | Patch is applied immediately; proposed tools are recorded but not run during inference |
| Batch execution | User steps the runtime; calls pass through existing capabilities and permissions |
| Success/failure/cancellation | Preserve completed results, record outcomes, and include batch results in the next compound observation; accepted state is not rolled back |
| Re-step/restart/edited base | No duplicate side effect; recoverable state and explicit predecessor semantics |
| Empty continuation | Can advance eligible next work; does not invent results or approve pending decisions |
| User-only engine | Same logical projection content boundary; role placement recorded as an experimental variable |

## Sequence And Handoff

The [experimental harness](../closed/260926-state-experiment-harness.md) and
[tool-plan follow-on](../closed/260926-state-experiment-plan-tools.md) are
completed evidence. They do not define the integrated alpha behavior. The user
has now recorded that alpha should use the normal TOAS runtime/history/model/
capability path, not a parallel experimental harness.

1. **Recorded direction:** integrated state-step loop, JSON response with
   multi-tool batch, user-controlled state/observation edits, pending batch
   execution, and results as compound-observation components. See
   [`tasks/planning/260926-state-step-contract.md`](../planning/260926-state-step-contract.md).
2. **Runtime mapping:** the existing local entry is
   `operator_api.step_once` -> `cli_session_commands.run_step`, which currently
   parses message transcript, constructs message lineage, invokes generation,
   and persists message plus message-linked tool records. State-step needs its
   own typed transcript/runtime path and typed correlation for tool outcomes;
   it can reuse model invocation and capability execution services. The
   operator-edited transcript remains current-state authority. Minimal record
   envelopes, JSON response validation, patch behavior, and phase transitions
   can be refined at their implementation seams rather than blocking the first
   integrated slice. See the ready child
   [`260927-state-step-alpha-loop`](260927-state-step-alpha-loop.md).
3. **Deferred follow-ons:** model-specific capability profiles, observation
   reference selector experiments, the selectable state-history projections in
   [`260927-state-step-history-projections`](260927-state-step-history-projections.md), broader seeds and
   format configuration, expanded capability scope, and RPC/async support.

Do not create a parallel harness or require a general SWE schema, automatic
handoff authoring, multi-agent coordination, or dynamic instruction mutation
for this first slice.

## Parent Completion And Allowed Writes

Keep this parent as the design reference while the alpha child refines and
implements the minimal records and response contract. Record decisions and
follow-on links here; do not use roadmap updates as task threading. Close this
parent after the integrated alpha contract and any necessary follow-on task
boundaries are reflected accurately.

Planning writes: this task, its task-linked planning artifacts, child task
metadata, and generated workboard sections. No source or test implementation
is authorized by this planning task. The harness child separately authorizes
its bounded experimental implementation surfaces.

The integrated alpha implementation is authorized and scoped by the child
[`260927-state-step-alpha-loop`](260927-state-step-alpha-loop.md), not by this
requirements parent.

## Harness Handoff Progress

- The paired harness now creates fresh equal jj fixtures, compares
  `state_only` with `history_plus_state`, supplies customs in both arms, and
  independently checks real commits and task/workboard boundaries.
- Offline scripted demo and 100% targeted module coverage pass. Full pytest had
  no test failures (3,293 passed, 17 deselected); the repo coverage gate still
  reports the unrelated pre-existing `src/toas/graph.py:616` miss.
- A user-authorized local Qwen pair used equal fixtures and initial requests.
  The state-only arm repeated inspection and failed within 12 turns. The
  history-plus-state arm passed repository checks for both commits but exhausted
  the same budget without a terminal `finish`. See the closed harness task for
  request/token counts and the captured run paths.
- This is one history-exposure observation, not a reproduction of ReAct or
  statistical evidence that either architecture is generally more effective.
- Follow-on [tool and plan experiment](../closed/260926-state-experiment-plan-tools.md)
  responds to the trace with full Git diff inspection, multi-action plans, and
  reviewed general-purpose scripts. It remains mechanics evidence, not a
  production step contract decision.
- The follow-on's matched live pair passed the revised independent repository
  checks in both arms. State-only used one four-call plan; history-plus-state
  required more inference turns and a reviewed script after a write-field
  mismatch. Both responses identified the returned model as
  `Qwen3.8-27B-Q8_0.gguf`; the configured alias was
  `qwen3.5-35b-a3b`. See its closed task and runbook for the full trace and
  single-pair limitations.
- A same-prompt live repetition also passed both arms. State-only varied from
  5 to 3 inference calls; history-plus-state stayed at 4 but changed its
  action sequence. The inputs matched across repetitions. Raw usage is recorded
  without a cache-cost interpretation; see the repeatability task/runbook.
- The contract direction has shifted from a leading whole-buffer state marker
  to ordinary, state, and state-diff transcript turns. The human-controlled
  transcript is authoritative for current working state; the event log is a
  historical record, not operational authority that can override transcript
  edits. User-facing projections can show full state/diff history, states,
  diffs, key states, or key states with cumulative diffs. Separately, the
  default LLM packet stays state-only: effective instructions/schema, current
  state object, and one latest compound observation, not an accumulated queue.
  The paper and inspected implementations support the latest-observation
  default. YAML and Markdown DSL are the initial configured human-facing
  formats and round-trip through normalized JSON. Instructions include an
  available-tool advertisement and state-step alignment blurb; the response
  uses the existing JSON lane for a state patch plus a batch of tools, or a
  terminal outcome. Valid patches apply immediately; the batch remains pending
  until the user steps the runtime through existing permissions. Tool results
  join the next compound observation. Users can edit state and observations
  between steps. State-step and conversation-step remain semantically
  independent while sharing runtime/model/capability services. Model-specific
  tool profiles, observation-reference addressing, selectable transcript
  projections (tracked by
  [`260927-state-step-history-projections`](260927-state-step-history-projections.md)),
  complete grammar/seed details, expanded capability scope, and transport
  support are follow-ons. See the updated
  [contract recommendation](../planning/260926-state-step-contract.md).

## Initial Evidence

Created the straw man and ready investigation child after a read-only survey.
No production behavior, parser grammar, or durable record format changed.
The related roadmap/manual-board review was done during today's paper intake;
this planning pivot does not reprioritize that strategic queue.

## Alpha Implementation Follow-Through (2026-09-27)

The integrated child now owns the first local production slice. It preserves
this parent's contract: typed state/state-diff records remain separate from
message events; edited state stays authoritative; inference uses a state-only
packet; patches apply before external consequences; and pending tools run only
on a later explicit `step` through the existing capability executor. The alpha
settled its minimal turn grammar, graph records, JSON response fields, seed
command, and interrupted-run behavior in
[`260927-state-step-alpha-loop`](260927-state-step-alpha-loop.md).

The child has focused local end-to-end evidence (3,299 passing tests in the
latest suite run; 27 failures are recorded in the child, primarily sandbox
restrictions plus two legacy experiment assertions). Full-suite closure remains
pending because sandboxed subprocess/cache/socket tests cannot run in this
workspace and the unrelated experiment harness has two existing assertion
mismatches. Broader projection controls, observation addressing, model-fit
tool profiles, and async/RPC transport remain follow-ons as already recorded
above.

## Simulation State Delta

Readable edit notation for this turn; the dated checkpoint is not overwritten:

```yaml
progress_added:
  - Built and verified the paired state-only/history-plus-state experiment harness.
  - Earlier simulation notes proposed same-step, leading-marker detection. This is superseded by the integrated, semantically independent state-step direction below.
  - Added equivalent illustrative YAML and Markdown state-DSL envelopes alongside normalized JSON, keeping editable-buffer and model-request formats as separate choices.
  - User wants both YAML and Markdown DSL as initial configured formats with bidirectional parse/render against canonical JSON; valid model patches are accepted immediately.
  - Recommended selecting initial state through a versioned prompt-asset seed reference recorded with its digest.
  - User refined the source/projection model: current human-controlled transcript has operational authority; the event log is historical and cannot override user edits. State/diff turns support user-facing projections, distinct from the default LLM state-only packet.
  - Confirmed the default packet uses one latest compound observation, aligned with the primary paper and inspected implementations; prior observations are not automatically queued. Observation components can be addressable, and selected text may enter a state diff by reference for runtime expansion.
  - Historical alpha proposal (superseded by `260928-state-user-control-turn-lifecycle`): the user edited the state directly before each inference. The current direction preserves ordinary USER/CONTROL transcript turns and changes only the state-mode inference projection; executable turns resolve through the normal frontier runtime, and eligible content/results enter the state packet as observations.
  - State-step uses an independent typed record/history surface and shares TOAS runtime/model/capability services without conversation-step semantics. The integrated alpha path is preferred over further disposable experiments.
  - Recorded state-local operations as permission-free; environment observations use existing read capabilities; environment changes use existing write/execution permissions. Model-fit profiles may narrow advertised tools but do not change authorization.
  - Added model/runtime capability-profile benchmarks and observation-reference selector experiments as deferred planning fragments, not blockers for the alpha loop.
next_steps_prepend:
  - Map the agreed user-facing alpha loop to runtime ownership and define minimal state/transition/tool-run record envelopes, JSON response schema, and `step` phase behavior.
accepted_decisions_added:
  - Treat the experiment as mechanics evidence only; do not promote its authored schema or patch rules into production by implication.
  - Keep state-step independent from conversation-step while sharing runtime and model capabilities; use TOAS's existing JSON batch tool lane and permission paths.
```

Validation: task metadata, local links, and unique section headings checked;
workboard synchronized. No runtime tests apply to these planning-only additions.
