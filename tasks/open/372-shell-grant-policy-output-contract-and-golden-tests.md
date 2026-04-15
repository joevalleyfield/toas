## Goal

Define a stable output contract for shell policy views and lock it with targeted golden/contract-style tests.

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
