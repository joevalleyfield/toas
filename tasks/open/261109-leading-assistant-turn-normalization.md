Filed as: 261109-leading-assistant-turn-normalization
FKA:
AKA: leading assistant turn marker normalization; strip leading TOAS:ASSISTANT; echoed turn marker ingress stripping; assistant marker escape fix
Legacy index:

keywords: active, bugfix, runtime, llm, normalization, streaming, projection, transcript

Related: `373`; `260828-generation-boundaries-and-bounds`

# Leading Assistant Turn Marker Ingress Normalization

## Intent

Normalize model completions that echo leading `## TOAS:ASSISTANT` turn headers at the generation and streaming ingress boundaries before they enter assistant message content and get escaped as `\## TOAS:ASSISTANT`.

## Context & Motivation

When models (including frontier models like GPT 5.6 Terra under `single_user_blob` mode, or models prompted with transcript framing) generate completions that begin with a turn header like `## TOAS:ASSISTANT\n\n`, TOAS currently treats the entire completion as message body content.

During transcript projection, `escape_transcript_content` in `src/toas/transcript.py` escapes any line matching `_ROLE_MARKER_LINE_RE` with a leading backslash to prevent collision with structural markers. As a result, the transcript renders as:

```text
## TOAS:ASSISTANT

\## TOAS:ASSISTANT
...
```

Furthermore, `unescape_transcript_content` unescapes this back into the durable event history on the next turn, entraining the model into continuing to emit the header in subsequent turns.

Symmetrically to `_truncate_assistant_turn_overrun` (which normalizes trailing hallucinated `## USER` turns in `src/toas/llm.py`), TOAS should normalize leading assistant role markers at the ingress/completion boundary, stripping the echoed header and leading whitespace so only substantive assistant content is preserved as `node["content"]`.

## In Scope

- [ ] Define leading assistant turn marker matching (e.g. `^\s*## TOAS:ASSISTANT(?:/[^\s\r\n]+)?(?:\s+[^\r\n]*)?(?:\r?\n)+` and `^\s*## ASSISTANT(?:\r?\n)+`) in `src/toas/llm.py`.
- [ ] Strip leading turn marker headers in `complete_chat_response` before building the completion payload.
- [ ] Ensure streaming escaper (`ClosedSetMarkerStreamEscaper` in `src/toas/cli_streaming.py`) or presenter suppresses/swallows an initial leading `## TOAS:ASSISTANT` turn header line rather than streaming an escaped `\## TOAS:ASSISTANT`.
- [ ] Add unit and regression tests in `tests/test_llm.py` and `tests/test_cli_streaming.py` while maintaining 100.00% statement coverage.

## Out of Scope

- Modifying prompt assets or changing `single_user_blob` tail framing constraints.
- Altering the closed-set escaping rules for markers genuinely contained in the body or code fences.

## Acceptance Criteria

1. Raw assistant completions starting with `## TOAS:ASSISTANT` have the leading marker stripped before becoming `node["content"]`.
2. The projected transcript contains only the canonical `## TOAS:ASSISTANT` turn header with no `\## TOAS:ASSISTANT` artifact.
3. Both streaming and non-streaming modes handle the leading marker consistently without emitting escape prefixes for the turn header.
4. All existing and new tests pass with 100.00% statement coverage on modified modules.
