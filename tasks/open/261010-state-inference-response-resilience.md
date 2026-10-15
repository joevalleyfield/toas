# State Inference Response Resilience

Filed as: 261010-state-inference-response-resilience
FKA:
AKA: prose before state patch; missing state diff; model response format recovery
Legacy index:

keywords: runtime, investigation, active, contract, state, inference, recovery, prompts

Parent: `260926-state-step-requirements`
Related: `261010-preview-request-pretty-inspection`; `261010-rolling-tool-failure-memory`

Status: ACTIVE requirements and request inspection; clarify state-update output and recover from model format failures

## Intent

Make state-mode inference workable when a local model emits explanatory prose
before its state update or falls back to its native tool-call syntax.

Confirmed operator direction:

- Some prose thinking before a state diff should be allowed.
- The model must clearly understand that a state update is required.
- Inspect the actual preview request, rather than infer prompt quality from
  error previews alone.
- Inference resilience is the current concern; the history side-slip remains
  a lower-priority future consideration.
- Before choosing a prompt/parser repair, compare structured input and
  instruction approaches experimentally, including a worked example and
  preceding turns with valid state diffs.
- The observed control result should not have been visible to the model. Treat
  that as a separate usage/runtime slip, rather than the core inference problem.
- Investigate drift induced by state/payload content and representation before
  adopting heavier prompting or prior-turn context. Specifically inspect embedded
  Markdown output and stringified JSON for possible structural expansion.
- Make request composition configurable so model-specific defaults can evolve
  from evidence and the operator can try alternatives during ordinary use.

## Evidence and Findings

See [request review](../../docs/notes/2026-10-10-state-inference-request-review.md)
and its captured preview JSON. The decoded preview exactly matches the latest
rejected request packet `st_0fd3c8cc81064c2c86e8edb0a75d701e`.

The request explicitly advertises `state_patch` and `tool_calls`, ending with
`Return JSON only.` It has no complete example response. Four inspected rejected
responses contain prose followed by XML-style `<tool_call>` markup and no JSON
state update. The latest request contains successful tool observations but no
format-rejection feedback or rejected response from the preceding failures.

Comparison with the preceding accepted inference uses actual recorded
`model_call.request_messages`: JSON packaging, instructions, schema, and tool
advertisement are unchanged. Only state and observation change, and the reported
returned model is the same. A worked example is a possible robustness measure;
its absence is not an established cause of this context-specific regression.

Current parser accepts bare JSON or a response wholly enclosed in a conventional
Markdown JSON fence, but rejects prose before otherwise valid JSON. Separately,
current validation defaults absent `state_patch` to `{}`; a well-formed JSON
tool-only proposal can therefore omit the state-update field entirely.

## Proposed Behavior and Boundaries

- Accept explanatory prose followed by one unambiguous structured proposal,
  subject to the existing patch/tool validation. Prose does not become executable
  intent or an implicit patch.
- Explicitly ask for a final proposal containing `state_patch` and `tool_calls`,
  with its input and instruction arrangement chosen from experimental evidence.
  An example or prior exchange remains a candidate, not a settled requirement.
  Explain that state changes and retained findings
  belong in `state_patch`, and TOAS tool requests use the advertised JSON shape.
- Make missing state-update output an actionable format failure; do not fabricate
  a patch from prose or execute XML-style calls as a substitute for a proposal.
- Preserve accepted state and pending-tool authority on an invalid response.
- Feed format-rejection information into a deliberate recovery path so the next
  attempt can correct its response instead of receiving the same request again.

Tentative interpretation: the existing JSON `state_patch` envelope remains the
model response contract; this does not require the model to author a literal
`## TOAS:STATE-DIFF` transcript block. An explicit empty patch may be legitimate
when there is no state change, but omission should be distinguishable from it.

## Success Conditions

- A useful explanation followed by a valid proposal succeeds without losing the
  validated patch, requested batch, or terminal outcome.
