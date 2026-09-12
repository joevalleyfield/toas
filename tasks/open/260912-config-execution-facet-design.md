Filed as: 260912-config-execution-facet-design
FKA:
AKA: config execution topic; execution help facet; execution config boundary
Legacy index:

Parent: `260912-config-show-navigation-and-model-view`
Related: `260912-config-navigation-hint-correction`; `260912-config-discovery-preservation`

keywords: config, exploration, inception, contract, usability, execution, policy

# Deliberate the execution config/help facet

## Pressure

The unfiltered config overview presents `execution` as a useful peer to
`models`, `generation`, and `extraction`, but the current configuration and
help corpus does not establish what that word owns. Selecting a key set now
would make the overview's presentation taxonomy look like a durable config
taxonomy without sufficient design evidence.

## Existing evidence

The repository currently uses “execution” for several related but distinct
areas:

- transcript-frontier stepping and consequence handling;
- model-addressable capability execution and authorization;
- direct-user shell intent, which has deliberately different authority;
- asynchronous run/watch/cancel lifecycle;
- shell runtime policy and file-write policy;
- extraction's transition from candidate intent to later execution.

Existing help and configuration already describe many of these through
`extraction`, `capabilities`, `shell`, `tool_writes`, and `runtime`. The
execution-model and execution-authority documents also describe invariants that
are not necessarily mutable configuration.

## Mismatch matrix

The matrix compares the operator question implied by “execution” with the
current configuration registry, help ownership, and invariant sources.
“Plain only” means the concept is useful to explain but has no justified
mutable setting. “Composed candidate” means a future view could gather
existing settings without creating an `execution.*` namespace.

| Operator question | Existing keys | Current help owner | Invariant / evidence source | Assessment |
| --- | --- | --- | --- | --- |
| What happens at the transcript frontier when I run a step? | none | no execution facet | `docs/execution-model.md`; `docs/vision.md` | Plain only: frontier authority and explicit stepping are semantics, not config. |
| Which authored candidates are extracted and in what order? | `extraction.*` | `extraction` config/plain facets | help asset; `docs/acceptance/complete-change-request.md` | Keep under extraction; it is upstream of execution. |
| Which model-facing capabilities are advertised or hidden? | `capability_advertisement.profile`; `capability_advertisement.hidden_tools` | `capabilities` plain facet; no config facet | `docs/capabilities.md` | Composed candidate: visibility is adjacent to, but not identical with, authority. |
| Which assistant shell commands may run, and how long? | `shell.allowed_commands`; `shell.assistant_timeout_s` | capability/tool guidance; no shell config facet | `docs/execution-authority.md`; `docs/capabilities.md` | Composed candidate, while retaining shell ownership. |
| How does direct user shell intent differ from assistant execution? | no dedicated key; assistant timeout does not define the user lane | no dedicated facet | `docs/capabilities.md`; `docs/execution-authority.md` | Plain only for now; do not imply the distinction through assistant policy keys. |
| How are file writes materialized? | `tool_writes.newline_style` | no tool-write config facet | tool capability help; rendering policy | Composed candidate only for a broader “write behavior” view. |
| How are async runs, streaming, cancellation, and progress controlled? | `runtime.async_runs`; `runtime.async_backend_mode`; `runtime.streaming_mode`; `runtime.cancellation_mode`; `runtime.thinking_stream_mode`; `runtime.prompt_progress_mode` | no runtime config facet | `docs/activity-health.md`; `docs/protocol-notes.md` | Composed candidate, but lifecycle must not be conflated with authorization. |
| What context budget and process environment does execution use? | `runtime.context_budget_mode`; `runtime.python_runtime`; `runtime.powershell_runtime`; `shell.environment` | no runtime/environment facet | runtime direction; environment policy | Separate runtime/environment concern; insufficient evidence for execution ownership. |
| What timing or health behavior surrounds a run? | `health_timing.*` | no health config facet | `docs/activity-health.md` | Separate liveness/observability concern; a diagnostic view is more natural. |
| Which backend/invocation mode runs the request? | `backend.mode`; `backend.managed_local`; `backend_startup.thinking_budget_tokens` | `models` facet partially exposes `backend.mode` | backend lifecycle code; model help asset | Keep backend and endpoint distinctions; do not make execution a compatibility bucket. |
| What generation behavior shapes the produced answer? | `generation.*` | `generation` config/plain facets | generation policy and invocation contracts | Keep under generation; answer production precedes action execution. |
| What persists, reloads, or records as a consequence? | `storage.hot_journal_limit_mb`; `session.*` | no persistence/session facets | execution-model; storage/transcript contracts | Plain/infrastructure concern, not an execution key family. |
| What diagnostics are emitted while execution proceeds? | `diagnostics.log_level`; `diagnostics.log_file` | no diagnostics facet | activity-health documentation | Separate diagnostics concern. |

