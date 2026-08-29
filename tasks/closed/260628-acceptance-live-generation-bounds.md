Filed as: 260628-acceptance-live-generation-bounds
FKA:
AKA: live acceptance max_tokens cap; per-mode timeout; runaway generation insurance
Legacy index:

keywords: acceptance, generation, max_tokens, timeout, live, hardening, follow-on

Parent:
Related: `260828-generation-boundaries-and-bounds`

Claimed for implementation on 2026-08-28: use the existing in-session
`/config set generation.max_tokens` affordance as the first acceptance
hardening slice.

# Acceptance Live Generation Bounds

## Current Reality

In live/hybrid mode, acceptance generations are unbounded
(`generation.max_tokens` defaults to 0 -> `backend_policy` maps `0 or None` ->
`None` -> the request omits `max_tokens`). The global `pytest-timeout`
`timeout = 20` in `pyproject.toml` is sized for the fast `replay_only` path.

Empirically (260628): a dense ~26B model at ~30 t/s could not reach a stop token
within 20s on the context-free acceptance prompt, so every live generation was
cancelled at the timeout. Swapping to a Qwen3.6 35B A3B (MoE, ~3B active) made
hybrid pass in ~24s total because the higher t/s reaches the natural stop in
time. So today this is NOT blocking — but it is fragile: a slower model, a
longer response, or a CI runner without the MoE will time out again.

## Desired Reality

Defensive, low-priority insurance so live/hybrid acceptance is robust to model
speed and response length:

- a bounded `max_tokens` for acceptance generations (e.g. seed
  `generation.max_tokens` in the cloned workspace, or add `/config set
  generation.max_tokens <n>` to the minimal-posture step) so generations
  terminate predictably
- a right-sized timeout for non-`replay_only` runs (the 20s blanket is a replay
  number; live needs more, or `--timeout=0` / a per-mode override)

## Notes

- Most of the real win here may instead come from
  `260628-acceptance-live-prompt-realism`: a realistic projected prompt makes a
  bounded, terminating response far more likely, which reduces the need for a
  hard cap. Sequence this after that decision.
- Do not perturb `replay_only` timing/behavior (the stub ignores `max_tokens`).
- The first implementation slice uses the existing operator configuration
  affordance in the minimal-posture step: `/config set generation.max_tokens
  1024`. This keeps the acceptance change on the ordinary runtime path and
  avoids adding a test-only backend or seed setting.
- Proposed timeout policy: acceptance replay-only uses a 5-second per-test
  safeguard; live-only and hybrid use 60 seconds. An explicit pytest
  `--timeout` value overrides these defaults.

## Exit Evidence

- [x] live/hybrid acceptance generations terminate with the configured 1024-token
  cap; hybrid acceptance passed in 37.53s on 2026-08-28
- [x] acceptance timeout defaults are mode-specific: 5 seconds for replay-only
  and 60 seconds for live-only/hybrid, with explicit `--timeout` override
- [x] `replay_only` remains fast and unchanged: 9 acceptance scenarios passed in
  0.96s on 2026-08-28

## Implementation Evidence

- `tests/acceptance/steps/test_complete_change_request_steps.py` now configures
  `generation.max_tokens` through `/config set` alongside the disabled-thinking
  posture.
- Replay acceptance: `9 passed in 0.96s`.
- Hybrid acceptance: `9 passed in 37.53s`.
- The timeout question remains deliberately open for a follow-up measurement;
  this slice changes generation length, not pytest timeout policy.

## Closure

Closed after adding the existing `generation.max_tokens` session affordance and
mode-specific acceptance timeouts. The remaining production generation-boundary
work is tracked separately in `260828-generation-boundaries-and-bounds`.
