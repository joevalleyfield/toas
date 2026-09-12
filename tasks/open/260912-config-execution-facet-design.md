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

Inception: gather the mismatch matrix and settle the semantic boundary before
opening an implementation follow-on.
