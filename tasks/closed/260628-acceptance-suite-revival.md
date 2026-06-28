Filed as: 260628-acceptance-suite-revival
FKA:
AKA: fix bitrotted acceptance tests; bring acceptance back online; replay_only acceptance repair
Legacy index:

keywords: acceptance, test, bitrot, replay, regression, follow-on, maintenance

Parent:
Related: `260628-transcript-writeback-surface-unification`

# Acceptance Suite Revival

## Current Reality (at filing)

The acceptance scenarios under `tests/acceptance/` are excluded from the default
suite via the `-m "not acceptance"` addopts in `pyproject.toml`, so they ran
green in neither CI nor local default runs. Several had silently bitrotted and
errored at fixture setup or on stale assertions. This surfaced while closing
`260628-transcript-writeback-surface-unification` (the acceptance recovery step
used the now-removed `rebuild_session`).

Confirmed pre-existing on `b93f8487` / `@--`, independent of the rebuild
removal:

- `test_complete_change_request_steps.py`: the `replay_only` fixture
  monkeypatched `toas.cli.generate_assistant_message`, but the cli-thinning
  refactors (`db5882cc`, `39a9e602`) moved that seam into
  `toas.runtime.step_generation_runtime` and dropped the cli import →
  `AttributeError` at fixture setup.
- same file: `then_recovered` asserted a history line starting with
  `selected_head=`, but `50faa254` reformatted history output to
  `history: root-to-head lineage (<head_id>)`.
- `test_control_lane_multi_command_frontier_steps.py`: wrote the working
  transcript to `<repo>/session.md`, but the resolved default session path is
  `<repo>/.toas/session.md` → `FileNotFoundError`.
- same file: asserted bare `stdout:\nfirst-shell`, but shell stdout now renders
  inside a `toas-output` projection fence
  (`source=tool.shell potency=inert\n<stdout>`).

## Work Done

- Repointed the `replay_only` generation stub at
  `toas.runtime.step_generation_runtime.generate_assistant_message`, which
  `build_step_cli_deps()` reads at dep-build time, keeping the full generation
  runner pipeline intact for both sync (`step_once`) and async step paths.
- Updated the recovery history assertion to the current
  `history: root-to-head lineage` format.
- Fixed the control-lane session-file writes to `.toas/session.md`.
- Updated the mixed-intent ordering assertion to anchor on the durable shell
  RESULT block (`source=tool.shell potency=inert\n<stdout>`) rather than the
  streamed stdout copy that precedes the result lanes; source-order intent
  preserved.

## Exit Evidence

- [x] `uv run pytest tests/acceptance -m acceptance --no-cov` is green
  (9 passed) in the default `replay_only` backend mode, no live backend needed.
- [x] default suite remains green at 100% coverage (acceptance edits are
  test-only and excluded from the default run).

## Open Follow-ons

Spun out as their own tasks (260628):

- `260628-acceptance-replay-in-routine-checks` (under parent
  `260628-project-checks-and-ci-posture`) — acceptance is not in the default
  gate; make `replay_only` part of the routine check set so bitrot is caught.
  The parent owns the project's broader check/CI posture (old-school SOP, not
  modern CI/CD).
- `260628-acceptance-live-prompt-realism` — spike found live runs send a ~7-token
  bare user message (no system/bootstrap/capability projection); decide whether
  to enrich the scenarios or document live as a connectivity-only smoke test.
- `260628-acceptance-per-step-hybrid-generation` — make `hybrid` honor
  `should_use_live` for model generation, not just fixture data, so it can replay
  setup steps and only go live on a chosen step.
- `260628-acceptance-live-generation-bounds` — defensive `max_tokens` cap +
  per-mode timeout so live/hybrid doesn't depend on a fast MoE.

Empirical note (live/hybrid): a dense ~26B model at ~30 t/s timed out the 20s
per-test budget on the context-free acceptance prompt; a Qwen3.6 35B A3B (MoE)
passed `hybrid` in ~24s. Throughput, not "thinking", was the bottleneck.
