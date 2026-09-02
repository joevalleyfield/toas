# TOAS Help System Design Survey

Status: DRAFT / DESIGN-ONLY
Date: 2026-09-01
Related task: `260901-help-system-design-survey`
Related direction: `260823-projection-discoverability`

## Intent

This note describes the help system as it exists today and sketches a future
user-facing model. It is deliberately not an implementation proposal. In
particular, it does not ask us to build a structured source of truth yet.

The immediate question is: what should a person or model be able to discover,
in what order, and with what distinction between an explanation, an example,
an executable command, and a capability advertisement?

## Existing surfaces

### 1. Top-level CLI help

Defined by `src/toas/cli.py` and reached through `toas help`, `toas --help`,
and `toas -h`.

It currently provides:

- a broad command list;
- the `TOAS_RPC_MODE` environment variable;
- a short explanation of history surfaces.

It covers stepping, async watch/cancel, backend lifecycle, history and
projection inspection, prompts, session continuation, surface binding,
replay scripts, and debug cancellation summaries.

Its shape is primarily a usage index. It does not currently explain command
relationships, common workflows, safety/authority boundaries, or the meaning
of the different history projections.

### 2. In-session slash-command help

Defined primarily in `src/toas/step.py`, dispatched by
`src/toas/runtime/operator_command_config_help.py`.

The compact `/help` view is a quick-start card pointing to six exact topics:

```text
/help full
/help commands
/help tools
/help cli
/help approvals
/help config
```

The full view combines:

- slash-command usage and one-line descriptions;
- the model-callable tool inventory;
- common configuration goals and examples;
- all valid configuration keys.

The topic views add two important semantics:

- `/help commands` marks examples inert so copying the whole result does not
  accidentally execute them;
- `/help approvals` explains replay queues and authorization boundaries.

This is the most operator-oriented surface, but it is also the most crowded.
It mixes discovery, reference material, recipes, policy explanation, and
configuration inventory in one family.

### 3. Tool reference and capability help

There are two related model-facing forms:

- `src/toas/tools_guidance.py` renders a full tool reference for prompt/help
  use;
- `src/toas/tools_cluster/capability_help_ops.py` implements the callable
  `capability_help` operation.

`capability_help` supports topic-oriented lookup (`core`, `editing`, `shell`,
`debug`, `all`) and individual tool names, with fuzzy aliases for likely
misspellings or broad terms. It gives argument shape, selected policy details,
and examples.

This surface is valuable because it supports progressive disclosure during a
run. It is not the same thing as operator help: it explains how a model may
call an explicitly available capability, not everything a human can do with
TOAS.

### 4. Capability advertisements and prompt-library material

`src/toas/capability_prompts.py` and the dynamic capability prompt assets
advertise a runtime-selected subset of tools and protocol constraints.

The current prompt material distinguishes:

- start-here guidance for choosing a first action;
- overview guidance for the current profile and callable shape;
- repo-work guidance for inspect/edit/test workflows;
- explicit capability-help escalation when argument shape is uncertain.

Unlike `/help`, these are contextual prompt inputs. They should be understood
as “what is available and how to behave in this run,” not as a complete product
manual.

### 5. Configuration help

Configuration help appears in several places:

- `/help config` gives command forms, durability, precedence, compatibility
  notes, prompt constraints, and selected examples;
- `/config show` reports effective values and precedence;
- `/config values <key>` reports categorical choices for one key;
- `docs/capabilities.md` documents the broader configuration and runtime model.

This is the strongest existing example of layered help: conceptual guidance,
current state, and a focused query are separate interactions. It is also a
source of duplication, especially around examples and precedence language.

### 6. Product and acceptance documentation

Relevant documentation already includes:

- `docs/capabilities.md` — current operator capability model;
- `docs/acceptance/operator-starter-triad.md` — `/help config` as a seed
  scenario;
- `docs/acceptance/spikes/help-config-*.md` — observed weak-model and operator
  friction around help/config/prompt discovery;
- `tasks/open/260823-projection-discoverability.md` — open design direction for
  prompt and projection discoverability;
- `docs/roadmap.md` — strategic framing for operator-surface clarity.

These documents contain design evidence that is not represented in the live
help output, particularly the distinction between conceptual projections,
executable context, and map-like/history views.

## Confirmed gaps and drift

### A. CLI inventory parity

