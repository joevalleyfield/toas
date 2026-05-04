# 474 Bootstrap Session Seed And Shared Tools Guidance Source

## Objective
Add a config-driven bootstrap seed prompt for empty/new sessions and unify `/help tools` + bootstrap tool guidance behind one shared source to prevent subtle drift.

## Why
- Current operator flow often requires extra control turns before weak models behave productively.
- Bootstrap behavior should be explicit and config-governed, not hidden policy.
- `/help tools` and prompt/template guidance are under pressure to diverge when maintained separately.

## Scope
In scope:
- Add one config key for bootstrap seed prompt ref (nullable).
- Render seed only at true bootstrap (no durable turns yet).
- Keep seed generation through existing prompt/template composition.
- Introduce a shared tools-guidance source and consume it from both `/help tools` and bootstrap composition.
- Add tests for bootstrap gate semantics and shared guidance consistency.

Out of scope:
- New slash-command surface for seed management.
- Multiple seed profiles or policy matrix expansion in first pass.
- Broader prompt-library redesign beyond what is needed for shared-source adoption.

## Proposed Shape
- Config key: `session.bootstrap_prompt_ref` (string ref or null).
- Default: current collaborative session-start template ref.
- Semantics:
  - `toas step` on empty/no-turn session emits bootstrap content.
  - Once any durable turn exists, no auto-bootstrap re-render.
  - Truncating transcript/history back to no-turn state allows reseed.
- Shared guidance:
  - Define one tools-guidance core renderer/data source.
  - `/help tools` and bootstrap template composition each render from that source (different presentation formats allowed).

## Verification
- Unit tests for:
  - bootstrap enabled/disabled behavior,
  - no-turn gate and post-turn non-rerender,
  - reseed after full truncate,
  - `/help tools` and bootstrap guidance sourced from same core set.
- Full suite:
  - `uv run pytest`

## Tracking
- Status: completed
- Owner: codex+operator pairing
- Opened: 2026-05-03
- Completed: 2026-05-04
- Notes:
  - Added `session.bootstrap_prompt_ref` with default session-start template reference.
  - Bootstrap emits seed content only when there are no durable working turns.
  - Shared tools guidance source is used by `/help tools` and prompt guidance composition.
  - Added tests for bootstrap gate semantics and guidance composition consistency.
