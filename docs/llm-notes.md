# LLM Endpoint Notes

These notes capture observed behavior from live probes against the current local OpenAI-compatible endpoint.

This file should distinguish:
- observed behavior
- likely implications
- possible mitigations

It should not blur those into one thing.

## Endpoint

Observed on April 1, 2026:

- base URL: `http://localhost:8080/v1`
- health endpoint: `{"status":"ok"}`
- reported model id: `Qwen3.5-35B-A3B-UD-Q8_K_XL.gguf`
- requested model alias `qwen3.5-35b-a3b` was accepted successfully

## Initial Probe Results

Source:
- `uv run toas-llm-harness --timeout-s 8`

### Exact Surface Control

Observed:
- prompt: `Reply with exactly OK.`
- returned `content`: `OK`
- exact match succeeded

Likely implication:
- simple exact-output constraints may be workable at the visible `content` layer

### Exact JSON

Observed:
- prompt: `Reply with exactly {"ok":true}.`
- returned `content`: `{"ok":true}`
- exact match succeeded
- JSON parseability succeeded

Likely implication:
- trivial JSON exactness is possible under simple prompts

### Hidden Reasoning Payload

Observed:
- both successful exact-output probes returned non-empty `reasoning_content`
- the visible `content` still matched the requested output exactly

Likely implication:
- TOAS needs an explicit policy for whether `reasoning_content` is ignored, recorded, or stripped
- hidden extra fields may not be show-stoppers, but they are not safe to forget about

### YAML / Tool-Call Shape

Observed:
- prompt asking for only a fenced YAML tool-call block timed out under an 8-second per-request limit

Likely implication:
- structured-output prompting may be slower or less robust than trivial exact-output cases
- agentic workflows should not assume YAML/tool-call responses are equally easy for the endpoint

## Open Questions

- Does longer timeout make the YAML scenario succeed reliably?
- If it succeeds, does it include hidden `reasoning_content` as well?
- How often does exact visible output stay exact under stronger system prompts?
- Should TOAS preserve returned concrete model ids in `llm_call` records in addition to requested aliases?

## Thinking-On vs Thinking-Off Comparison

Source:
- `uv run toas-llm-harness --timeout-s 12`
- comparison run using `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`

### Request Knob

Observed:
- the nearby `Eaten` repo uses `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`
- TOAS now uses the same request-side knob for generation

Likely implication:
- request-shape control is better than prompt hacks for trying to suppress visible thinking

### Exact Visible Output

Observed:
- both `exact_ok` and `json_exact` still succeeded with exact visible `content`
- this held with thinking on and with the no-thinking request knob

Likely implication:
- simple exact-output constraints remain workable at the visible `content` layer in both modes

### Hidden Reasoning Still Present

Observed:
- `reasoning_content` remained present in both modes
- the no-thinking request knob reduced reasoning payload size somewhat on simple probes, but did not remove it

Likely implication:
- TOAS should not assume `enable_thinking: false` fully suppresses hidden reasoning fields on this endpoint
- normalization policy still needs to handle `reasoning_content` explicitly

### YAML Tool-Call Fragility

Observed:
- the YAML fenced-block scenario timed out at 12 seconds with thinking on
- it also timed out at 12 seconds with thinking off

Likely implication:
- YAML/tool-call prompting is currently fragile enough that TOAS should not lean on it without repair/extraction help
- JSON-first structured prompting is currently the safer shape to test and build around

### JSON Tool-Call Comparison

Observed:
- a JSON tool-call prompt succeeded with thinking on
- the same prompt timed out at 12 seconds with thinking off

Likely implication:
- the no-thinking request knob is not uniformly beneficial
- prompt/runtime policy should be driven by scenario evidence, not by assuming one mode dominates

## Current TOAS Policy

Observed in runtime:
- TOAS generation requests use the no-thinking request knob by default
- `llm_call` records now distinguish:
  - `requested_model`
  - `response_model`
  - visible `response.content`
  - hidden `response.reasoning_content` when returned
- transcript-visible assistant output still uses only `response.content`

Likely implication:
- durable records preserve response-side facts without letting hidden fields leak into transcript-visible consequences
- the default no-thinking mode is still a provisional choice and may need revisiting as structured-output probes expand

## Updated Open Questions

- Should TOAS keep defaulting generation to no-thinking if JSON tool-call prompts are slower or less reliable in that mode?
- Should `reasoning_content` always be preserved in `llm_call` records, or only when explicitly probing/debugging?
- Which JSON tool-call prompt shapes are robust enough to support extraction/repair work?
- At what timeout budget, if any, do YAML tool-call prompts become practical on this endpoint?