`/help cli` is a hand-maintained subset of the actual CLI dispatcher. It does
not mention several dispatchable commands, including `watch`, `cancel`,
`backend`, `intents`, `session continue`, `surface`, `ancestry`, `diff`,
`index`, `replay-script`, and debug commands.

The top-level CLI usage is broader, but still does not provide a per-command
explanation or workflow grouping beyond the small history section.

### B. Tool inventory parity

Tool names are mostly registry-derived in `/help full` and `tools_guidance`,
but topic groupings and descriptions are independently authored. For example,
the capability-prompt core profile includes `capture_task_thread`, while the
`capability_help` core topic does not.

The result is not only maintenance duplication; it changes what a consumer is
told is “core.”

### C. Description and example duplication

Tool summaries, callable examples, shell policy text, newline policy text, and
configuration examples occur in multiple modules and docs. Some are concise
and some are operationally detailed. There is no documented rule for which
surface should be authoritative when they differ.

### D. Human help versus model capability

The current output makes these concepts adjacent enough to be conflated:

- a CLI command the operator can invoke;
- a slash command that changes or inspects transcript state;
- a model-callable tool exposed in the current profile;
- a prompt asset that teaches a protocol or workflow;
- a documentation-only concept or design direction.

The system already has the right semantic distinctions internally, but the
help model does not consistently name them.

### E. Progressive disclosure is uneven

`/help` has compact and topic forms, and `capability_help` has topic/tool forms,
but the CLI and docs do not have equivalent “start here → focused reference →
exact usage” paths. `/prompt` provides a parallel discovery path for prompt
assets, without a documented relationship to `/help`.

### F. Dynamic versus static truth is unclear

Some information is runtime-dependent: visible tools, shell allowlist,
configured backends/models, effective config, selected surfaces, and defaults.
Other information is stable product guidance. The current surfaces expose both
without consistently labeling whether a line is:

- a current runtime fact;
- a general rule;
- an example;
- a compatibility note;
- a design or documentation claim.

## Proposed conceptual model

The future help system should be thought of as a small set of named lenses,
not one giant manual:

```text
start here
  ├─ operate the current session
  │    ├─ slash commands
  │    ├─ approvals / replay
  │    └─ configuration
  ├─ inspect durable state
  │    ├─ heads / history / graph
  │    ├─ transcript / llm-input
  │    └─ ancestry / diff / intents
  ├─ run or connect TOAS
  │    ├─ step / async / watch / cancel
  │    ├─ backend / daemon / host
  │    └─ surfaces / continuation
  ├─ understand callable capabilities
  │    ├─ available now
  │    ├─ tool shape and limits
  │    └─ examples
  └─ explore prompt and projection assets
       ├─ prompt library
       ├─ conceptual projections
       └─ executable-context projections
```

This is a design grouping, not a proposed command syntax. It gives each item a
primary question and makes room for the same item to have multiple views
without pretending those views are identical.

## Inventory schema direction

The inventory should not be forced into a conventional two-dimensional table.
The word “matrix” is useful only to suggest deliberate cross-comparison. The
eventual artifact should instead be an extensible structured document, likely
JSON or YAML, so that relationships, alternatives, nested content, and
dimension-specific evidence can remain explicit.

At minimum, four dimensions should remain separate top-level concerns rather
than being collapsed into labels or tags:

```yaml
item:                         # what exists
surface:                      # where it is exposed
audience:                     # who consumes it
intent:                       # what the consumer is trying to do
```

These dimensions answer different questions:

- `item`: the command, tool, prompt, projection, concept, or workflow being
  described;
- `surface`: CLI, slash command, callable capability, prompt library,
  transcript projection, documentation, or acceptance artifact;
- `audience`: human operator, model, maintainer, or test/acceptance reader;
- `intent`: operate, inspect, configure, select, transform, recover, explain,
  authorize, or discover.

The schema should also leave room for separate subordinate structures rather
than flattening everything into fields on one row:

```yaml
identity:
  canonical_name:
  aliases: []
  compatibility_forms: []
placement:
  workflow_areas: []
  parent_topics: []
content:
  summary:
  when_to_use:
  invocation:
  examples: []
behavior:
  output_shape:
  state_effect:
  durability:
  authority:
constraints:
  policy: []
  safety: []
  prerequisites: []
availability:
  static_or_dynamic:
  runtime_dependencies: []
disclosure:
  role:
  next_topics: []
evidence: []
status:
```

