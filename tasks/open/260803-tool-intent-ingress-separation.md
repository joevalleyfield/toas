Filed as: 260803-tool-intent-ingress-separation
FKA:
AKA: native tool calling; alternate callable lanes; tool ingress adapters; harness separation
Legacy index:

keywords: runtime, decomp, inception, contract, tooling, native, ingress, harness

Related: `260803-language-exec-fenced-block-lane`; `260412-json-callable-lane-parser-and-policy`; `260803-seed-prompt-composition-study`; `260803-first-failure-plan-recovery`; `260628-gemini-endpoint-discovery`; `171`; `174`

# Tool-Intent Ingress And Harness Separation

Separate native provider tool calling, TOAS text-callable alternatives, shared
step/runtime semantics, and harness observation so any supported calling lane
can be selected without forking capability behavior or turning the harness into
production policy.

This is a requirements parent. It owns the canonical ingress boundary and the
cross-lane equivalence contract, not the implementation of every individual
syntax or provider.

## Motivation

Native provider tool calling is the extreme happy path when a backend exposes
it faithfully. TOAS originated in environments where that channel was blocked,
rewritten, or captured by hidden provider policy, so its YAML/action and direct
shell lanes remain essential.

The desired architecture does not choose one history and discard the other:

- use native calling when it is genuinely available and reliable;
- retain multiple text/transcript call encodings for blocked or hostile paths;
- preserve TOAS's visible, one-layer-at-a-time step interaction regardless of
  how tool intent entered the runtime;
- keep model/provider probing and conformance measurement in the harness,
  orthogonal to production semantics.

## Separation Model

```text
model/provider or user surface
        |
        v
intent ingress adapter
  - native provider tool_calls
  - YAML / JSON structured fence
  - toas-tool call expression
  - executable language fence
  - direct user $ / slash intent
        |
        v
canonical ToolIntent / ToolPlan
        |
        v
origin + effective authority resolution
        |
        v
shared capability validation / execution
        |
        v
durable request/result facts
        |
        v
lane-appropriate transcript + next-model projection
```

Alongside, not inside, that path:

```text
harness
  - sends/records provider requests
  - captures raw responses
  - invokes or observes ingress adapters
  - compares normalized intent/results
  - reports capability and fidelity
```

The harness never decides production authority, frontier meaning, retry,
execution success, or which lane is active for an ordinary session.

## Current Repo Evidence

### Native transport is partially represented

- `src/toas/llm.py::BackendResponse` already has optional `tool_calls`.
- `GeminiRESTDriver` normalizes Gemini `functionCall` parts into an
  OpenAI-shaped `tool_calls` list in streaming and non-streaming responses.
- `OpenAIDriver` currently returns text/reasoning/usage only and does not
  normalize native response tool calls.
- `LLMDriver.call` does not accept a provider-neutral tool-definition/schema
  input, so TOAS cannot yet advertise its live registry natively through the
  driver contract.
- The ordinary generation/runtime path has no consumer of
  `BackendResponse.tool_calls`; current references outside `llm.py` are tests.
- Current response handling rejects empty textual content in paths where a
  tool-call-only native response may legitimately contain no assistant text.

Native tool calls therefore exist as a transport-edge data field, not yet as a
complete operator/runtime capability.

### Alternate ingress and shared execution already exist

- `src/toas/graph.py::normalize_tool_plan` owns canonical callable aliases,
  arguments, intention, and basic plan validation after YAML deserialization.
- `src/toas/runtime/intent_arbitration_edges.py` already orders multiple textual
  intent candidates.
- `src/toas/tools_cluster/registry.py` owns capability validation/dispatch.
- `src/toas/tools_cluster/execution.py` owns shared plan execution.
- Direct user shell intent and assistant-addressable shell capability already
  prove that equivalent operations can enter different authority contexts
  while retaining related result shapes.

### Harnesses currently probe, but do not own, semantics

- `src/toas/llm_harness.py` probes provider behavior, structured output, and
  protocol collisions and records raw/normalized observations.
- `docs/protocol-notes.md` correctly labels those observations non-normative.
- `src/toas/acceptance_harness.py` exercises operator behavior through external
  runs but should not become an alternate runtime implementation.

The architectural risk is not current harness overreach so much as future
pressure to put native/text lane translation into whichever harness first
needs to compare them.

## Canonical Tool Intent

Define one provider- and syntax-neutral intent shape sufficient for all ingress
adapters. At minimum it needs:

- callable name;
- normalized arguments;
- optional intention;
- ordered-plan position and grouping identity;
- origin role and ingress lane;
- source location or provider call identity;
- authority context requested, without granting it;
- provider-native metadata needed for result round-trip, such as call id;
- raw-source reference for diagnostics/audit without making raw syntax
  execution truth.

The current normalized `{"tool_name": ..., "args": ...}` shape is the starting
point, not necessarily the final domain object. Provider call identity and
source/provenance must not be smuggled into tool arguments.

Ingress adapters may produce different diagnostics, but equivalent valid calls
must converge before capability validation and execution.

## Ingress Adapter Contract

Each adapter owns only:

- recognizing its source envelope/body;
- parsing/deserializing it;
- preserving source identity and raw diagnostic context;
- normalizing into canonical `ToolIntent` / `ToolPlan`;
- reporting ambiguous or invalid source without executing it.

Adapters do not own:

- capability implementation;
- effective authorization;
- tool plan scheduling or first-failure behavior;
- durable result semantics;
- activity terminality;
- provider retry policy;
- transcript/history ownership.

## Native Provider Tool Calling

### Outbound advertisement

- Translate the effective live TOAS capability registry into provider-native
  tool schemas at the Model Invocation edge.
- Respect capability profiles, hidden tools, effective policy, and provider
  schema limitations.
- Record the exact schemas and native-tool selection policy sent in `llm_call`
  evidence.
- Keep the provider translation derived from the same registry truth used by
  textual capability guidance.

### Inbound normalization

- Normalize provider-native calls into canonical intents with stable provider
  call ids and origin metadata.
- Support tool-call-only responses without requiring fabricated assistant text.
- Handle native calls plus assistant text without losing either surface.
- Define deterministic conflict behavior when one response contains both
  native calls and text that itself parses as a TOAS callable lane; never
  execute both accidentally.
- Preserve provider-specific raw response material for diagnostics while
  keeping provider shapes out of capability execution.

### Tool results back to the model

- Preserve call ids/names needed to project shared `tool_result` facts into
  provider-native tool-result messages on a later model invocation.
- Native result projection is a Model Invocation adapter over durable/shared
  results, not a second result store.
- Native request/result envelopes may be omitted from the human transcript when
  a clearer TOAS projection exists, but they must remain inspectable.

## Preserve TOAS Step Interaction

Native tool calling must not silently introduce a hidden provider-style agent
loop.

The intended turn shape remains:

1. one model invocation produces conversation, synthesis, or tool intent;
2. TOAS records/projects that consequence;
3. one later `toas step` resolves the next layer—such as executing the tool
   plan;
4. results become durable facts and projected transcript content;
5. another step may invoke the model with those results.

Whether a narrowly configured convenience surface eventually collapses these
steps is a separate orchestration policy. Native calling itself does not own
looping.

## Lane Selection And Fallback

Resolve tool-ingress mode explicitly from backend capability, transport,
configuration, and prompt profile. Candidate modes include:

- `native`: advertise provider-native tools and accept native calls;
- `text`: use one selected TOAS callable prompt/recognizer family;
- `hybrid-observe`: advertise or accept both only for controlled compatibility
  measurement, with deterministic single-winner arbitration;
- `none`: conversation/synthesis only.

Requirements:

- record the selected mode and provenance in model-call evidence;
- do not infer native availability merely from provider name;
- do not silently fall back after a response in a way that duplicates an
  already emitted call;
- allow native request failure to produce an explicit later retry/fallback
  decision rather than mutating the in-flight call shape invisibly;
- keep blocked-channel profiles free to avoid collision-prone words and native
  schemas entirely;
- let a reliable provider use the native happy path without still entraining it
  to emit YAML.

## Prompt Recomposition Boundary

Seed/prompt composition should select an ingress profile, not declare one
universal tool syntax:

- native profile: role/stance plus provider-native schema advertisement; omit
  `no-provider-tools` and text-call few-shots unless needed as fallback;
- text profile: choose YAML/JSON/`toas-tool`/executable-fence activators and
  retain provider-deconfliction guidance;
- conversation-only profile: omit both tool advertisements while preserving
  the conversation/synthesis stance;
- transport-resilient text profiles may teach structural or unusual activators
  without changing runtime authority.

This may require the default template to separate stable stance layers from
lane-specific protocol/constraint layers more clearly than it does today.

## Harness Boundary

Create conformance scenarios that can be applied across ingress adapters while
keeping harness code outside semantic ownership.

The harness may:

- declare a scenario's logical tool intent and expected result;
- send native schemas or text prompts through a selected provider/adapter;
- retain raw request, raw response, normalized intent, execution/result
  observations, timings, and provider identity;
