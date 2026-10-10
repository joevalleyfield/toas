# State Inference Request Review — 2026-10-10

Associated task: `261010-state-inference-response-resilience`.

## Source and Method

Inspected dogfood `.toas/session-20261010-1247-preview-request-pretty-inspection.md` and a bounded tail of `.toas/events.jsonl`. The original transcript had a failed Vim `TOAS:RUN` wrapper; direct CLI preview refused that marker at line 560. For inspection, a temporary snapshot retained the transcript before `## TOAS:RUN 17f18462a3f4`, removing the entire failed-run region. The dogfood files were not edited, and no model call or tool execution was performed.

Actual command, run from the dogfood workspace:

```sh
TOAS_RPC_MODE=off toas step --preview-request --session /private/tmp/toas-inference-review-261010-session.md
```

The local run used the TOAS `.codex-local/bin/uvt run --no-sync --no-cache` wrapper with bytecode disabled. The portable command above identifies the CLI operation.

[Captured preview JSON](2026-10-10-state-inference-preview-request.json). Preview phase: `infer`; one `user` message containing an 8,279-character JSON packet. No separate system message appears in this preview. The decoded content is exactly equal to the recorded `request_packet` for the latest rejected transition `st_0fd3c8cc81064c2c86e8edb0a75d701e`. This verifies the TOAS packet, not any unseen provider/server chat-template behavior.

## Decoded Instructions

```text
Advance the supplied TOAS state using the latest observation.

Observation Ephemerality and Persistence:
- Observations are strictly single-turn ephemeral: tool results disappear from view
  after this step unless you persist relevant information into state.
- Retain insights, facts, and conclusions by summarizing them into state.notes.
- Retain code or data slices in state.artifacts using bounded slice references
  (<target>:<start>-<end> or (ref: <target>:<start>-<end>), e.g. ib_8f2a1c:23-85,
  .toas/scratch/ib_8f2a1c.txt:23-85, or src/toas/cli.py:100-145) or full block references
  ((ref: <block_id>), (ref: .toas/scratch/<block_id>.txt), or (ref: <target>)). Bounded references
  expand automatically during state-step packet preparation.
- Tool outputs exceeding thresholds spill to .toas/scratch/<block_id>.txt with a preview.
  Intentional bounded reads permit up to 500 lines without spilling: when ingesting spilled
  lists or files, read the complete file via read_file or reference it in state.artifacts
  rather than sipping only the tail, as single-turn ephemerality drops the previewed head
  unless persisted into state.
- Do not manually transcribe file listings, diffs, or raw tool outputs into state.notes
  or report. Storing explicit references in state preserves them across turns, and references
  in report expand into complete user output upon completion.

Return one JSON object with these fields:
- state_patch: an object containing the changes to the current state. Use null to
  remove a key.
- tool_calls: an array of batch tool calls, each with tool_name and args matching
  the tool argument definitions and type signatures. Use an empty array when no tools are needed.
- continue_on_error: optional boolean; set true (or set continue_on_error: true on
  individual tool calls) to execute all batch calls without aborting on tool failure (useful for speculative or exploratory batches).
- outcome: optional; use continue or complete. A complete outcome means the
  goal is done and cannot include tool calls.
- report: optional string; provide a concise user-facing report or direct answer
  to the user's goal when completing the task (outcome: complete) or sharing
  intermediate progress. Explicit references (such as (ref: <target>) or
  (ref: <target>:<start>-<end>)) expand automatically in the final report.

Available tools, argument definitions, type signatures, and the tool protocol are supplied alongside
the state. Propose tool calls only; TOAS validates and executes them on a later explicit step.
Inference and tool execution are separate operations. Return JSON only.
```

## Decoded Response Schema

```json
{
  "state_patch": "object",
  "tool_calls": [
    {
      "tool_name": "string",
      "args": "object"
    }
  ],
  "continue_on_error": "boolean (optional)",
  "outcome": [
    "continue",
    "complete"
  ],
  "report": "string"
}
```

