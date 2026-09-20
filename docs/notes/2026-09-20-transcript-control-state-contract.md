# Transcript Control State And Resolution Contract

Status: Normative direction with current-state exceptions (2026-09-20).

This note is the companion to the [transcript control-state survey](2026-09-20-transcript-control-state-survey.md). It is the navigation point for settings that affect a future TOAS step but do not all belong in a global or workspace configuration file.

## Contract in brief

TOAS does not have one universal settings ladder. Resolution is domain-specific
because ordinary configuration, transcript control deltas, child-process
environment, and TOAS's own process environment answer different questions.

The durable history shape is individual control deltas. A full settings block
may be useful as an inspectable, replayable checkpoint or projection, but it is
not a replacement for deltas and does not make every setting serializable to a
project or global file.

The intended history rule is branch-forward: a control delta inserted at a
frontier applies to that branch and its descendants until another delta
overrides it. The current implementation is mixed. Message-derived selection
and environment modifiers use a working lineage in several paths, while a
number of control-record reducers currently scan the supplied journal without
an explicit head and therefore behave history-forward when the normal step path
supplies the whole journal. That gap is a correctness issue, not a reason to
hide control state in sidecar process memory.

## The four environment questions

The word *environment* names two different control surfaces, with two further
runtime layers beneath them:

| Domain | Question | Durable transcript state? | Resolution summary |
| --- | --- | --- | --- |
| TOAS control-plane environment | How is the TOAS process started or compatibly configured? | No; host/bootstrap input | A compatibility input to the relevant TOAS policy resolver. It must not be treated as a transcript delta or child-process variable. |
| File and session configuration | What ordinary `OperatorConfig` baseline applies? | Files plus `config_override` records | Ordinary config uses the scoped ladder in [config precedence](2026-05-09-config-precedence-principles.md). |
| Transcript control deltas | What policy should this transcript branch use? | Yes; record-specific control records and message-derived intents | Resolve each record type against the requested message lineage. Do not assume that a single reducer or global ladder covers all types. |
| Child-process environment | What environment should a tool subprocess receive? | Yes, when supplied by transcript controls or environment policy | Host baseline, call-local additions, transcript `/env` modifiers, then selected environment policy; `replace` modes can intentionally discard earlier layers. |

Examples of TOAS control-plane environment include RPC mode, provider
compatibility variables, stream compatibility flags, host ownership, daemon,
debug, and test switches. Examples of transcript-controlled child environment
include `/env` modifiers, environment profiles and bindings, and future
fence-local `env` inputs. The same spelling, such as a `TOAS_*` key, does not
make the two domains interchangeable.

## Resolution and provenance rules

### Ordinary configuration

The ordinary config lane has a documented source order: runtime secrets,
durable session overrides, local project files, global files, environment
compatibility inputs, and in-code defaults. The lane is defined more precisely
in [Config Precedence and Sequencing Contract](2026-05-09-config-precedence-principles.md).

That ladder is not a promise that every runtime policy follows the same order.
For example, streaming flags and child-process environment have their own
resolvers, and selected runtime policy can intentionally replace an earlier
environment layer.

### Transcript control deltas

Each control record has its own state transition and provenance. Relevant
records include config overrides, shell-scope grants, command/workspace
context, target selection, surface bindings, and related session controls.

The resolver contract is:

1. identify the message lineage or explicit history head for the operation;
2. select only control records applicable to that lineage;
3. apply records in durable order, using the record type's documented scope
   and override rules;
4. expose the winning source and any exceptional fallback when inspection or
   diagnostics request provenance.

The current graph control-state helpers accept an event sequence but not a head
identifier. Normal stepping commonly supplies the full journal, which makes
these controls history-forward today. This is explicitly current behavior, not
the target contract. New control-state work should take lineage as an explicit
input and preserve branch-forward semantics.

### Same-step visibility

An inline control command may affect later consequences in the same step when
the owning runtime path supports a live update. The existing config lifecycle
does this for `config_update`; other control records are persisted after the
frontier consequences and must not be assumed to have the same timing until
their command contract says so. Documentation should name this per operation
rather than generalizing from `/config` to all settings.

### Child-process environment

Child-process environment is a runtime consumer of policy, not the environment
that configures TOAS itself. The observed order is:

```text
host process environment
  -> explicit call-local environment
  -> transcript /env modifiers
  -> selected shell.environment profile/binding
```

An environment policy may inherit, merge, or replace. A replace operation is
therefore a deliberate boundary, not an accidental precedence inversion. The
effective environment and its source layers should be inspectable without
serializing secrets into a checkpoint.

## Deltas, checkpoints, and replay

Individual deltas are the canonical history representation because they retain
operator intent, ordering, and branchability. A full settings checkpoint can be
added as a derived or explicitly authored projection when it has a clear schema,
source provenance, and validation against intervening deltas.

A checkpoint must not silently:

- collapse unrelated policy domains into one precedence rule;
- turn a child-process environment snapshot into a TOAS bootstrap setting;
- overwrite intervening deltas without recording the relationship;
- imply that secrets or ephemeral host state are durable transcript content; or
- become the only way to insert a setting change before an assistant turn.

Insertion, inline control steps, and explicit end steps remain valid history
shapes. The branch-forward rule applies regardless of which surface authored
the delta.

## Scope cuts

The following are intentionally outside a first transcript settings checkpoint:

- host/bootstrap, daemon, protocol, test-only, and debug environment switches;
- ephemeral secret values and other material that must not enter transcript
  history;
- derived operational observations such as activity health and stream events;
- backend process lifecycle state and transport carrier details.

They remain documented as inputs or runtime state where needed; excluding them
from a checkpoint is not permission to treat them as undocumented.

## Ownership and navigation

- [Config Precedence and Sequencing Contract](2026-05-09-config-precedence-principles.md)
  owns the ordinary config lane.
- [Execution Model](../execution-model.md) owns transcript authority, graph
  participation, and the distinction between frontier selection and control
  state.
- [Runtime Ownership And Module Boundaries](../runtime-ownership.md) routes
  implementation across graph storage, runtime reducers, policy resolution,
  and child-process tools.
- The [survey](2026-09-20-transcript-control-state-survey.md) remains the
  evidence inventory and implementation decomposition; it is not a second
  precedence contract.

Future implementation tasks should link back here when they add a control
record, resolver, checkpoint projection, or environment surface.
