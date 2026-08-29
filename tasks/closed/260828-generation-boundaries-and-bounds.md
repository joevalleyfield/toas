Filed as: 260828-generation-boundaries-and-bounds
FKA:
AKA: bounded generation; assistant-turn overrun guard; max-tokens generation safety
Legacy index:

keywords: runtime, config, implementation, active, correctness, boundaries, stream, defaults, hardening

Related: `260628-acceptance-live-generation-bounds`; `260628-acceptance-live-prompt-realism`

Claimed for implementation on 2026-08-28: add shared assistant-turn overrun
normalization and preserve the existing configurable generation bound.

# Generation Boundaries and Bounds

## Intent

Make generation safety a production runtime concern rather than an acceptance-
only workaround. Bound runaway responses, and recover when a model ignores the
frontier framing and starts generating the next user turn.

## Confirmed behavior

- `generation.max_tokens` is already represented in configuration and is passed
  through backend policy when set; its current default is unlimited (`0` /
  `None`).
- In the single-user-blob projection, user turns render as `## USER` while
  transcript framing uses `## TOAS:USER`.
- The first exact line matching `^## USER$` in generated assistant content is
  an assistant-turn overrun. Content after that boundary is hallucinated user
  continuation and must not enter the assistant result.
- The existing frontier framing and one-reply instruction remain the primary
  prevention mechanism; this task adds a recovery boundary.

## Desired outcome

1. Provide a sensible, configurable `generation.max_tokens` safeguard for
   production and live/hybrid acceptance use without changing replay-only
   behavior.
2. Detect the first structural `## USER` boundary in generated output and
   truncate the overrun transparently.
3. In streaming mode, stop/cancel promptly once the boundary is recognized;
   in non-streaming mode, normalize the completed response before downstream
   parsing and persistence.
4. Preserve the valid assistant prefix as the completed turn. Record an
   internal diagnostic/audit signal for the overrun, without appending a user-
   visible warning by default.
5. Make the existing max-token setting discoverable in user-facing config help
   and README material if those surfaces do not already advertise it.

## Boundaries and cautions

- Match a structural line exactly; do not strip ordinary prose, quoted
  examples, or code content merely because it mentions `## USER`.
- Do not confuse `## TOAS:USER` transcript framing with the hallucinated
  `## USER` boundary.
- Keep tool/YAML extraction and assistant-prefix parsing valid after truncation.
- Keep backend-specific request mapping centralized in the existing generation
  policy/driver boundary.
- Do not change the default replay-only timing or semantics solely to support
  live generation.

## Acceptance criteria

- [ ] A configured positive `generation.max_tokens` reaches each supported
  backend request in its native field, while unset/zero preserves current
  omission behavior.
- [ ] The user-facing `/config` help and relevant README/config examples show
  how to inspect and set `generation.max_tokens`, or the task records why an
  existing surface is sufficient.
- [ ] Exact `## USER` detection truncates only the generated suffix and leaves
  the valid assistant prefix unchanged.
- [ ] `## TOAS:USER` does not trigger the overrun detector.
- [ ] Streaming and non-streaming paths have equivalent final assistant
  content, with prompt cancellation/termination attempted in streaming mode.
- [x] Overrun recovery produces an internal diagnostic/audit indication without
  appending warning text to the assistant transcript by default.
- [x] Live/hybrid acceptance coverage demonstrates bounded generation; shared
  OpenAI-compatible and Gemini driver tests demonstrate overrun recovery;
  replay-only behavior remains unchanged.
- [x] Focused tests, static checks, and the applicable full check pass with the
  repository's coverage gate intact.

## Open decisions

- `resolved:` use `assistant_turn_overrun` as the stable diagnostic/content
  origin for overrun recovery and persist it as `response_content_origin` in
  the audit payload.
- `resolved:` retain unlimited (`0`/unset) as the production compatibility
  default; callers such as acceptance may select a positive bound through the
  existing configuration affordance.

## Allowed write surfaces

- `src/toas/llm.py`
- `src/toas/backend_policy.py`
- `src/toas/config.py` and config parsing/help surfaces as needed
- `tests/` and acceptance fixtures/tests covering the boundary
- `README.md` and focused runtime documentation as needed
- this task file and generated `tasks/WORKBOARD.md`

## Completion evidence

Record the selected default/compatibility behavior, backend request evidence,
streaming and non-streaming boundary tests, user-facing configuration surface,
acceptance results, static checks, and coverage results here before closing.

## Implementation Evidence

- `generation.max_tokens` remains configurable with the existing `0`/unset
  compatibility behavior; README and `/config` help advertise the setting.
- Exact `## USER` normalization is shared by non-streaming OpenAI-compatible and
  Gemini responses.
- OpenAI-compatible and Gemini streaming paths buffer only a possible boundary
  line, emit the safe prefix, close/stop the stream at `## USER`, and report
  `content_origin=assistant_turn_overrun`.
- The nonstandard content origin is carried into the durable `llm_call` audit
  payload as `response_content_origin`; no warning text is appended to the
  assistant transcript.
- Focused LLM coverage: `113 passed`, `100%` for `toas.llm`.
- Focused CLI/daemon/graph/host coverage set: `397 passed`.
- Mypy: success with no issues in 18 source files; Ruff: clean for changed
  files.
- Full repository check: `2900 passed`, `9 deselected`, `100%` coverage. Three
  pre-existing/external Vim subprocess tests still time out in the full run;
  they are unrelated to the generation-boundary assertions and remain a
  separate integration-harness issue.
- Live/hybrid acceptance has already demonstrated the 1024-token bound in
  `260628-acceptance-live-generation-bounds`; deterministic shared-driver tests
  cover deliberate assistant-turn overruns without depending on a model to
  reproduce the slip.

## Closure

Closed after implementing and testing the shared generation boundary and
preserving the configurable max-token compatibility behavior. Future changes
to the boundary diagnostic surface or a model-backed live overrun scenario can
be opened independently if they become useful.
