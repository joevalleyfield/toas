Filed as: 260623-host-stdio-llm-error-surfacing-probe
FKA:
AKA: host-stdio request-shape failure probe; async llm error surfacing repro switch
Legacy index:

keywords: runtime, host-stdio, async, llm, error, surfacing, probe, debug

# Host-stdio LLM error surfacing probe

Parent: `260623-host-stdio-llm-failure-surfacing`
Related: `260614-model-backend-failure-handoff`

## Current Reality

The host-stdio path is expected to surface failed runs visibly, but we need an
easy end-to-end repro path that forces a provider-facing request-shape failure
without relying on an external backend quirk or changing default behavior.

## Desired Reality

TOAS has a narrow, opt-in debug probe that intentionally corrupts the outgoing
LLM request shape so host-stdio async failure surfacing can be exercised on
demand.

## Scope

- Add a boundary-only debug hook at LLM request construction time.
- Keep default behavior unchanged.
- Prefer an env-controlled mode so the probe works through host-stdio and other
  adapter surfaces without broader config/API design work.

## Acceptance

- With the probe unset, normal request-shape omission behavior remains intact.
- With the probe enabled, TOAS sends a deliberately bad shape suitable for
  end-to-end failure-surfacing reproduction.
- Focused tests pin both normal and probe-on request shapes.

## Completed

- Added `TOAS_DEBUG_BREAK_LLM_REQUEST_SHAPE=max_tokens_null` at the LLM
  request boundary so host-stdio debugging can deliberately reintroduce a bad
  `max_tokens: null` field.
- Kept the default unbounded request shape unchanged when the probe is unset.
- Added focused regression coverage for both normal omission behavior and the
  opt-in malformed-shape path.
