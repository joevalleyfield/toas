Filed as: 260912-config-execution-facet-design
FKA:
AKA: config execution topic; execution help facet; execution config boundary
Legacy index:

Parent: `260912-config-show-navigation-and-model-view`
Related: `260912-config-navigation-hint-correction`; `260912-config-discovery-preservation`

keywords: config, exploration, parked, contract, usability, execution, policy

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

The useful relationship is not “every help topic becomes a config filter,” nor
“every config filter must follow one key prefix.” It is:

```text
/help config TOPIC
        |
        +-- config facet with related keys --> /config show TOPIC
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

The `related_keys` for a curated config facet may cross key prefixes when the
settings form a tightly coupled control surface. Prefix alignment is useful
for simple families, but it is not the design rule. A cross-prefix facet must
still explain the shared operator question, identify its included settings,
and preserve ownership/source labels in the resulting view.

On that basis, `execution` should not be rejected as a filter merely because
its candidates live under `runtime`, `shell`, `tool_writes`, or
`capability_advertisement`. It should be rejected or deferred only if those
settings do not form a coherent execution-control question. The existence of
the word `execution` in the overview is not sufficient evidence by itself;
the coupling and operator use case are the evidence we need.

## Worked example: candidate execution groups

Applying that rule to the current registry produces several plausible groups,
but they answer different questions:

| Candidate facet question | Cross-prefix members | Why the coupling is plausible | Why it should not be merged casually |
| --- | --- | --- | --- |
| Which assistant actions are admitted and bounded? | `capability_advertisement.profile`; `capability_advertisement.hidden_tools`; `shell.allowed_commands`; `shell.assistant_timeout_s` | All affect whether an assistant-addressable action is visible, authorized, or bounded by default. | Visibility, authorization, workspace scope, and lifetime are separate invariants; the view must label those distinctions. |
| How does a run progress and terminate? | `runtime.async_runs`; `runtime.async_backend_mode`; `runtime.streaming_mode`; `runtime.cancellation_mode`; `runtime.thinking_stream_mode`; `runtime.prompt_progress_mode`; selected `health_timing.*` | All shape run lifecycle, progress reporting, or observation of terminality. | Health is observational, and transport deadlines must not be presented as action or process termination policy. |
| How is an action materialized in its process/filesystem environment? | `shell.environment`; `runtime.python_runtime`; `runtime.powershell_runtime`; `tool_writes.newline_style` | All affect the environment or representation in which a concrete action takes effect. | They span process setup and file rendering; one “execution” heading could conceal important ownership differences. |
| Which candidate becomes the next action? | `extraction.*` | Extraction controls candidate lanes, arbitration, staging, and projection immediately before execution. | It is intentionally upstream of execution and already has a coherent plain/config topic. |

The first two rows are the strongest cross-prefix candidates, but they are
not one tight group: “may this assistant action run?” and “how does the run
progress?” have different users, failure modes, and invariants. The third is a
possible operational-materialization topic. The fourth should remain
extraction.

This gives a reusable test for other topics: begin with the operator question,
collect keys by behavioral coupling, record the prefixes crossed, and split
the facet when the rows have different authority, lifecycle, or failure
semantics. A cross-prefix facet is justified when its members are changed or
inspected together in a real workflow—not merely because they appear in the
same implementation path.

### Interim implication for `execution`

The bare label `execution` currently names too many of these questions to be a
safe single key set. The next design choice is therefore among:

1. make `execution` a plain-help umbrella and expose narrower config facets;
2. make it a composed config view with explicit subsections such as action
   bounds and run lifecycle;
3. replace the overview hint with the narrower questions until a composed
   view has a demonstrated operator use case.

None of these choices requires an `execution.*` namespace.

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

Parked for deliberate reconsideration. The matrix and open alternatives are
preserved, but this topic is not in the active implementation path until a
concrete operator workflow makes one execution grouping worth pursuing.
