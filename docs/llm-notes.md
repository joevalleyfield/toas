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

## Core Probe Results

Source:
- `uv run toas-llm-harness --timeout-s 20`

### Exact Surface Control

Observed:
- prompt: `Reply with exactly OK.`
- thinking on:
  - exact `content` match succeeded
  - non-empty `reasoning_content` was returned
  - latency was about `2.2s`
- thinking off:
  - exact `content` match succeeded
  - `reasoning_content` was absent
  - latency was about `96ms`

Likely implication:
- simple exact-output constraints are workable
- the corrected no-thinking request shape has a large practical effect

### Exact JSON

Observed:
- prompt: `Reply with exactly {"ok":true}.`
- thinking on:
  - exact `content` match succeeded
  - JSON parseability succeeded
  - non-empty `reasoning_content` was returned
  - latency was about `5.8s`
- thinking off:
  - exact `content` match succeeded
  - JSON parseability succeeded
  - `reasoning_content` was absent
  - latency was about `154ms`

Likely implication:
- simple exact JSON is robust on this endpoint when the request is shaped correctly

### YAML / Tool-Call Shape

Observed:
- prompt asking for only a fenced YAML block with one echo call
- thinking on:
  - timed out at `20s`
- thinking off:
  - succeeded
  - returned a fenced YAML block
  - `reasoning_content` was absent
  - latency was about `321ms`

Likely implication:
- YAML is not inherently the problem on this endpoint
- the bigger issue is whether hidden reasoning is active

### JSON Action Shape

Observed:
- prompt: `Return only JSON with the shape {"tool_name":"echo","text":"hi"}.`
- thinking on:
  - JSON parseability succeeded
  - non-empty `reasoning_content` was returned
  - latency was about `3.4s`
- thinking off:
  - JSON parseability succeeded
  - `reasoning_content` was absent
  - latency was about `243ms`

Likely implication:
- JSON and YAML can both be viable action lanes here when the request flags are correct

## Request-Shape Correction

Observed:
- an earlier TOAS probe path sent a literal top-level field named `extra_body`
- that did not match how the OpenAI SDK actually sends `extra_body`
- the sister repo uses the SDK, which merges:
  - `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`
  into the real request body
- once TOAS switched to the SDK and the direct harness flattened `chat_template_kwargs` into the top-level JSON body, the endpoint started suppressing hidden reasoning as expected

Likely implication:
- the earlier “thinking off still returns reasoning” result was a probe bug, not a stable endpoint property
- request-shape correctness matters enough to change both latency and output behavior dramatically

## Current TOAS Policy

Observed in runtime:
- TOAS generation uses the OpenAI client
- TOAS generation sends the no-thinking request knob by default
- `llm_call` records now have explicit trace granularity:
  - default `TOAS_LLM_TRACE=minimal`
  - optional `TOAS_LLM_TRACE=full` for forensic capture
- minimal mode records:
  - `requested_model`
  - `response_model` when present
  - `trace_mode`
  - `input_count`
  - visible `response.content`
  - `response.has_reasoning_blocks` (detected from `<think>...</think>`)
  - `response_has_reasoning_content` when the backend returned hidden reasoning fields
- full mode additionally records:
  - full projected request `messages`
  - hidden `response.reasoning_content` when returned
- transcript-visible assistant output still uses only `response.content`
- projected model-input context strips assistant `<think>...</think>` blocks by default before subsequent model calls

Likely implication:
- durable records preserve failure/debug signals by default without always paying full forensic storage cost
- full forensic payload remains opt-in when deep tracing is needed
- reasoning visibility and reasoning roundtrip are now separated by policy

## What The 170 Series Established

Observed:
- the harness now compares thinking-on vs thinking-off behavior
- the harness reports timing, parseability, hidden reasoning presence, and structured failures
- the harness can also write a report to an output file for archiving and later comparison

Likely implication:
- the endpoint characterization arc is now in a state where future protocol work can build on evidence instead of conversational memory

## Open Questions

- Which action terms are most likely to collide with provider-native tool semantics on more hostile backends?
- How much entrainment is needed before a backend reliably stays inside the TOAS action lane?
- Which prompt variants best avoid protocol collision when the backend has a hidden system prompt and its own tool protocol?