- Bare JSON and existing JSON-fenced proposals remain supported.
- Multiple candidate proposals, malformed patches, and prose/XML without a state
  proposal cannot accidentally accept or execute work.
- Actual rendered requests make the final state-update contract clear, consistent
  with accepted prose. Evidence supports the chosen input representation and
  any format demonstration rather than assuming one is necessary.
- Rejection recovery is bounded and observable; tests and a concrete operator
  artifact show what the next attempt receives and how exhaustion is reported.

## Open Decisions

- Recovery timing: correction context on the next explicit step, an explicitly
  bounded inference-only repair attempt within a step, or both. No hidden tool
  execution loop is implied.
- How to delimit the final proposal when prose itself quotes JSON examples, and
  whether explanatory prose should be separately retained or displayed.
- Whether unchanged state must be explicitly represented by `state_patch: {}`
  in all protocols, and how any compatibility behavior should be versioned.

## Progress

- 2026-10-10: actual CLI preview inspected against recorded failed requests;
  evidence captured. No parser, prompt, retry, or execution implementation changed.
- Recorded failed invocation messages and a network-free SDK-call capture both
  contain the JSON state packet; no TOAS transcript fallback was found. Server
  prompt rendering remains outside the available historical capture.
- Saved an offline replay at the SDK call and SDK-serialized HTTP boundaries:
  [readable request](../../docs/notes/2026-10-10-state-inference-sdk-request.md),
  [SDK arguments](../../docs/notes/2026-10-10-state-inference-sdk-request.json), and
  [HTTP body](../../docs/notes/2026-10-10-state-inference-http-body.json).
  Captured message content exactly matches the recorded failed invocation.
  Current settings were used; this is not a historical wire capture.

## Matched Inference Pilot

Run isolated inference calls against the configured local model using the
captured failed state and observations. Do not execute generated tool calls or
write proposals into dogfood history. Compare six conditions, twice each:

1. Original captured request, retained as a reference including its control result.
2. Same JSON packet with control results excluded.
3. Clean data as readable JSON with the same instructions in a system message.
4. Same split instructions with clean structured data expressed as YAML.
5. Clean JSON packet with a complete illustrative state-patch response example.
6. Clean JSON packet preceded by the actual accepted user/assistant exchange
   containing a valid state patch.

All clean conditions share state, tool observations, tool definitions, and output
schema. Keep model settings and output budget fixed, interleave the conditions,
and retain SDK inputs, complete responses, evaluation details, and returned model
identity. Report current-parser acceptance separately from presence of an
unambiguous valid proposal after prose, and inspect proposals for useful state
updates and appropriate tool requests. Two samples per condition are diagnostic
evidence, not a statistical benchmark. Prior-turn exposure intentionally varies
more than examples alone and should not be interpreted as an isolated token-level
effect.

## Pilot Findings — 2026-10-10

See [results and complete evidence](../../docs/experiments/261010-state-inference-format/REPORT.md).
Twelve isolated calls completed against the verified loopback endpoint; no
generated tools executed and no patches or model proposals entered dogfood history.

- Separate system instructions plus readable JSON: valid proposals in 2/2 trials.
- An actual prior accepted exchange plus the clean JSON packet: valid in 2/2.
- Clean JSON alone, YAML with separate instructions, and an appended example
  inside the JSON instruction string: no valid proposal in either trial.
- Original reference: one prose-prefixed valid proposal, one XML-style failure.
  The former is a direct artifact for future prefix-tolerant parser coverage.
- Successful split-JSON proposals retained fresh observations. One prior-turn
  proposal instead favored older artifacts, so assess state maintenance as well
  as format correctness before adopting history exposure.

This small pilot does not establish reliability or the trigger for the regression.
Next experiments should isolate message-role changes from pretty-printing and
compact state-diff demonstrations from full prior-observation exposure. An example
is not the preferred repair on the evidence so far, although other example
arrangements remain untested. Control-result visibility remains a separate slip.
Production parser, prompt, and recovery behavior have not changed.