### Key coverage summary

The full registry is accounted for above or by explicit exclusion:

- `extraction.*`, `generation.*`, and `llm.*` remain owned by extraction,
  generation, and models/backend selection respectively;
- `runtime.*`, `shell.*`, `tool_writes.*`, `capability_advertisement.*`, and
  `health_timing.*` are execution-adjacent, not evidence of an execution key
  family;
- `backend.*` and `backend_startup.*` remain backend concerns;
- `storage.*`, `session.*`, `diagnostics.*`, and `prompt.*` are persistence,
  diagnostics, and prompt-composition concerns;
- legacy `llm.backends` is a migration concern, not a new execution concept.

The matrix finds no missing execution-specific key family. It does find a
legitimate plain-help concept and a possible composed inspection view, but
composition would need labeled subsections and must preserve each setting's
existing topic ownership.

## Filter suitability finding

The useful relationship is not “every help topic becomes a config filter.” It
is:

```text
/help config TOPIC
        |
        +-- config facet with related_keys --> /config show TOPIC
        |
        +-- plain-only facet ----------------> explanation, no config view
```

The existing resolver already embodies this contract: a curated topic with a
config facet returns its ordered `related_keys`; a topic without that facet
returns no curated keys; and an unknown query falls through to exact, prefix,
token, and description search over the valid key registry. This preserves two
different kinds of discovery:

- curated topics answer “what belongs together for this operator question?”;
- key search answers “where is this configurable behavior described?”

On that basis, `execution` can be a plain-help topic without automatically
being a `/config show execution` filter. A future composed filter would need
an explicit config facet whose related keys are deliberately selected from
other owners, with the output labeling those ownership boundaries. The
existence of the word `execution` in the overview is not sufficient evidence
for that facet.

## Design questions

1. Is `execution` primarily a plain-help concept, a config facet, or both?
2. If it has a config facet, what user question does it answer that the
   existing runtime, shell, tool, and extraction topics do not?
3. Should it organize existing keys by execution consequence, or introduce a
   new ownership boundary? The default is to avoid introducing keys or moving
   ownership solely to make the overview symmetrical.
4. Which invariants belong in plain help even when no corresponding setting
   exists—especially explicit frontier stepping, authority separation, first
   failure, and durable consequences?
5. Should `/config show execution` eventually be a composed cross-topic view,
   or should the overview use a different label until a single owner emerges?

## Decision gates

Before implementation, produce:

- a mismatch matrix from the existing config key registry and help topics to
  the execution questions operators actually ask;
- a proposed boundary that names included keys, excluded keys, and why;
- a plain-help companion describing invariants independently of mutability;
- an acceptance path proving every advertised execution affordance is real and
  that no existing key becomes undiscoverable;
- an explicit decision on whether `execution` is a topic, a composed view, or
  a deferred label.

## Non-goals

- no new execution config keys in this design pass;
- no renaming of runtime, shell, tool, backend, or extraction settings;
- no migration or compatibility removal;
- no implementation of `/config show execution` until the boundary is agreed.

## Status

Design matrix recorded; the semantic boundary and whether a composed config
view is worthwhile remain open before an implementation follow-on.