Advertised tool protocol: TOAS batch calls; validate and execute only on a later explicit step.

## Rejected Responses

The four failures below are logged as `failure_phase: response_validation`. None contains a JSON state proposal after its prose. Each falls back to XML-style tool calling. These are missing-proposal failures, not merely valid proposals rejected because they have a prose prefix.

### st_c23c5ffa52c74266aaf8879988fca827

```text
Let me explore the codebase to understand the current implementation of the CLI and the preview-request feature.

<tool_call>
<function=shell>
<parameter=argv>
["rg", "--files-with-matches", "preview.request|preview_request", "-i", "src/toas"]
</parameter>
</function>
</tool_call>
```

### st_202387828c594fb0a5eab255d00fab3f

```text
Let me start by exploring the current implementation to understand where `--preview-request` is handled.

<tool_call>
<function=read_file>
<parameter=path>
AGENTS.md
</parameter>
</function>
</tool_call>
```

### st_21b594c4be584b25a202eec211da2e66

```text
I need to look at the actual `_run_step` and `run_step` implementations in detail to understand how `--preview-request` works and where I'll add the `--pretty` flag.

<tool_call>
<function=shell>
<parameter=argv>
["sed", "-n", "196,270p", "src/toas/cli.py"]
</parameter>
</function>
</tool_call>
```

### st_0fd3c8cc81064c2c86e8edb0a75d701e

```text
Let me analyze the observation carefully before proceeding.

**Observation analysis:**
- Tool outcomes at index 0 and 1 show grep/rg results (already executed): they reveal `src/toas/cli.py` structure — `_run_step` at line 198, `run_step` at 235, `preview_request` handling at lines 228-255, and help text at lines 91, 129-130.
- A control result notes the shell grant was updated (effective: awk, cat, echo, find, head, ls, pwd, rg, sed, tail, wc).
- These results are single-turn ephemeral; I must persist the relevant findings into state before they drop.

**Key facts to persist:**
- `_run_step` (cli.py:198) builds a `kwargs` dict; when `preview_request` is set (lines 246-255) it does `kwargs["preview_request"] = True`, then calls `run_operator_step_once(**kwargs)` at line 232.
- `run_step` (cli.py:235) is the dispatcher; help text lines 91/129-130 document `--preview-request`.
- I still need to see the actual body of `_run_step` and how `preview_request` flows into `run_operator_step_once` (in `operator_api.py`) to find where the request messages are printed.

**Next steps:** I should read the relevant slices of `src/toas/cli.py` and locate `operator_api.py` / `step.py` to find where the preview request payload is rendered. Let me explore before implementing.

Let me persist the findings and launch exploratory reads in parallel.

<tool_call>
<function=shell>
<parameter=argv>
["rg", "-n", "preview_request", "src/"]
</parameter>
</function>
</tool_call>
```

## Operator-Perspective Assessment

The requested JSON contract is present, but the request offers an abstract schema instead of a worked response. Its instructions are embedded in the same JSON string as state and observations, begin with persistence details, and end with a strict JSON-only rule. That rule conflicts with the newly requested tolerance for explanatory prose. These are prompt clarity opportunities; the evidence does not establish why this particular model chose XML tool syntax.

The latest packet observation contains `operator_observation`, `tool_outcomes`, `user_inputs`, and `control_results`. The outcomes are the two successful grep results. It contains no preceding format-rejection diagnostic or rejected response. Repeating inference therefore supplies no explicit instruction to correct the demonstrated format error.

A useful final proposal example would put both retained findings and proposed tools in the required envelope:

```json
{
  "state_patch": {
    "notes": {
      "findings": [
        "The CLI delegates preview handling to the operator API."
      ]
    }
  },
  "tool_calls": [
    {
      "tool_name": "read_file",
      "args": {
        "path": "src/toas/operator_api.py"
      }
    }
  ],
  "outcome": "continue"
}
```