## Reliability Follow-Up

The operator requested a stronger reliability check after the pilot. Run 18
additional trials each for split JSON and the real prior-turn exchange, plus
eight additional clean-JSON baseline trials: 44 calls, yielding totals of
20/20/10 per condition. Preserve the two-trial discovery pilot separately and
report independent follow-up results as well as descriptive combined counts.
Use the same captured state, clean observations, model settings, and output
budget; interleave the conditions. Record SDK finish reasons to distinguish
format failures from output-budget truncation. Inspect accepted proposals for
retention of fresh findings and relevant next requests. Report binomial
uncertainty bounds and limit conclusions to this state/context, rather than
claiming cross-task robustness from repeated inference on one input.

Artifacts: `docs/experiments/261010-state-inference-format/reliability/`.

### Reliability Findings — 2026-10-10

Completed all 44 inference-only follow-up calls. See the
[report and evidence](../../docs/experiments/261010-state-inference-format/reliability/REPORT.md).
Every response ended normally (`stop`), with no recorded truncation or transport
error, and the same returned Qwen3.8 model. Requests were identical within each
condition. No generated tools executed and no state proposals entered history.

- Independent follow-up: real prior accepted exchange 18/18 valid explicit
  proposals (95% Wilson interval 82.4–100%); split system instructions/readable
  JSON 12/18 (43.7–83.7%); clean original JSON packaging 0/8 (0–32.4%).
- Including discovery: 20/20, 14/20, and 0/10 respectively. These are repetitions
  of one input, not cross-task reliability estimates; 20/20 still has an 83.9%
  lower Wilson bound under the independent-trial assumption.
- Prior turns improved format without ensuring state maintenance: one patch
  repeated unchanged notes, two retained mostly questions/plans, and another
  attached CLI lines to an older AGENTS.md block ID. Split JSON also produced
  an invented artifact and a grep command with no file operand.
- Split JSON produced a complete JSON response omitting `state_patch`. Current
  runtime defaults the missing field to `{}`; this experiment scores it as a
  failure of the explicit state-diff contract. Preserve this concrete artifact
  for required-field behavior coverage.
- Broader prefix extraction recovered 13/18 split-JSON and 3/8 baseline
  proposals, but three extra recoveries followed an unclosed `<tool_call>` tag.
  Only one extra baseline recovery was ordinary prose followed by fenced JSON.
  Deliberate prose tolerance and XML envelope handling remain distinct decisions.

Next isolate a compact state-diff demonstration exchange from full prior-history
exposure, then evaluate held-out states and short sequences of updates. Score
fresh-finding retention and artifact correctness alongside format compliance.
The evidence supports investigating prior diffs, explicit patch requirements,
and bounded corrective feedback; no production repair or retry policy has been
selected or implemented.

## Payload-Trigger Investigation

The operator considers prior-turn conditioning heavy handed and wants to locate
what inside the supplied state/payload induces drift. Compare input content and
representation while retaining the same instruction text and one-user-message
layout; add no examples or preceding turns.

Inspection of the four failed packets found no leaf strings decoding into JSON
objects/arrays. The latest two include Markdown-fenced grep outputs under
`observation`; state itself is already structured. The first two failures had
no tool outputs, so the fences are not a necessary historical trigger. Distinguish
HTTP/message serialization escaping from escaped text inside the model's packet.

Run three trials each for a fresh clean baseline, whole-packet pretty printing,
output fence removal, structured stdout, structured numbered matches, state
inline-backtick removal, an empty state plan, and absent tool outcomes. The
last two remove information rather than merely re-expressing it. Structured
forms must exactly reconstruct the captured output and metadata; do not guess
source paths or insert extra facts. Keep exploratory findings separate from
reliability claims and preserve complete SDK input/output evidence.

