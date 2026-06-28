Filed as: 260628-acceptance-per-step-hybrid-generation
FKA:
AKA: hybrid honor should_use_live for generation; per-step model stub; targeted live step
Legacy index:

keywords: acceptance, hybrid, generation, stub, harness, test, follow-on, refactor

Parent:
Related: `260628-acceptance-suite-revival`; `260628-acceptance-live-prompt-realism`

# Acceptance Per-Step Hybrid Generation

## Current Reality

The acceptance fixture installs the replay generation stub
(`toas.runtime.step_generation_runtime.generate_assistant_message`) only when
`backend_cfg.mode == "replay_only"`. In `hybrid` and `live_only` it is never
installed, so every generating step calls the live backend.

`should_use_live(step_index, step_label, step_labels)` exists and is consulted —
but only inside `when_implement`, and only to choose the *fixture data* (the
`change_line` text written into the transcript), never to gate model generation.

Net effect: `hybrid` behaves like `live_only` for model generation. It does not
honor `--acceptance-live-from-step` / `--acceptance-live-from-label` for the
model. So you cannot say "replay the setup steps, only go live on the step I
care about." This is what made the live diagnosis expensive (every step hit the
backend) and is a naming/expectation mismatch.

## Desired Reality

In `hybrid`/`live_only`, install a generation shim (instead of an
unconditional pass-through) that, per call, consults `should_use_live` against a
running generating-step index and either:

- returns the deterministic replay stub (early / pre-live-from steps), or
- falls through to the real `generate_assistant_message` (at/after the chosen
  live-from step).

`replay_only` stays all-stub; `live_only` stays all-live; `hybrid` becomes
genuinely per-step.

## Design Notes / Open Seam

- There is no global generating-step counter today; generating steps are spread
  across separate `@when` functions (`posture`, `stage_frontier`, `implement`,
  ...). The shim needs a counter (e.g. in `acceptance_state`) incremented per
  model call, mapped to the existing `live_from_step` / `live_from_label`
  semantics (the label map is currently local to `when_implement`).
- Prefer spike-first: locate where the counter should live and how labels map to
  call order before committing to the shim wiring. Keep `replay_only` green and
  unchanged throughout.

## Exit Evidence

- [ ] `hybrid --acceptance-live-from-step N` replays steps < N and goes live at
  steps >= N (verified by which steps hit the backend)
- [ ] `replay_only` and `live_only` behavior unchanged
- [ ] suite stays green in `replay_only`
