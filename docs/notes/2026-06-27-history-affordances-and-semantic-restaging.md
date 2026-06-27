# History Affordances And Semantic Restaging

Status: DRAFT
Related tasks: `260627-history-affordances-semantic-restaging`; `260626-transcript-parallelism-design-pressures`; `260614-architecture-follow-through-coordination`

## Purpose

Capture an exploratory product/design question:

```text
How should TOAS make durable history usable as operator material rather than
only as audit trail?
```

This note is not adopted product direction.
It is a white-paper shaped exploration intended to:

- preserve the current uncertainty without flattening it into vagueness
- separate user jobs from substrate mechanics
- record vocabulary that seems promising
- identify what future evidence would make a concrete affordance worth
  implementing

## Current Tension

TOAS already has rich durable history mechanics:

- append-only message and non-message records
- transcript projection
- branching through transcript divergence
- historical callable selection
- rebuild and inspection surfaces
- emerging pressure toward multiple bounded projection surfaces and
  queue-shaped work

But that does not automatically amount to a product use-case.

The challenge is not merely "which operations on history are possible?"
It is:

```text
Which operations on history become useful when an intelligence is invited to
act on them?
```

This matters because a purely mechanical history surface can be correct without
being especially helpful.

## Naming Pressure

The current word "replay" appears to carry too much meaning.

In the repository today, it spans several distinct ideas:

- re-execute prior callable intent
- fixture or harness playback
- reconnect/event-stream replay
- broad product-language implication that old work can somehow become useful
  again

Only the first of those is close to an operator-facing job.
The rest are implementation or test vocabulary.

This creates two kinds of confusion:

1. it makes one narrow operation sound like a product center
2. it makes several non-equivalent history operations sound more unified than
   they really are

The naming critique is not that replay is meaningless.
It is that replay is too mechanism-colored to serve as the main user-facing
concept.

## A More Credible User Job

The strongest currently visible job is narrower and more concrete than
"replay history."

It looks more like:

```text
I did some exploratory work earlier. The world shifted. Help me refresh the
useful parts of that exploration in the new context.
```

Examples:

- earlier inspection steps should be re-run after the branch changed
- previous observations may now be stale and should be checked again
- an exploratory sequence should be carried forward into a sibling branch
- prior intent should be staged into a new frontier without copying forward old
  results as if they were still current

This suggests that the reusable asset is often not the old result itself.
It is more often:

- the prior investigative move
- the prior intent sequence
- the prior exploration recipe
- the distinction between old observations and still-relevant setup

## Working Vocabulary

No vocabulary here is proposed as adopted surface language.
The point is to preserve candidate concepts that better match plausible user
jobs than "replay."

Promising words:

- `continue from`
- `restage`
- `refresh`
- `re-run`
- `reapply`
- `carry forward`

Current intuitive meanings:

- `restage`: recover prior intent or exploratory steps into the active
  frontier without executing them yet
- `re-run`: execute earlier staged or selected intent in the current context
- `refresh`: higher-level operator goal that may involve restaging, re-running,
  and comparing outcomes
- `continue from`: branch or resume work from an earlier point in the durable
  conversation history

This is not a final taxonomy.
It is a reminder that operator language should name intention first and
mechanism second.

## Mechanical Primitives Vs Semantic Affordances

The useful split may be:

### 1. Mechanical primitives

These should stay explicit, auditable, and append-only:

- select prior nodes, ranges, or consequence groups
- distinguish prior intent from prior result
- stage prior intent into a new frontier or projection
- execute staged intent in the current context
- compare old and new consequences
- mark findings as stale, confirmed, superseded, or branch-local

### 2. Semantic affordances

This is where intelligence becomes useful:

- identify prior exploratory bundles that look reusable
- infer whether old work was setup, observation, conclusion, or mutation
- suggest which earlier steps are likely stale and worth refreshing
- summarize drift between prior and current outcomes
- propose a concrete staged plan rather than requiring the operator to manually
  reconstruct one from raw history

The key principle is:

```text
Intelligence should help select, group, and re-present history.
It should not make durable history less explicit.
```

## Why Parallelism Changes The Story

Parallel projection work makes this pressure more concrete.

Once TOAS can support multiple bounded projection surfaces, a new use-case
becomes easier to name:

- one branch or child projection performs exploratory setup
- the world changes elsewhere
- the earlier exploratory steps may need to be refreshed in place or
  re-applied in another projection

That makes "history reuse" less abstract than it appears in single-surface
work.

At the same time, parallelism also sharpens an important design question:

```text
Should TOAS re-run prior work directly, or should it first restage reusable
intent and let execution happen explicitly in the new context?
```

The second option currently appears more TOAS-native because it:

- preserves old results as historical facts rather than silently replacing them
- keeps execution explicit
- allows intelligence to separate reusable setup from stale observation
- reduces pressure to invent magical in-place mutation semantics

## Experimental Stance

This topic likely wants experimentation more than specification.

Two sources of utility are plausible:

1. models may already know useful patterns for reusing prior work if TOAS
   advertises the right history-shaped affordances
2. the affordances themselves may need to be designed so that in-context
   learning can discover their usefulness

That suggests a near-term posture:

- keep the mechanical substrate crisp
- avoid prematurely freezing the surface vocabulary
- let adjacent parallelism work produce concrete examples
- vary the capability advertisement and observe which framings lead to useful
  operator behavior

The product problem is therefore not only:

```text
what history APIs should exist?
```

It is also:

```text
what invitation causes intelligence to do something genuinely helpful with
history?
```

## Candidate Experimental Shapes

These are not adopted commands.
They are examples of mid-level affordances that may prove more useful than raw
history primitives while remaining less opaque than one-shot automation.

- extract the exploratory steps that supported this conclusion
- restage the checks from this earlier branch into the current projection
- refresh observations that may now be stale after branch drift
- compare the earlier result set to a current re-run
- carry forward setup steps but not the old conclusions

The pattern behind all of them is the same:

```text
history becomes reusable operator material when intent, result, and
relevance-to-current-context can be separated.
```

## Open Questions

- What is the smallest durable unit of reusable historical work: one call, a
  sequence, a consequence group, or a seed-like bundle?
- Does TOAS need new durable record families for stale/confirmed/superseded
  findings, or can those remain projection/operator-layer semantics at first?
- Should any first implementation stop at restaging and comparison rather than
  direct re-execution?
- How much capability can be unlocked through better prompts and visible
  advertisement without adding new commands yet?
- Which parts of historical reuse should be explicit operator commands versus
  assistant suggestions over existing substrate?

## Provisional Stance

Until stronger use-cases emerge, the conservative stance is:

- do not treat "replay" as the headline product concept
- treat history reuse as exploratory design space rather than adopted
  direction
- prefer explicit staging of reusable prior intent over automatic in-place
  refresh
- let queue-shaped parallelism and adjacent operator workflows supply the first
  honest pressure for concrete affordances

## Exit Evidence

This note should become more specific only when one or more of the following is
true:

- parallel projection work produces a recurring need to refresh prior
  exploratory steps after world-state changes
- a prompt or capability framing reliably causes the model to make useful
  history-aware suggestions
- one history-facing affordance can be described with clear durable semantics
  and without overloaded vocabulary
- user/operator practice reveals a stable distinction between restaging,
  re-running, and refreshing
