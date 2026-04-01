## Goal

Make continuation from non-tip lineages explicit and predictable at the operator boundary.

## Scope

- Tighten how `step` derives explicit parentage when a bind or selected head is not the current tip
- Ensure new message events continue the intended lineage rather than whichever tip happens to be latest
- Clarify precedence between active head selection and bind index controls

## Behavior

- Continuation from the active tip may still use default parentage
- Continuation from a non-tip head or bind point must result in explicit parentage on the first new divergent message event
- Later appended events in the same continuation may default from that new message event

## Rules

- Message lineage is decided in message-event space only
- Non-message records must not interfere with continuation semantics
- If head selection and bind selection disagree, the precedence rule must be explicit and tested

## Non-Goals

- No merge behavior
- No automatic branch reconciliation

## Done When

- The first new event after non-tip continuation carries the correct explicit parent
- The rule is consistent across generation, callable execution, and no-op cases
- The precedence between selected head and bind index is documented in tests and CLI behavior
