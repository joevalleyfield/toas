Filed as: 260831-transcript-source-reference-operations
FKA:
AKA: run and stage; assistant source references; local transcript reach-back; plan adoption operations
Legacy index:

keywords: runtime, projection, decomp, inception, correctness, usability, transcript, frontier, provenance, authority

Parent: `260803-tool-intent-ingress-separation`
Related: `260803-language-exec-fenced-block-lane`; `260803-first-failure-plan-recovery`; `260831-verbatim-staged-plan-restaging`; `260627-history-affordances-semantic-restaging`; `260830-exec-grant-policy-matchers`

# Transcript-Native Assistant Source Reference Operations

## Intent

Define small, explicit transcript operations that let a current user turn act
on nearby assistant-authored executable source without copying it by default,
without treating durable execution history as a duplicate-prevention authority,
and without turning continuation into hidden runtime state.

The temporary conversational hooks are `run` and `stage`; they are not adopted
product names. The task owns the underlying source-reference model and only
later chooses compact operator spelling.

## Confirmed design truth

- The initial reference scope is local: the latest relevant prior assistant
  turn and its ordered executable candidates. Broader history search is
  deferred.
- The local source root is lexical rather than separately bound state: a
  reference resolves against the last assistant message before its own trailing
  frontier. That remains true after arbitrary intervening user/result turns;
  no synthetic session handle or durable source binding is needed for the
  initial model.
- Source references are explicit transcript operations, not opaque runtime
  queues. Durable provenance makes a reference reliable but does not replace
  its visible transcript representation.
- An explicit current reference creates a new request. Earlier matching
  `tool_request`/`tool_result` evidence is audit context, never a reason to
  reject it as a duplicate.
- Reference operations address assistant intent only. Ordinary user YAML is
  already current executable material and is not a source-reference target.
- A source-reference operation participates with YAML, shell, configuration,
  grants, and other operator commands in the existing textual `in_order`
  arbitration stream. A line later in the transcript is a later operation;
  normal success sequencing needs no separate `then` connective.
- Referenced execution may remain in its bounded assistant/policy-mediated
  lane. The user can interleave explicit grants, timeouts, or other policy
  changes before the reference; referencing does not imply direct unbounded
  user execution.
- Materializing assistant source into an ordinary user YAML frontier is a
  deliberate authority and representation transition. It is appropriate for
  mutation, not the default way to inspect or continue source.
- Quiet staging is the default: staging a source reference projects an explicit
  reference-ready frontier rather than copying its source. `--verbose` is the
  explicit loud/materializing form, aligned with existing verbose projection
  affordances such as `/compact --verbose` and `/concept-graph`.

## Design sketch

Use `P` only as explanatory notation for an assistant turn's ordered candidate
sequence and `P.n` for a selected member/span. Candidate concrete operations
include:

```text
run P        execute referenced assistant source under effective policy
stage P      defer/project referenced assistant source for a later decision
run P.n      execute a selected assistant candidate/span
stage P.n    defer/project a selected assistant candidate/span
```

The current selector direction is a typed compact plan/operation coordinate,
with the assistant-turn root implicit for the local feature:

```text
/run                 entire local assistant sequence
p1                   first plan only (all its operations)
p1..                 first plan and every later plan in source order
p-1                  last plan
p-1.o1               first operation of the last plan
p2.o3                third operation of the second plan
p2.o3..              operation three onward through the assistant sequence
p2.o3..o5            operations three through five within plan two
p2.o3..p3.o2         finite range crossing into plan three
p1.o-1               final operation of plan one
p1.o-4..o-2          fourth-last through second-last operation of plan one
p1.o-4..p2.o-3       fourth-last operation of plan one through third-last
                      operation of plan two, inclusive, with all intervening
                      plans/operations retained in original forward order
```

Index `1` always names the first operation of its selected plan. A failure at
`p2.o3` stages the sequence tail as `p2.o4..`; it does not reinterpret
`p2.o1..` as a recovery-relative suffix. `p1..` is the concise plan-level
form of the sequence tail previously illustrated as `p1.o1..`. A negative
plan coordinate is a request-time tail-relative convenience, never a reverse
ordering operation: `p-1..` selects the final plan and `p-2..` selects the
final two plans, both in original forward source order. A recovery continuation
from a tail-relative request is projected with resolved forward absolute
coordinates (for example `p4.o2..`), so later transcript meaning never changes
as a human counts from a different tail.

