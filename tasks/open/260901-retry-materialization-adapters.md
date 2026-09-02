Filed as: 260901-retry-materialization-adapters
FKA:
AKA: generic retry projection; source-preserving timeout projection; fence attribute patching
Legacy index:

keywords: runtime, projection, implementation, inception, correctness, contract, transcript, frontier, provenance, authority

Parent: `260831-transcript-source-reference-operations`
Related: `260901-source-reference-recovery-integration`; `260803-language-exec-fenced-block-lane`; `260831-language-write-materialization-fences`

# Representation-Neutral Retry Materialization

## Intent

Generalize retry recovery beyond YAML tool plans without sacrificing transcript
authority or source fidelity. A failed executable action may originate from a
YAML tool plan, an executable language fence, shell shorthand, or a future
source form. Recovery owns the action's effective execution constraints; the
source-form projection owns whether and how those constraints can be visibly,
editably rendered.

This task is the follow-on to the YAML-focused source-reference recovery
slice. It must not turn recovery into a serializer or introduce invisible
per-retry execution state.

## Core model

The shared recovery transition receives a representation-neutral retry
materialization request:

```text
authored source fragment
+ source form / projection adapter
+ effective execution constraints
-> editable retry frontier | explicit unsupported-materialization outcome
```

The transition remains generic: it owns sequencing, recovery stop behavior,
authority-lane change, and durable evidence. An adapter owns source syntax and
the minimal edit required to make a constraint explicit.

Earlier successful or failed execution facts remain audit evidence. They do
not consume source, suppress a later explicit request, or create hidden
auto-resume state.

## Source-preserving patch invariant

Every successful materialization is an anchored source patch:

- preserve every byte outside deliberate replacement/insertion spans;
- parse and validate the patched representation before projecting it;
- never parse and reserialize a source form merely to add a constraint;
- reject duplicate or ambiguous attributes rather than silently choosing one;
- when no faithful patch exists, produce an explicit unsupported-materialization
  outcome instead of inventing a YAML/tool-call representation or applying a
  hidden override.

The projected retry must visibly carry every constraint that affects its later
execution. A prose-only timeout is not enough.

## Adapter direction

### YAML tool-plan adapter

Use parser/source spans to locate the operation's actual `args` mapping and
make a minimum local patch only when that tool declares `timeout_s` as an
executable argument. Existing explicit timeouts remain authored intent.

Do not use a textual `timeout_s` search. A comment, block scalar, alias, flow
mapping, or `args: # comment` may contain the same text without representing
the desired mapping entry. If an alias or other construct cannot be augmented
without changing its meaning, report the limitation explicitly rather than
duplicating `args` or replacing the operation.

### Executable-fence adapter

Treat the opening information line as a tokenized source span. Retain name and
value spans, quote style, and header-end offset for every fence attribute.

- If `timeout_s` already exists once, replace only its value span, retaining
  quote style, ordering, and all surrounding whitespace.
- If absent, insert exactly ` timeout_s=<value>` at the header-end offset,
  before its newline.
- Preserve the complete fence body and closing fence byte-for-byte.
- Duplicate/malformed attributes, or a fence language without an executable
  timeout attribute contract, are unsupported rather than candidates for
  normalization.

For example, only the indicated header bytes change:

````markdown
```python exec runtime=python
print("hello")
```
````

becomes:

````markdown
```python exec runtime=python timeout_s=30
print("hello")
```
````

### Other forms

Each source form needs an explicit adapter and visible syntax for constraints
before it participates in automatic retry materialization. Do not assume YAML
is an interchangeable recovery lingua franca.

## Scope and exit evidence

- Define the small typed request/result boundary between generic recovery and
  source-form materializers.
- Implement YAML and executable-fence adapters only where their source syntax
  and execution contracts already exist and can be validated end-to-end.
- Add fixtures with comments, quotes, block scalars, flow mappings, aliases,
  duplicate/malformed attributes, and non-default timeouts.
- Prove byte identity outside the single intended patch, then prove that the
  projected retry executes with the visible constraint.
- Prove unsupported forms emit an explicit frontier outcome and do not
  reserialize source or apply hidden execution policy.

## Deferred

- New executable-fence attribute grammars solely to support this task.
- Broad source-language coverage before a language has an established runtime
  and explicit editable constraint syntax.
- Reworking the attempt-local `/run` selection or generic recovery transition
  semantics already settled by the source-reference parent.

## Progress

- 2026-09-01: Added the first executable-fence adapter slice. Markdown fence
  scanning now retains source spans for individual header attribute values and
  the opening-header insertion point. `timeout_s` is accepted by the existing
  bash, Python, PowerShell, and explicit-runtime interpreter fence lanes.
  `retry_materialization.materialize_executable_fence_timeout` replaces only
  an existing timeout value or appends one header attribute, then reparses the
  patched fence. It preserves the body and closing fence byte-for-byte and
  explicitly refuses inactive, malformed, duplicate, JSON, and YAML forms.
  Wiring the adapter into generic source-reference recovery remains the next
  slice of this task.
- 2026-09-01: Wired the executable-fence adapter through the existing generic
  source-reference recovery transition. A failed referenced executable fence
  now projects the original fence with only the timeout header patch; it is
  not converted into YAML. A materialization refusal leaves the authored fence
  visible with an explicit instruction to edit its timeout before stepping.
  JSON and YAML remain deliberately body-governed forms rather than receiving
  a fence-header timeout projection.