Artifacts and condition definitions:
[payload ablation](../../docs/experiments/261010-state-inference-format/payload-ablation/README.md).

### Payload Investigation Findings — 2026-10-10

Completed 44 additional inference-only calls: 24 representation/content-screen
calls, 12 goal/instruction-placement-screen calls, and eight independent
instruction-order confirmation calls. See the
[report and complete evidence](../../docs/experiments/261010-state-inference-format/payload-ablation/REPORT.md).

- Removing output fences or expanding grep results into numbered records did
  not yield a valid strict proposal in any of three trials per condition.
  Whole-packet pretty printing and structured stdout each yielded 1/3. State
  inline-format removal yielded 0/3; emptying its plan yielded 1/3, with incorrect
  source paths in the successful proposal. These screens do not establish zero
  effect, but offer no consistent cure.
- Emptying only the goal changed the failure pattern: two of three responses
  avoided XML. One attempted malformed JSON; another supplied a JSON patch with
  `report: null`, allowed by runtime but rejected by the stricter advertised-schema
  metric. The goal remains a possible contributor; no individual state field has
  been established as the cause.
- Moving the **unchanged instructions member to the end** yielded 3/3 strict
  successes versus 0/3 baseline, then 4/4 versus 0/4 in independent confirmation.
  Combined 7/7 versus 0/7; the Wilson lower bound for 7/7 is 64.6%, for confirmation
  alone 51.0%. All reordered proposals changed state and retained fresh CLI
  findings/locations, with relevant source requests. Some still synthesized code
  outlines into notes rather than retaining references.
- Reordering retains decoded packet equality, character length, instruction
  wording, Markdown outputs, escaped strings, state, observation, schema, and
  tools. Each request is one user message, without examples or prior turns.
  Instruction placement/recency is the strongest smaller hypothesis so far;
  model attention mechanism and cross-context reliability remain unproven.
- All calls ended normally on the same model. A prefix-scan diagnostic bug
  double-counted one JSON object after a blank line; corrected and rescored one
  plain-instruction recovery. Strict counts and earlier reliability results did
  not change. No generated tools executed and no patches entered history.

The packet builder currently inserts instructions first, and generation serializes
that insertion order (`build_state_step_packet`, `GenerationRunner.prepare_state_request`).
Three additional captured packets each scored 3/3 for both original ordering
and instructions-last. On the larger state-seed packet, moving the goal, plan,
or output-schema members later each also scored 3/3; role-separated instructions
and data scored 3/3. These results show no advantage in strict proposal validity
for order or roles on those held-out contexts, but do not invalidate the original
same-context 7/7 versus 0/7 result. See the
[cross-context screen](../../docs/experiments/261010-state-inference-format/payload-ablation/instruction-placement/cross-context/README.md)
and its complete trial evidence. The strict metric measures proposal shape,
advertised-tool adherence, and registered argument validity; it does not
establish task correctness or state-maintenance quality.

The initial cross-context scores were wrong: the runner hard-coded a four-tool
allowlist even though the newly captured requests advertised larger registries.
It now reads each SDK request's `tools.available` list and validates against
that list plus the local registry. All cross-context and placement results were
rescored; earlier pilot packets advertised exactly the original four tools, so
their counts are unchanged. No inference result was executed or written to
history. Production behavior did not change.

Next inspect proposal quality and state maintenance for these held-out packets,
then compare the composition choices on additional tasks before choosing any
default. Test genuine JSON-string expansion only when a captured packet contains
such strings. Prior-turn conditioning remains a candidate, not the preferred
first repair.

## Configurable Request Composition

Confirmed direction: turn the one-off experimental arrangements into selectable
composition policies. Support model/target defaults and explicit overrides for
on-the-fly comparisons. The two useful directions are explicit conversation turns
and instructions after the supplied data. Keep these as choices the operator can
compare and tune, rather than committing to one universal arrangement.

