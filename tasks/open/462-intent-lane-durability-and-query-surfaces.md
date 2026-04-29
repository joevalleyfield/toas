## Goal

Add a first-class non-message intent lane for session-level goals (task/arc/mission metadata) that remains durable and queryable without overloading message events.

## Why

`456` completed transcript path decoupling; next operator need is durable expressed intent independent of message content.

## Scope

- define durable intent record shape and append semantics
- keep intent records distinct from message-event numbering/lineage
- add lightweight query/projection surfaces for recent/active intents
- test append, query, and projection invariants

## Done When

- intent records can be appended durably
- operators can inspect active/recent intents via CLI/session surface
- tests prove no message-lineage semantic drift
