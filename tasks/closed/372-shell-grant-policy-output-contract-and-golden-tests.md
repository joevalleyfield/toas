## Goal

Define a stable output contract for shell policy views and lock it with targeted golden/contract-style tests.

## Status

Closed (2026-04-14)

## Why Now

After `330`, the shell grant surface is richer (`exact/prefix/glob`, source attribution, transcript/config lanes). A compact contract test layer prevents accidental regressions during upcoming `331`-`333` work.

## Scope

- define explicit contract expectations for:
  - `/shell list`
  - `/shell config list`
  - grant update confirmations (`add/remove/unset/reset`, config lane variants)
- add focused tests that assert structure/content markers rather than brittle full-text snapshots where possible
- add one or more golden fixtures only where they materially improve readability and reviewability

## Intended Behavior

- policy-facing shell outputs are predictably shaped and reviewable
- future shell-arc changes can evolve internals without silently degrading operator-facing clarity

## Constraints

- keep tests maintainable; avoid over-snapshotting noisy dynamic fields
- do not introduce queue behavior here (`331` owns that)

## Done When

- contract tests exist for the policy-view/update outputs listed above
- tests fail on meaningful shape regressions and pass on benign formatting-neutral changes
- task `371` helpers are consumed by these tests where applicable

## Completed

- added contract-style tests covering:
  - `/shell list` policy-view shape markers
  - `/shell config list` output shape (`config shell grants:` header + payload line)
  - transcript-lane update confirmations:
    - `/shell add`
    - `/shell remove`
    - `/shell unset`
    - `/shell reset`
  - config-lane update confirmations:
    - `/shell config add`
    - `/shell config remove`
    - `/shell config reset`
- tests assert stable structure markers (`startswith`, key line fragments) rather than brittle full-output snapshots
- confirmed task `371` shared helper usage remains covered via `render_shell_policy_view` and slash-command usage wiring checks
- verified full test suite pass (`uv run pytest -q`)
