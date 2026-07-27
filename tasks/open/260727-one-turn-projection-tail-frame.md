Filed as: 260727-one-turn-projection-tail-frame
FKA:
AKA: transcript completion guard; next-turn execution frame; Gemini Enterprise one-turn tail; final user prompt restatement
Legacy index:

keywords: projection, implementation, active, compatibility, transcript, frontier, backend, renderer, gemini

Related: `260628-acceptance-live-generation-bounds`; `260614-legacy-and-fidelity-adapter-precedence`

# One-Turn Projection Tail Frame

## Objective

Make transcript-based inference usable without manual prompt editing by
appending a small, synthetic execution frame to the rendered model request.
The frame tells the backend to compute exactly the next assistant turn from the
active frontier rather than continue simulating the transcript.

This task delivers the first working frame. Empirical wording reduction and
renderer/model comparison are follow-on optimization, not prerequisites.

## Observed Working Baseline

The current manual workaround appends a compact restatement shaped roughly as:

```text
## TASK

You are the TOAS Assistant. Based on the complete transcript and context above,
generate the next single assistant response to the final user prompt. Don't
overthink it.

**Final User Prompt:**

[requested tool results]
[additional operator-run tool output and results]
[literal user text]

**Constraints:**
1. Generate only the `## TOAS:ASSISTANT` turn.
2. Do not generate any `## TOAS:USER` or `## RESULT` turns.
3. Follow the policies, formats, and tools established by the system prompt.
4. Produce the response shape requested by that prompt.
```

Less framing has produced worse behavior in dogfooding. The first
implementation should therefore preserve the substance of this proven shape
instead of waiting for an ablation study.

The sentence `Don't overthink it.` addresses a distinct quality problem
observed while using Gemini through Gemini Enterprise. Here, "Gemini" names
the model/use case, not TOAS's `gemini-rest` provider driver. The same model may
be reached through an OpenAI-compatible endpoint configured with
`llm_provider = "openai"` or through TOAS's request-based Gemini driver.

The hint therefore belongs to the transcript-rendering shape (or an explicit
variant of that shape), not to provider or endpoint selection. It remains
conceptually separate from the general one-turn constraint even when both are
shipped together in the initial frame.

## Required Behavior

1. A transcript-completion request, currently represented by
   `generation.transport_mode = "single_user_blob"`, ends with a synthetic
   one-turn execution frame after the rendered transcript.
2. The frame reconstructs the operationally active request, not just the last
   isolated user message. It must retain, when present:
   - results of tools requested by the assistant;
   - results of additional tools run directly by the operator;
   - literal user-authored text;
   - other unresolved projected context needed to decide the next assistant
     action.
3. Reconstruction is deterministic and derived from the already-selected
   model-input/frontier projection. It must not mutate, append to, or become
   authoritative over transcript or durable history.
4. The general frame explicitly requires exactly one assistant turn and
   forbids synthesized user and result turns.
5. The frame defers detailed response format and tool policy to the active
   system/bootstrap prompt; it does not hard-code YAML as a universal response
   format when the active prompt requires something else.
6. The initial transcript frame includes the empirically required
   `Don't overthink it.` hint. Selection of that frame is based on transcript
   rendering/transport shape, or an explicit renderer profile if one proves
   necessary; it must not be inferred from `llm_provider`, endpoint protocol,
   or use of the `gemini-rest` driver.
7. Native chat/message rendering remains unchanged unless evidence shows that
   a native backend also requires the logical operator in a backend-appropriate
   form.
8. The actual request recorded in `llm_call` evidence reflects the rendered
   input sent to the backend closely enough to inspect and reproduce the tail
   frame behavior.

## Ownership And Implementation Direction

This is model-request rendering behavior, not transcript serialization or
graph behavior.

The current likely seam is the `single_user_blob` request renderer in
`src/toas/llm.py`, supplied with structured request messages assembled by the
runtime. If reconstructing the active frontier cleanly requires a structured
intermediate object, introduce it at the runtime/model-invocation rendering
boundary rather than teaching transcript storage about the frame.

Prefer an explicit logical tail-frame representation plus transcript-renderer
wording over provider conditionals. In particular, an OpenAI-compatible
endpoint serving Gemini Enterprise must receive the same frame as the
request-based Gemini driver when both use the transcript rendering shape. Do
not require a broad renderer framework before landing the working baseline.

## Acceptance Criteria

- [ ] Given a projected request containing a user prompt, an assistant tool
  request, its result, an additional operator-run result, and trailing literal
  user text, transcript rendering automatically appends one tail frame that
  preserves all of that active material.
- [ ] The generated frame contains the effective one-assistant-turn constraint
  and excludes instructions to generate user or result turns.
- [ ] The transcript frame contains `Don't overthink it.` while the
  backend-neutral one-turn rule is independently testable.
- [ ] Equivalent `single_user_blob` requests sent through
  `llm_provider = "openai"` and the request-based Gemini driver receive the
  same logical tail frame; provider choice does not select or suppress it.
- [ ] `chat_messages` requests retain their current message payload shape.
- [ ] Transcript serialization and transcript/history projection output are
  byte-for-byte unchanged for representative fixtures.
- [ ] No synthetic frame is written as a message event, control record, tool
  record, or other durable state.
- [ ] Request/audit coverage proves that a `single_user_blob` model call sends
  the framed projection and that the stored transcript remains unchanged.
- [ ] A focused behavioral fixture or captured backend result demonstrates
  single-turn output without adding response-normalization behavior to this
  projection-only task.
- [ ] The default test suite passes.

## Non-Goals

- Finding the minimum viable wording before shipping the frame.
- Running a full cross-model benchmark or freezing a permanent prompt string.
- Changing transcript parsing, serialization, graph topology, head selection,
  frontier durability, or event schemas.
- Introducing projection-specific state into `events.jsonl`.
- Coupling frame or hint selection to the Gemini provider driver, an endpoint
  protocol, or model-name guessing.
- Solving response normalization after a backend ignores the rendered
  instruction, except for the bounded regression evidence needed by this task.

## Follow-On Evidence, Not A Gate

After the baseline works in normal TOAS execution, narrower experiments may
remove or vary one element at a time:

- repeated active-frontier material;
- the task heading;
- explicit one-turn constraints;
- renderer- or model-use-case-specific hints;
- amount of literal versus compressed frontier restatement.

Compare exact one-turn emission, frontier correctness, tool choice, domain
reasoning, continuation failures, and token cost. Open a focused follow-on only
when an experiment identifies a concrete renderer-specific improvement.

## Allowed Write Surfaces

- `src/toas/llm.py`
- `src/toas/runtime/model_invocation_contracts.py`
- a focused new renderer/runtime module under `src/toas/runtime/` if it makes
  the logical-frame/backend-rendering split clearer
- `src/toas/config.py` and `src/toas/config_parsing.py` only if an explicit
  renderer profile cannot be derived safely from existing provider/transport
  selection
- focused tests under `tests/`
- this task file and mechanically generated `tasks/WORKBOARD.md` sections

## Required Completion Evidence

- focused renderer and model-invocation test commands and results;
- default `uv run pytest` result;
- before/after captured request payload for one representative
  `single_user_blob` frontier;
- proof that the corresponding transcript and durable event lineage contain no
  synthetic frame;
- one Gemini Enterprise dogfood result through an OpenAI-compatible configured
  endpoint showing a single assistant turn without manual prompt editing;
- request-shape parity evidence for the request-based Gemini driver, without
  requiring that driver for the primary use case.