- compare native, YAML, JSON, call-expression, and executable-fence fidelity;
- characterize proxies that strip or rewrite activators;
- report unsupported capabilities and expectation failures.

The harness must not:

- contain the only parser/normalizer for a production lane;
- synthesize semantic success when runtime evidence is absent;
- execute tools through a harness-only authority path;
- choose ordinary session ingress mode;
- own prompts, provider retries, step scheduling, or durable records.

Production adapters should be callable by the harness; production must not call
into harness modules.

## Cross-Lane Equivalence Matrix

For representative tools and plans, prove which properties are identical and
which remain lane-specific:

| Concern | Shared after ingress | Lane/provider-specific |
| --- | --- | --- |
| Tool name and arguments | yes | source spelling/schema |
| Capability validation | yes | parse/deserialization diagnostics |
| Effective authority | shared resolver | origin evidence/requested context |
| Execution and first-failure policy | yes | source-span/restaging syntax |
| Durable request/result facts | yes | provider call id/raw envelope metadata |
| Human transcript projection | shared semantic facts | ergonomic lane rendering |
| Next-model result projection | shared source facts | native tool message vs text result context |
| Harness expectations | shared logical scenario | raw transport/provider observations |

## Acceptance Criteria

- [ ] One canonical tool-intent/plan contract represents native calls and every
  implemented text/direct-user lane without provider fields leaking into tool
  arguments.
- [ ] Ingress adapters stop at recognition/parsing/normalization and share
  capability validation, authority, execution, failure, and durable result
  semantics.
- [ ] The provider driver contract can accept effective tool definitions and
  return tool-call-only or mixed text/tool responses losslessly.
- [ ] OpenAI-compatible and Gemini-native call responses normalize to the same
  canonical intent shape, including stable call identity.
- [ ] Provider-native results can be projected back on a later invocation from
  shared durable result facts.
- [ ] Native calling preserves visible TOAS step boundaries and does not create
  an implicit internal agent loop.
- [ ] Ingress mode/profile selection is explicit, provenance-bearing, and
  avoids duplicate execution during mixed output or fallback.
- [ ] Prompt composition can select native, text, or no-tool profiles while
  sharing the stable role/conversation/synthesis stance.
- [ ] A shared scenario corpus compares equivalent native and alternate-lane
  calls without putting production parsers, authority, or execution inside a
  harness module.
- [ ] Model-call audit evidence records effective tool schemas, ingress mode,
  raw/normalized response shape, and relevant provider identity.
- [ ] Existing blocked-native-channel operation remains fully supported.

## Non-Goals

- Requiring native tool calling from every backend.
- Retiring YAML, JSON, direct shell, executable fences, or other resilient
  alternates when native calling works.
- Hiding repeated model/tool execution behind an automatic loop.
- Letting provider schemas or harness fixtures become capability authority.
- Flattening all lane-specific diagnostics and projections into one lowest-
  common-denominator text format.
- Treating a provider-advertised feature as proven working without observation.

## Likely Follow-On Split

1. Canonical `ToolIntent` / `ToolPlan` domain contract and ingress adapter port.
2. Provider-neutral tool-schema advertisement input on `LLMDriver`.
3. OpenAI and Gemini native request/response normalization parity.
4. Runtime consequence path for native tool-call frontiers and mixed outputs.
5. Native tool-result message projection from shared durable results.
6. Explicit ingress-mode policy, provenance, and fallback/arbitration.
7. Prompt-template profile separation for native/text/no-tool modes.
8. Cross-lane harness scenario schema and conformance reporting.

Open bounded children only after the canonical object and step-state transitions
are fixed enough that each slice has one owner and test story.

## Allowed Write Surfaces

- this task file and mechanically generated `tasks/WORKBOARD.md` sections
- related requirements tasks for relationship/profile corrections
- follow-on task artifacts opened from the requirements decisions

## Required Completion Evidence

- current native-tool request/response/runtime trace;
- canonical tool-intent schema and state transition examples;
- native/text/direct-user ingress ownership matrix;
- lane selection and mixed-output arbitration table;
- TOAS step sequence for a native tool call and result round-trip;
- harness dependency-direction rule plus representative shared scenarios;
- bounded follow-on task graph with allowed write surfaces and tests.

## Operator Input Welcome

Useful additions include a preferred native-call step projection, providers
where native calling is genuinely reliable, examples of blocked or rewritten
native channels, desired lane-selection controls, and existing harness artifacts
that should become shared conformance scenarios.