This sketch is intentionally not a final schema and contains no inventory
entries. Its purpose is to prevent premature flattening. In particular,
aliases, examples, evidence, and relationships may each need their own shape;
they should not automatically become string-valued columns.

The first real collection pass should therefore gather a few representative
items as nested objects, test whether the four dimensions stay independent,
and only then decide which subordinate structures are genuinely needed.

## Progressive discovery protocol

The inventory should be developed through repeatable discovery passes over
small slices. Each pass should answer a bounded set of questions, preserve
source evidence, and update only the slice under examination. This gives us a
way to discover missing dimensions while avoiding a premature exhaustive
catalog.

### Core questions for every slice

1. What concrete item or family of items is being examined?
2. On which surface does it appear, and is that surface human-facing,
   model-facing, documentation-facing, or shared?
3. Who is expected to consume it?
4. What intent does it support or express?
5. What is the shortest accurate explanation of what it is?
6. What exact invocation, selector, callable shape, or navigation step is
   available?
7. What does using it produce, mutate, persist, or leave untouched?
8. What authority, policy, safety, or inertness constraints apply?
9. Which parts are static guidance and which depend on runtime/config/session
   state?
10. What neighboring item, prerequisite, alias, or next disclosure step is
    relevant?
11. What evidence supports each important claim, and is that evidence source
    code, observed behavior, existing help content, documentation, or
    inference?
12. What remains unknown, contradictory, or intentionally out of scope?

### Slice-specific follow-ups

The core questions should be supplemented according to the slice:

- CLI command slice: command family, options/defaults, exit/output behavior,
  local-versus-RPC routing, and relationship to other commands;
- slash-command slice: transcript lane, durable side effects, control versus
  user-facing output, inert examples, and whether the command changes the
  next frontier;
- tool slice: current visibility/profile, required and optional arguments,
  callable aliases, policy limits, write/destructive behavior, and result
  shape;
- prompt-asset slice: asset category, composition role, intended consumer,
  whether it teaches protocol or workflow, and whether it describes current
  capabilities or supplies operating instructions;
- projection/history slice: source lineage, selection semantics, projection
  purpose, inclusion/exclusion rules, and whether the result is conceptual,
  executable-context, diagnostic, or durable;
- configuration slice: key or command scope, allowed values, precedence,
  durability, timing of effect, secret handling, and startup-only/runtime-
  adjustable status;
- documentation/acceptance slice: normative status, audience, scenario or
  claim under test, observed friction, and relationship to live behavior.

### Suggested pass sequence

The questions can be applied progressively:

1. Start with a representative operator path, such as `/help config`, to
   identify the minimum useful fields.
2. Compare one CLI history command with its related slash/help or documentation
   explanation to test surface and audience separation.
3. Compare one callable tool across registry help, capability help, and prompt
   advertisement to expose profile and description drift.
4. Examine one prompt asset and one projection to test whether item identity,
   intent, and disclosure role remain distinct.
5. Only then expand to adjacent families and add fields justified by repeated
   evidence.

Each pass should produce three separate outcomes:

```yaml
observations: []       # what the sources or runtime visibly show
candidate_fields: []   # schema dimensions needed to represent the slice
open_questions: []     # unresolved product or semantic decisions
```

The pass should not silently convert an observation into a product rule. A
claim such as “this is a core capability” requires either explicit product
intent or a clearly marked inference; repeated appearance in help output is
evidence of exposure, not automatically evidence of priority.

## Repeatable corpus-building process

The progressive passes can become a repeatable process for building an
exhaustive corpus if “exhaustive” is always qualified by a declared collection
boundary. The process must first enumerate the sources in scope, then account
for every discoverable item in those sources, and finally prove that every
record has either passed review or has an explicit unresolved disposition.

### 1. Declare a collection run

Every run should begin with a small run manifest. This is not yet the final
inventory schema; it is control metadata for the collection process.

```yaml
run:
  id:
  date:
  scope:
    product_surfaces: []
    source_paths: []
    source_revisions: []
    runtime_profiles: []
    observed_scenarios: []
  schema_revision:
  collector:
  reviewer:
```

The scope must say whether the run covers source code, rendered output,
runtime observations, documentation, acceptance transcripts, or some bounded
combination. A run that omits a source class is incomplete only relative to
that declared scope, not globally defective.