This example is a proposed instruction improvement, not a change to the active packet. Prefix tolerance should still require one unambiguous validated proposal. Tool-only XML and prose cannot supply a missing state update. Format repair should preserve state and tool authority, and its timing remains an explicit task decision.

## Parser and Validation Evidence

`src/toas/runtime/state_step.py::_parse_state_response` currently calls `json.loads` on bare content, stripping only a whole-response Markdown fence. The inference validator uses `response.get("state_patch", {})`, so an omitted patch silently becomes empty if the remaining JSON validates. The task records required-field clarity and prose-prefix tolerance as separate concerns.

## Successful Versus Failed Context Comparison

The earlier accepted transition `st_b0c9fc434f7748ddae666d60b8e709e3`
retains actual `model_call.request_messages`, even though the separate
minimal-trace `llm_call` projection omits them. Comparing that accepted request
with the first XML-style failure `st_c23c5ffa52c74266aaf8879988fca827`:

- Both contain one user message with the entire packet serialized as JSON.
- `instructions`, `schema`, and `tools` are exactly equal.
- Only `state` and `observation` differ at the packet's top level.
- The accepted request has empty initial state plus the two `cat` results
  (AGENTS.md and the task) and the original user shell commands.
- The failed request has the populated implementation goal/state and a control
  result, with zero tool outcomes. That control result includes trailing `/run`.
- Later XML-style failures persist after the two successful grep observations
  are supplied, so absent tool outcomes alone do not explain the switch.
- Accepted and failed model-call records report the same returned model,
  `Qwen3.8-27B-Q8_0.gguf`, despite the configured `qwen3.5-35b-a3b` alias.

There is no demonstrated instruction, schema, tool advertisement, JSON
representation, or reported model change explaining why an example suddenly
became necessary. An example is a proposed robustness measure, not an established
diagnosis. Different task/state/observation content may influence the model's
response, but these records do not prove a causal trigger or expose all server
chat-template/sampling state.

## Live Invocation Boundary Check

Investigated whether preview might show a state packet while inference sends
the transcript. Every inspected XML-style rejection retains
`model_call.request_messages` containing one user message whose decoded JSON
equals its recorded `request_packet`, including the state object.

The live path is `generate_state_packet` -> `prepare_state_request` ->
`resolve_model_invocation(request_messages=..., working=[])` ->
`_call_model_once(messages=plan.messages)` -> the OpenAI driver. Supplying
explicit request messages bypasses conversation transcript projection.
Recorded `transport_mode: null` means the normal `chat_messages` mode in this
code; the current dogfood configuration also resolves to `chat_messages`.
The transcript-style `single_user_blob` transformation exists but is not the
recorded mode for these failures.

A local, network-free capture replaced the SDK client's `create` method and
passed the recorded failed packet through request preparation and the driver.
Messages at the SDK call were exactly equal to the recorded failed messages,
and the complete state was present. Current provider was `openai`; generation
extras contained only `chat_template_kwargs`, with no `messages` override.

This supports correct TOAS delivery up to the SDK call. It is not a historical
HTTP capture or proof of the server's rendered/tokenized prompt. Server-side
request/template inspection would address that remaining boundary. The rejected
response itself discusses ephemeral observations and persisting findings into
state, which also suggests it saw state-step instructions despite choosing the
wrong output format.

The later offline replay also passes through the installed SDK serializer.
Saved artifacts: [readable request](2026-10-10-state-inference-sdk-request.md),
[SDK call arguments](2026-10-10-state-inference-sdk-request.json), and
[SDK-serialized HTTP body](2026-10-10-state-inference-http-body.json).
The exact recorded messages survive both boundaries. `extra_body` is merged
into the serialized HTTP body as `chat_template_kwargs`; it does not replace
the messages. This capture uses current settings and a mock transport, rather
than recovering the historical on-wire request.
