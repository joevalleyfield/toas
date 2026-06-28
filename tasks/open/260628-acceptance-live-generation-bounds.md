Filed as: 260628-acceptance-live-generation-bounds
FKA:
AKA: live acceptance max_tokens cap; per-mode timeout; runaway generation insurance
Legacy index:

keywords: acceptance, generation, max_tokens, timeout, live, hardening, follow-on

Parent:
Related: `260628-acceptance-suite-revival`; `260628-acceptance-live-prompt-realism`

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

## Exit Evidence

- [ ] live/hybrid acceptance generations terminate without relying on a fast MoE
- [ ] non-replay timeout is sized for real generation (no 20s blanket cancels)
- [ ] `replay_only` remains fast and unchanged
