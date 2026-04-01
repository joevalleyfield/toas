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
