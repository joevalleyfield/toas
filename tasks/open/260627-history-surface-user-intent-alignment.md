Filed as: 260627-history-surface-user-intent-alignment
FKA:
AKA: history subcommand expectation audit; naive-user history affordances; history surface UX contract
Legacy index:

keywords: surface, investigation, inception, usability, history, projection, graph, transcript

Parent: `260614-architecture-follow-through-coordination`
Related: `260627-history-surface-corruption-semantics`; `260627-fail-closed-history-query-hardening`; `260627-history-recovery-tooling`; `260627-history-affordances-semantic-restaging`; `260627-split-storage-rebuild-and-projection-parity`

# History Surface User Intent Alignment

## Current Reality

TOAS exposes several history-facing subcommands:

- `heads`
- `history`
- `transcript`
- `llm-input`
- `rebuild`
- `graph`

They are all mechanically meaningful, but they do not yet read as one coherent
operator-facing product surface.

A naive-user audit across docs, CLI routing, runtime code, and current
workspace behavior suggests several kinds of mismatch:

- some commands are named more broadly than the user intent they actually serve
  (`history` reads closer to "recent durable event summary" than "conversation
  history")
- some commands are much sharper or more mutating than their surface wording
  suggests (`rebuild`)
- some commands expose substrate truth in a form that is faithful but not
  obviously useful to a human operator (`graph`)
- some commands are comparatively well-shaped but underspecified in docs about
  what transformation they apply (`llm-input`)
- the commands do not yet tell one stable story about what "history" means to
  a user versus what it means to the substrate

The new `fsck` / fail-closed behavior improves integrity semantics, but it does
not by itself answer the more basic affordance question:

```text
if history is healthy, do these commands do what users actually want?
```

And, after refusal:

```text
if history is unhealthy, do the commands fail in a way that still matches user intent?
```

## Desired Reality

Each history-facing surface should have a crisp operator-facing job:

- what user question it answers
- what level of projection or normalization it applies
- whether it is observational, analytical, or mutating
- how it behaves on invalid targets
- how it behaves when `fsck` refuses the underlying history

The goal is not just consistency under corruption. The goal is that the set of
history commands feels intentional and legible to a user who is not reasoning
from implementation seams.

## Audit Findings To Preserve

The initial exploration surfaced these concrete pressures:

- `transcript` is close to "show me the conversation as TOAS can reconstruct
  it" and is one of the clearest surfaces
- `llm-input` is close to "show me what the model sees", but its projection
  rules (drop control, strip reasoning, coalesce adjacent user messages) should
  be explicit
- `history` currently mixes head listing with recent raw event summaries and
  therefore does not cleanly answer one user question
- `heads` is useful but terse; it may need either stronger framing or richer
  affordances for disambiguation
- `graph` is truthful substrate rendering, but it is not obvious that this is
  what a naive user wants when they ask to inspect history
- `rebuild` is the most dangerous mismatch because its name sounds inspectable
  but its effect is mutating and stateful
- invalid `head_id` handling and refusal output are part of the affordance
  contract, not just error handling trivia

## Focus

- write down the operator-facing job for each of the six surfaces
- distinguish "history as user-facing material" from "history as durable event
  substrate"
- identify naming, output-shape, or help-text mismatches that make the current
  commands harder to use than they need to be
- specify how `fsck` refusal should preserve affordance clarity rather than
  merely stopping execution
- decide whether some current commands need narrower framing, renamed
  semantics, or companion surfaces

## Exit Evidence

- a surface-by-surface intent matrix for `heads`, `history`, `transcript`,
  `llm-input`, `rebuild`, and `graph`
- explicit notes on where current command names overclaim, underclaim, or hide
  mutation
- examples of healthy-history and corrupt-history behavior that still read as
  coherent operator affordances
- at least one bounded follow-on implementation or docs slice justified by the
  audit
