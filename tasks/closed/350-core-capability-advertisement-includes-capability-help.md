## Goal

Ensure `capability_help` is advertised in the default (`core`) capability profile so on-demand capability introspection is available without profile escalation.

## Why Now

Hiding `capability_help` behind non-core profiles makes a high-value read-only introspection tool harder to discover during normal operator loops.

## Scope

- include `capability_help` in core capability-advertisement profile selection
- keep low-signal tools (for example `echo_block`) out of core by default
- add a regression test confirming core repo-work advertisement includes `capability_help`

## Outcome

Implemented in current pass:
- core profile now includes `capability_help`
- test coverage added for core-profile advertisement behavior
