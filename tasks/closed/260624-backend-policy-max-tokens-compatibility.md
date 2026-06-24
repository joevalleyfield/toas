Filed as: 260624-backend-policy-max-tokens-compatibility
FKA:
AKA: backend policy constructor compatibility; prompt policy max_tokens default; token flags regression
Legacy index:

keywords: config, hardening, active, compatibility, prompts, policy, coverage, tokens

Related: `261-generation-policy-in-operator-config`; `260624-graph-provenance-coverage-gap-closure`
Status: closed

# Backend Policy Max Tokens Compatibility

## Current Reality

The new token-budget flags added `max_tokens` to `BackendGenerationPolicy`, but
older direct constructor callsites still instantiate the policy without that
field.

This breaks prompt tests and any similar compatibility callsites with a
constructor `TypeError` even though `max_tokens` is conceptually optional.

## Desired Reality

`BackendGenerationPolicy` should remain backward-compatible for callers that do
not care about a request token budget, while still allowing config-derived
policies to thread an explicit `max_tokens` value.

## Plan

- make `max_tokens` optional at the policy constructor boundary
- add a direct compatibility regression test
- rerun focused prompt/policy coverage to confirm the slice stays fully covered

## Closure

Closed by `policy: restore backend max tokens compatibility`.

Restored backward-compatible `BackendGenerationPolicy` construction by making
`max_tokens` optional with a default of `None`, added direct regression coverage
for legacy constructor usage, and covered the no-prefix dynamic prompt listing
branch hit by the focused prompt/policy slice.
