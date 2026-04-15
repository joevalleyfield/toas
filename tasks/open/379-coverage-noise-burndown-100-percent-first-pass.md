## Goal

Reduce future coverage-report noise by driving selected small/medium modules to `100%` so they disappear from the missing-lines output.

## Why Now

After the first ratchet checkpoint (`375`), the next leverage move is shrinking noisy report surface so future gaps are concentrated in genuinely hard modules.

## Scope

- prioritize modules already near-complete coverage (`95%+`) for quick elimination
- land narrow deterministic tests to close remaining uncovered lines
- keep task slicing explicit per module so progress remains auditable
- record and apply a preference for explicit callable/functor classes over closure-heavy local state where refactors are needed for testability

## Intended Behavior

- coverage report contains fewer near-complete modules
- remaining report entries are higher-signal targets for deeper reliability work

## Constraints

- no semantic drift in runtime behavior
- no broad rewrites in this pass; keep changes incremental and test-first

## Done When

- first set of `95%+` targets are either at `100%` or split into justified follow-ons
- roadmap and subtasks reflect completed/remaining burn-down targets

## Progress

- completed first target set:
  - `380` (`rpc_transport.py`) to `100%`
  - `381` (`transcript.py`) to `100%`
- completed second target set:
  - `382` (`rpc_client.py`) to `100%`
  - `383` (`capability_prompts.py`) to `100%`
- partial third target set:
  - `384` (`shell_grants.py`) to `100%`
  - `385` (`shell_intent.py`) closed at `99%` by design-signal decision
- fourth target set:
  - `387` (`secrets.py`) to `100%`
  - `388` (`rpc_windows.py`) to `100%`
- both modules now disappear from coverage missing-lines report (`skip_covered = true`)
  - full suite now reports `8 files skipped due to complete coverage`

## Next Targets

- identify next near-complete candidates for elimination from missing-lines output
- `386` landed; continue from simplified parser flow and prefer behavior-meaningful coverage over synthetic branch forcing