Negative operation coordinates are likewise tail-relative within their named
plan (`o-1` is that plan's final operation). The runtime resolves every
negative endpoint against the selected assistant source before validating range
order. Ranges are inclusive and must remain forward in source order:

```text
p1.o-4..p2.o-3   valid: resolved start through resolved end, inclusive
p2.o-1..p1.o1    invalid: reverse source order is not a selection mode
```

For example, if plan one has eight operations and plan two has seven,
`p1.o-4..p2.o-3` resolves to `p1.o5..p2.o5`. Any projected continuation uses
those resolved forward absolute coordinates rather than retaining tail anchors.

Plan and operation ranges are hierarchical, not a flattened/reversed sequence
syntax: no omitted-plan reverse shorthand such as `p.-1..`. Future explicit
assistant-turn coordinates (for example `a1.p2.o3`) remain deferred. Compact
contextual aliases such as `failed` and `tail` remain candidates for generated
recovery affordances, with exact expansion/provenance to be specified.

## Canonical candidate-space invariant

`p` coordinates must name one canonical, source-ordered candidate space. The
runtime must not render/index every fence while authorization or execution
silently renumbers a filtered eligible-plan subset (or vice versa). Each
addressable candidate needs a stable source ordinal/span, kind, and declared
available transitions before any projection, reference resolution, or
authorization decision consumes it.

Structural classification happens early enough to establish that shared space:

- runnable candidates can be selected by `run` and remain policy/authority
  checked when reached in the ordered stream;
- materializable candidates can be selected by `stage` even when not runnable;
- arbitrary inert, malformed, or unsupported content is either excluded before
  numbering or shown as an explicitly unaddressable diagnostic.

Later authorization must accept or deny the already-selected candidate; it
must never create a competing coordinate space. This preserves one visible
indexing model even when grants/configuration earlier in the same turn change
whether a runnable candidate is permitted to execute.

### Compatibility warning

Existing internals may already carry raw/unfiltered fence or source ordinals,
including inert or otherwise non-addressable blocks. That inventory may need to
survive during the migration and should be named as a distinct source/fence
index, not silently repurposed as `p` coordinates. The implementation must
define an explicit mapping from raw source inventory to canonical addressable
candidate coordinates and adapt incumbent consumers forward. No user-visible
reference should depend on whichever incidental filtered/unfiltered list an
older path happened to enumerate.

`stage` has two projection modes:

- quiet (default): stepping a staged reference projects another explicit
  executable source reference, preserving the assistant execution lane and
  making room for grants/configuration before it runs;
- loud (`--verbose`): projects source as editable user working text, possibly
  with a chosen serializer or other declared projection shape.

## Recovery relationship

On first failure of an assistant's automatically executed sequence, the
runtime may create an editable user retry for the failed action and retain the
remaining assistant source as later explicit reference operations rather than
copying a staged YAML tail. Later failures in a mixed user/reference sequence
must preserve the failed current operation in its own form and keep later
operations explicit and ordered.

Generated recovery should default to `run`ning the referenced remaining source
after the corrected failed action succeeds. A later failure simply pauses at
the next component and exposes its local recovery point. The preferred
disposition (`run` versus quiet `stage`) should eventually be configurable;
the configuration key and persistence scope remain deferred.

For failure of assistant source member `P.i`, recovery deliberately has split
authority:

```text
P.i              -> materialized user retry: direct-user permissions
P.i timeout      -> effective assistant timeout rendered explicitly
P.(i+1)..P.n     -> referenced assistant suffix: bounded/policy-mediated
```

The materialized retry is therefore not a verbatim claim about the original
assistant source: it is an explicit user working projection that retains the
effective assistant timeout as visible, editable intent. The original source
remains preserved separately. The later suffix remains assistant source and
keeps its ordinary authority boundary until explicitly staged/materialized.

If a reached `run` reference fails, it recovers identically: materialize the
actual failed selected assistant action as the user retry with the effective
assistant timeout rendered explicitly, then emit a bounded `run` reference for
the remaining part of that selected source range. There is no distinct
"bounded-reference failure" recovery model.

## Non-goals

- A global replay browser, historical search language, or durable replay queue.
- Suppressing explicit current requests because equivalent history exists.
- Treating reference selection as automatic direct-user/unbounded execution.
- Fixing final syntax, stable handle notation, or cross-session reference
  identity before local transcript examples require them.
- Broad redesign of all failure/recovery behavior in this task.

## Implemented first slice

- Added local `/run` and `/stage` operator commands for the latest prior
  assistant message.
- Added canonical source-ordered plan selection for whole plans, plan tails,
  single operations, operation tails, and positive/negative coordinates.
- Quiet staging now projects an explicit `/run` reference with source-message
  and selector provenance; it does not copy source into user YAML or execute.
- Referenced `/run` execution uses the assistant authority/policy lane and
  records source-reference provenance on projected results.
- The implementation intentionally leaves verbose materialization, finite
  cross-plan ranges, aliases, and generated recovery disposition deferred.

## Elaboration questions

- Should operation coordinates also allow negative tail indexing (`o-1`), or
  should only plans use it initially?
- How should contextual aliases such as `failed` and `tail` expand when their
  selected suffix crosses plan/fence boundaries?
- What configuration surface should select generated recovery's `run` or
  quiet-`stage` disposition?
- How should failure of a later bounded `/run P.n` reference project its retry
  without confusing it with the deliberately user-materialized original-plan
  failure form?

## Exit evidence

This requirements parent is ready to split once representative transcript
fixtures establish:

- local reference selection and source-coordinate rules;
- ordered interaction with grants/configuration/YAML;
- first-failure and repeated-edit recovery behavior; and
- a clear distinction between quiet staging and explicit materialization.

The first implementation slice may limit its grammar to local `run` selectors
(`run`, `pN`, `pN.oM`, and open tails including resolved negative indices) and
quiet staging. Verbose materialization projection shapes, finite cross-plan
ranges, and contextual aliases may follow without changing the candidate-space
or recovery model.

Follow-on implementation tasks should own one bounded seam each and preserve
the original source/projection/authority distinctions above.