### Small Initial Policy Surface

Tentative layout names, not proposed final configuration keys:

| Layout | Behavior |
| --- | --- |
| `packet_first` | Current single user JSON packet, instructions first; compatibility/reference arrangement |
| `packet_last` | Same packet and instruction words, instructions member last |
| `role_messages` | Explicit instruction and data messages with appropriate conversation roles |

Select prior accepted state/diff context separately from layout. A role-separated
request without prior turns and a request containing an accepted exchange are
different conditions: system instructions/readable JSON yielded 14/20, the real
prior exchange 20/20, and instruction-last ordering 7/7 on the captured context.
The prior-exchange experiment included older observations as well as a format
demonstration; it does not establish the effect of roles alone.

Keep instruction wording, output contract, history selection, and data rendering
independent enough to vary one factor at a time. Additional representation options
(readable JSON, projected text versus structured outputs) remain candidates as
evidence warrants them. A selected layout must preserve the supplied state,
schema, tool definitions, and authorized observation information.

### Resolution And Experiment Semantics

- Reuse the existing named model-target and effective-policy machinery for model
  defaults, rather than introduce a second model catalog. `TargetCatalogEntry`
  already carries sparse generation overrides; composition needs its own explicit
  policy rather than overloading `generation.transport_mode`.
- Resolve global defaults, model/target preferences, and explicit scoped or
  per-invocation overrides with documented precedence and visible provenance.
  The exact configuration namespace and override command remain open.
- Use one composer for normal inference, preview, and explicit experimental
  comparisons. Operators should be able to compare layouts on a fixed accepted
  state/observation without editing a bespoke Python runner. A one-call override
  should not silently replace the model's persistent default.
- Record the resolved composition, instruction/protocol identity, selected target,
  configured and returned model identities, generation settings, and actual request
  messages with each call/comparison. The observed configured alias differed from
  the returned model identity; retain both when associating evidence with a model.
- Preserve lineage and observation ephemerality when selecting prior context.
  Define a bounded accepted-state/diff history policy; old tool observations and
  control results must not become visible merely because a turn layout is enabled.
- Keep transport adaptation explicit. A role layout subsequently flattened by a
  provider transport must be visible in the effective SDK-boundary preview/audit,
  rather than presented as if role separation survived.

Tentative default-tuning model: the operator promotes evidence-backed preferences
for a model/target. Automatic selection or promotion has not been requested or
specified. Context diversity and state-maintenance quality should inform defaults
alongside format adherence.

### Acceptance Shape And Ownership

- Operator can select both promising layouts and the current reference layout
  through the normal configuration/override surfaces; resolution identifies the
  winning source and uses the chosen model's settings.
- Preview and inference use the same resolved composition; SDK-boundary evidence
  confirms the messages after provider adaptation. Local and daemon paths preserve
  the same semantic configuration and output contracts.
- An explicit bounded comparison varies composition on a frozen state/observation,
  retaining complete requests, responses, model identity, and evaluation evidence.
  Proposed tools and patches remain proposals in an inference-only comparison.
- Switching a layout preserves the state-update envelope, required patch semantics,
  tool authority, and existing append-only history. History exposure is deliberate
  and bounded, with control-result visibility covered separately.
- Inspect concrete preview and SDK artifacts for every initial layout; verify
  configuration precedence, scoped overrides, model-target switching, and message
  fidelity with focused tests when implementation begins.

Likely ownership: effective configuration and `runtime/model_targets.py` resolve
policy; the state request projection/composer owns message arrangement;
`GenerationRunner.prepare_state_request` consumes it; `llm.py` owns provider
adaptation. Keep prompts explicit library material and CLI/RPC adapters thin.
This section defines the next design direction; production composition remains
unchanged. Open a focused implementation follow-on once the policy schema,
override scope, and accepted-history projection are settled.