The run should have a stable artifact boundary, even while the corpus schema
is still evolving:

```text
run/
  manifest.yaml
  sources.yaml
  slices/
    <slice-id>.yaml
  conflicts.yaml
  report.yaml
```

The run manifest and source ledger control completeness. Slice files contain
observations and candidate records. The conflict file contains adjudication
that cannot be represented as an ordinary item decision. The report is the
only place that claims whether the run is complete.

### 2. Build a source ledger before extracting items

The source ledger is the completeness boundary. It should enumerate each
source unit in scope and assign a collection state:

```yaml
sources:
  - id:
    kind: implementation | rendered_help | prompt_asset | documentation | acceptance | runtime_probe
    path_or_reference:
    revision_or_observed_at:
    expected_item_families: []
    state: pending | collected | reviewed | blocked | excluded
    exclusion_reason:
```

Source units should be chosen at a useful granularity: a module or command
family for implementation, a topic/output mode for rendered help, an asset for
prompts, and a scenario or section for acceptance material. The ledger should
not use “the repository” as one undifferentiated source.

### Subdivision is an explicit scoping operation

A chosen unit may turn out to be untenable after inspection. It may contain
multiple unrelated help families, cross several audiences, require different
runtime profiles, or be too large to review with reliable evidence. The
collector may subdivide it either while choosing the initial slice in step 1
or later as a state transition during collection.

Subdivision must preserve provenance and coverage. The original unit becomes a
non-terminal parent with a recorded reason and an explicit child list; it is
not marked collected merely because some of its content was examined.

```yaml
sources:
  - id: cli_surface
    state: subdivided
    subdivision_reason: mixed command families and runtime ownerships
    children: [cli_history, cli_runtime, cli_transport]
```

The same rule applies to candidate items discovered to contain several
concepts. A candidate may be split into child items when its identity,
audience, intent, or surface-specific behavior cannot be represented without
ambiguity. The split should retain a parent relationship and explain whether
the parent remains a meaningful concept or is only a collection container.

### 3. Extract candidates without interpretation

For each pending source unit, collect candidate items and raw observations
first. At this stage, preserve names, invocation text, descriptions, examples,
and source locations as encountered. Do not resolve aliases, merge concepts,
or infer intended audience yet.

The extraction result should separate:

```yaml
source_observations: []
candidate_items: []
candidate_relationships: []
candidate_fields: []
extraction_questions: []
```

This makes omissions visible: a source can be marked collected only when its
candidate set and extraction questions are both present.

The unit of work should have a small handoff record identifying:

```yaml
slice:
  id:
  source_ids: []
  collector:
  reviewer:
  purpose:
  boundary:
  state: pending | collecting | collected | subdivided | reviewed | blocked | excluded
  parent_slice:
  child_slices: []
```

`boundary` should say what is deliberately not being collected in this slice.
That prevents a collector from treating adjacent omissions as accidental
gaps, while still leaving them available for a later slice.

### 4. Normalize and adjudicate candidates

After extraction, compare candidates across sources. Each candidate should be
classified as one of:

- new item;
- additional surface of an existing item;
- alias or compatibility form;
- example or recipe, not an item;
- relationship or prerequisite, not an item;
- duplicate observation;
- unresolved collision.

Adjudication is where the four independent axes are tested. A candidate must
not be merged merely because its spelling matches another candidate, and it
must not be split merely because it appears on a different surface. The
decision should preserve both the concept identity and the surface-specific
expression when those differ.

Adjudication should have an explicit authority order:

1. observed runtime behavior for claims about what currently happens;
2. implementation references for claims about what the current build defines;
3. explicit product/design intent for claims about what the system is meant to
   communicate;
4. existing help and documentation as evidence of what is currently exposed
   or claimed, not automatic authority over behavior;
5. collector inference only when marked as inference.

When these layers disagree, preserve the disagreement and classify it rather
than choosing one silently. The reviewer may resolve a conflict only by
recording the authority used and the reason the other evidence does not govern
that claim.

### 5. Complete the item record

An item is corpus-complete only when the collection process has attempted the
required fields and recorded an explicit outcome for each. “Not applicable,”
“unknown,” and “not yet observed” must remain distinguishable.

The minimum completeness contract is:

```yaml
item:
  identity: required
  dimensions:
    item: required
    surface: required
    audience: required_or_explicit_unknown
    intent: required_or_explicit_unknown
  content: required
  behavior: required_or_explicit_unknown
  constraints: required_or_explicit_not_applicable
  availability: required_or_explicit_not_applicable
  disclosure: required_or_explicit_not_applicable
  evidence: one_or_more_typed_entries
  status: required
```

The exact field names may change. The important process rule is that blanks are
not silently accepted as completion.

Collection completeness and semantic completeness are separate statuses:

```yaml
collection_status: complete | incomplete | blocked
semantic_status: established | disputed | unresolved | not_applicable
```

For example, a source can be completely collected while producing an item
whose intended audience is still disputed. A run may claim complete collection
without claiming that every product decision has been settled.

### 6. Review evidence and conflicts

Every consequential claim should point to typed evidence. Review should
separate:

- `surface_content`: what existing help or prompt text says;
- `behavior_observation`: what a runtime or acceptance probe demonstrated;
- `implementation_reference`: what source code currently defines;
- `documentation_claim`: what a product/design document asserts;
- `design_inference`: what the collector concludes from other evidence.

Conflicting evidence should create an explicit conflict record rather than
being silently reconciled:

```yaml
conflicts:
  - id:
    items: []
    claims: []
    evidence: []
    disposition: open | resolved | accepted_divergence
    rationale:
```

### 7. Close the source ledger and run coverage checks

The run closes only after every source unit is in a terminal state and every
terminal state is justified. A subdivided source is terminal only when all of
its children are terminal and the parent-to-child coverage is complete.
`excluded` and `blocked` are allowed outcomes, but they prevent an
“exhaustive and clean” result unless the run explicitly accepts them.

The future validator should be able to evaluate gates equivalent to:

```text
source_ledger has no pending entries
source_ledger has no blocked entries
every subdivided source has a non-empty child list and complete child coverage
no subdivided source is also treated as directly collected without an explicit reason
every collected/reviewed source has candidate_items or an explicit empty result
every candidate has exactly one adjudication outcome
every accepted item has all required fields or explicit unknown/not_applicable
every accepted item has typed evidence
every conflict is resolved or explicitly accepted as divergence
every declared surface and audience appears in coverage reports
```

State transitions should be explicit:

```text
pending → collecting → collected → reviewed
                    ↘ subdivided → reviewed
                    ↘ blocked
                    ↘ excluded
```

`subdivided` is a controlled terminal state for the parent only when every
child is terminal and the parent coverage claim is satisfied. `blocked` and
`excluded` require reasons. `reviewed` means the slice passed review; it does
not imply that every item inside it is semantically established.

### 8. Publish a run result, not just a corpus snapshot

The corpus should be accompanied by a run report:

```yaml
result:
  status: complete | complete_with_divergence | incomplete | blocked
  source_counts: {}
  candidate_counts: {}
  item_counts: {}
  unresolved_questions: []
  unresolved_conflicts: []
  excluded_sources: []
  schema_changes: []
  next_run_scope:
```

This keeps “we collected everything in scope” separate from “the product is
fully documented” and from “the sources agree.” A complete run may still
contain accepted divergences or unresolved product questions, but those must
be visible in the result.

### Executable exit criteria

A collection run can claim `complete` only if all of the following are true:

1. The scope manifest names every source class and concrete source unit in
   scope.
2. No source unit remains `pending` or `blocked`.
3. Every `subdivided` source has complete terminal child coverage and a
   recorded subdivision reason.
4. Every source unit has an extraction result, including an explicit empty
   result where no candidate exists.
5. Every candidate has one and only one adjudication outcome.
6. Every accepted item satisfies the completeness contract.
7. Every item has typed evidence, including provenance for inferred claims.
8. No unresolved conflict remains unless the result is downgraded to
   `complete_with_divergence`.
9. Coverage reports show every declared surface, audience, and intent was
   examined, even when the result is zero items.
10. The validator reports zero schema errors and zero orphan references.
11. The run report records its source revisions, schema revision, and any
   excluded material.

These are intentionally phrased so they can later be implemented as a
validator over YAML/JSON. Until then, they are review gates and should be
applied manually to sample runs.

The future validator should have a narrow, deterministic contract:

```text
validate(run_directory)

exit 0  complete collection with no unaccepted divergence
exit 1  incomplete coverage or non-terminal source/slice
exit 2  schema or required-field error
exit 3  unresolved conflict or unaccepted divergence
exit 4  orphan, duplicate, or invalid parent/child reference
```

The validator should report machine-readable findings in addition to its exit
code. It should validate the run artifacts and references, not attempt to
judge prose quality or decide product intent.

### Worked process fixture: `/help config`

Before collecting the complete help corpus, a small fixture can test the
process itself. This is a procedure example, not an inventory entry:

```yaml
slice:
  id: slash-help-config
  source_ids:
    - step-help-renderers
    - operator-help-dispatch
    - config-help-acceptance
  purpose: test the minimum collection and review loop
  boundary: excludes other slash topics and all CLI help
  state: reviewed

observations:
  - kind: surface_content
    claim: /help config exposes command forms, precedence, durability, and examples
  - kind: behavior_observation
    claim: /config values <key> provides focused categorical lookup
  - kind: documentation_claim
    claim: the starter triad treats /help config as a first-principles path

candidate_items:
  - provisional_identity: config-help
    adjudication: new_item
    dimensions:
      item: config help
      surface: slash command
      audience: human operator
      intent: discover and configure
    semantic_status: established

candidate_fields:
  - availability.runtime_dependent
  - behavior.durability
  - content.examples

open_questions:
  - whether /config show belongs to the same item or a related focused item
```

The fixture passes only if its source units are explicitly registered, its
observations are typed, its candidate has an adjudication, its required fields
are either filled or explicitly unknown, and its open question does not get
mistaken for a failed collection gate. A later validator can use this fixture
as a contract test for the run format.

Each help item should eventually distinguish four layers:

1. What is it?
2. When would I use it?
3. What is the exact invocation or callable shape?
4. What limits, authority, durability, or projection semantics matter?

Short help should answer layer 1 and point onward. Focused help should answer
layers 2–4 without reproducing every neighboring topic.

## Design questions to resolve later

- Should `toas help` and `/help` share headings and vocabulary while remaining
  separate surfaces?
- Should CLI help be organized by workflow rather than dispatcher order?
- Is `/help tools` the right home for model-callable tools, or should it be
  explicitly labeled as runtime capability reference?
- Should `/prompt` appear as a help topic, and should prompt assets declare
  whether they are instructional, executable-context, or projection-oriented?
- Which data must be live: visible tool profile, shell grants, config values,
  backend/model choices, selected surface, and history anchor?
- Which examples must be inert by construction, and which should be copyable
  one line at a time?
- How should aliases and compatibility commands be presented without making
  them look like preferred paths?
- What is the smallest “start here” card that works for a new human operator,
  a weak model, and an experienced maintainer?
- Which dimensions must be present on every item, and which can be absent or
  represented by an explicit `unknown`/`not_applicable` value?
- Which relationships are item-to-item references, and which are merely
  navigational groupings?
- Should one item have multiple surface projections, or should each
  item/surface pairing be a distinct inventory object linked to one concept?
- Is YAML the better review format, with JSON as a machine interchange form,
  or should the design remain format-neutral until the sample collection?

## Candidate gap list for follow-on tasks

1. Define shared vocabulary for CLI command, slash command, tool capability,
   prompt asset, projection, recipe, and runtime fact.
2. Produce a manually reviewed command/capability matrix across all existing
   help surfaces.
3. Decide the intended audience and primary question for each help topic.
4. Reconcile the meaning of “core” across capability prompts and
   `capability_help`.
5. Identify which duplicated descriptions are policy truth versus examples or
   convenience prose.
6. Design a live-fact versus static-guidance labeling convention.
7. Define the CLI help workflow groupings and the minimum explanation for each
   command family.
8. Define the relationship between `/help`, `/prompt`, and projection
   discovery.
9. Add acceptance scenarios for first-principles discovery, especially the
   existing `/help config` starter triad and a CLI history-inspection path.
10. Only after the above decisions, evaluate whether any structured inventory
    would reduce drift without becoming an unused abstraction.

## Current conclusion

The immediate problem is not that TOAS lacks help text. It has several useful
help mechanisms, each optimized for a different audience or moment. The
problem is that their boundaries and relationships are implicit.

The next useful artifact is therefore a reviewed structured-schema sketch and a
small representative sample of audience/workflow scenarios. The sample should
test dimensional independence without becoming the inventory itself.
Implementation should follow those decisions, not precede them.
