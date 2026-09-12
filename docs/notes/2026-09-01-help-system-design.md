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

When a dimension has multiple values, the collection must represent that
multiplicity structurally—using a sequence or nested object—not by joining
values with semicolons or embedding a second classification in prose. The
four dimensions remain separate even when one item is exposed on several
surfaces or serves more than one audience.

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

### Corpus tracks and phase gate

Every run must declare one track before collection:

```yaml
track: product | process
phase: product_coverage | process_review
```

`product` runs collect current help surfaces, related behavior, and the
relationships needed to describe what users or models can discover. `process`
runs inspect the inventory shape, collection procedure, validators, or review
mechanics. A product artifact may record a schema pressure as a local
candidate, but it must not turn that pressure into a process slice by default.

The process track is locked until a separate product-coverage report declares
all in-scope product surface families closed. That report must enumerate the
families and show each as `covered`, `covered_with_gap`, `empty_by_design`, or
`blocked`, with source references and an explicit reason for every non-clean
state. `covered_with_gap` is sufficient to move phases only when the gap is
recorded as a follow-on and no source family remains unexamined. A process
probe may run early only when it is the minimum check needed to make this gate
executable; it must be marked `gate_probe`, not used to expand process review.

The initial product-family checklist is deliberately broad rather than a
permanent inventory schema:

```yaml
product_surface_families:
  - cli_and_command_help
  - slash_command_help
  - callable_tool_reference
  - capability_and_dynamic_prompts
  - configuration_help_and_state
  - prompt_browse_and_render
  - history_and_projection_views
  - recovery_extract_replay_and_queue_workflows
  - documentation_and_acceptance_surfaces
```

The next product run must select an unclosed family or a cross-family seam
needed to close one. It must not select a validator concern merely because a
previous report listed it in `schema_changes` or `open_questions`.

At the end of each run, the report must include `track`, `phase`, and
`next_run_scope`. A report is invalid if a `process` run exists while the
product-coverage gate is open, unless it is explicitly marked `gate_probe`.
This prevents the word “matrix” or a growing schema-change list from silently
changing the work from product discovery to process review.

### 1. Declare a collection run

Every run should begin with a small run manifest. This is not yet the final
inventory schema; it is control metadata for the collection process.

```yaml
run:
  id:
  date:
  track: product | process
  phase: product_coverage | process_review
  scope:
    product_surfaces: []
    source_paths: []
    source_revisions: []
    runtime_profiles: []
    observed_scenarios: []
  schema_revision:
  collector:
  reviewer:
  gate_probe: false
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

Before review begins, every run artifact must parse as the declared format.
This is a collection gate, not a semantic review judgment: malformed YAML or
JSON should be found before a reviewer evaluates coverage, evidence, or
adjudication.

The process uses separate state vocabularies for collection and review:

```text
collection_state:
  pending → collecting → collected → reviewed
                      ↘ subdivided → reviewed
                      ↘ blocked
                      ↘ excluded

review_level: self | independent | dual
```

`subdivided` is a parent-source state. It is terminal only after every child
source has reached a terminal state and the parent-to-child coverage claim is
complete. `reviewed` means the collection artifact was inspected at the
declared `review_level`; it does not imply independent review or semantic
agreement.

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
    collection_state: pending | collecting | collected | subdivided | reviewed | blocked | excluded
    review_level: none | self | independent | dual
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
  collection_state: pending | collecting | collected | subdivided | reviewed | blocked | excluded
  review_level: none | self | independent | dual
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

Collection completeness, semantic completeness, and divergence are separate
statuses:

```yaml
collection_status: complete | incomplete | blocked
semantic_status: established | disputed | unresolved | not_applicable
divergence_status: none | open | accepted
```

For example, a source can be completely collected while producing an item
whose intended audience is still disputed. A run may claim complete collection
without claiming that every product decision has been settled.

### 6. Review evidence and conflicts

Review begins only after the run directory passes structural parsing. The
pre-review check should load the manifest, source ledger, every slice, the
conflict record, and the report, and should fail on malformed YAML/JSON,
missing required top-level sections, or unreadable references. A parseable
artifact may still fail later semantic and coverage gates.

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
every run artifact parses as its declared YAML/JSON format before review
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
`excluded` require reasons. `reviewed` means the slice passed its declared
review level; it does not imply that every item inside it is semantically
established.

### 8. Publish a run result, not just a corpus snapshot

The corpus should be accompanied by a run report:

```yaml
result:
  collection_status: complete | incomplete | blocked
  semantic_status: established | unresolved | disputed
  divergence_status: none | open | accepted
  status: complete | complete_with_divergence | incomplete | blocked
  source_counts: {}
  candidate_counts: {}
  item_counts: {}
  unresolved_questions: []
  unresolved_conflicts: []
  excluded_sources: []
  schema_changes: []
  track: product | process
  phase: product_coverage | process_review
  gate_probe: false
  product_coverage:
    status: open | ready_for_process_review
    families: []
  next_run_scope:
```

This keeps “we collected everything in scope” separate from “the product is
fully documented” and from “the sources agree.” A complete collection may
still contain unresolved semantic questions. `complete_with_divergence` should
mean `collection_status: complete` plus `divergence_status: open` or
`accepted`; it should not be used merely because the corpus contains ordinary
open questions.

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
8. No unresolved conflict remains unless `divergence_status` is `open` or
   `accepted` and the result is downgraded to `complete_with_divergence`.
9. Coverage reports show every declared surface, audience, and intent was
   examined, even when the result is zero items.
10. The validator reports zero schema errors and zero orphan references.
11. The run report records its source revisions, schema revision, and any
   excluded material.
12. If `track: process`, the product-coverage report has status
   `ready_for_process_review`, unless the run is explicitly a `gate_probe`.
13. A product-coverage report lists every declared product family and gives
   each a terminal disposition with evidence; an unexamined family keeps the
   gate open regardless of how many individual slices are complete.

These are intentionally phrased so they can later be implemented as a
validator over YAML/JSON. Until then, they are review gates and should be
applied manually to sample runs.

The future validator should have a narrow, deterministic contract:

```text
validate(run_directory)

exit 0  complete collection with no open or unaccepted divergence
exit 1  malformed artifact, incomplete coverage, or non-terminal source/slice
exit 2  schema or required-field error
exit 3  unresolved conflict or unaccepted divergence
exit 4  orphan, duplicate, or invalid parent/child reference
```

The validator should report machine-readable findings in addition to its exit
code. It should validate the run artifacts and references, not attempt to
judge prose quality or decide product intent.

Across runs, accepted items also need a global identity check. A later slice
must either reference an existing canonical item, create a new canonical item,
or record an explicit duplicate/split decision. Slice-local completion does
not permit two unlinked records to silently represent the same item.

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

## Product-coverage gate

The declared product surface families have now all been examined in bounded
product-track runs. The gate is closed with `covered_with_gap` status for each
family; no family is pending, blocked, or empty by design. The evidence and
follow-on gaps are recorded in
`docs/notes/help-corpus/2026-09-04-product-coverage-gate/`. The validator
batch remains process-track calibration and is not treated as product
coverage.

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

The next useful artifact is a product decision synthesis tied to observable
discovery paths. The representative corpus already exists; further schema
sketching is not the default next step. Implement bounded, sufficiently settled
improvements while leaving unrelated design questions explicit.

## Steering review — 2026-09-04

This is a direction-setting synthesis, not an independent review of all corpus
claims. The existing coverage-gate report establishes that nine families were
examined. It does not establish exhaustive item coverage or certify the runtime
probes in prior slices. Historical collection instructions above are procedure
reference; this section determines the next work.

The main risk is now failure to convert observations into decisions. Forty-six
collection passes include ten validator calibration passes, yet the candidate
gap list still largely asks for more definition. Permission to do process review
is not a reason to make it the next priority. The workboard's config UX vote
provides a concrete product outcome without requiring a global help registry.

### Decisions and dispositions

These are steering decisions/recommendations, not claims that current behavior
already satisfies the proposed contract.

| Covered family | Disposition and next evidence |
| --- | --- |
| Configuration help and state | Proceed with `260904-config-help-state-feedback`: guidance explains, inspection reports state, mutation reports effective change. Verify the starter discovery path. |
| Slash-command help | Apply that disclosure rule to config first. Defer global topic rearrangement until the config path demonstrates a navigation failure the local change cannot fix. |
| CLI and command help | Treat `/help cli` as curated orientation pending an explicit parity decision. Defer full inventory parity work; the history scenario must establish whether a missing onward link prevents discovery. |
| History and projection views | Retain distinct selection, lineage, topology, transcript, and model-input meanings. Next synthesis records one path from CLI help to the appropriate read-only view; use existing slices before collecting more. |
| Callable tool reference | Recommend that focused tool lookup expose exact required/optional arguments and defaults, while keeping profile visibility separate. Validate the `capture_task_thread` path before opening a child; whether “core” names priority or exposure remains undecided. |
| Capability and dynamic prompts | Keep runtime availability distinct from general instructions. Revisit labeling when the focused-tool scenario shows stale or misleading availability; do not make a static registry claim mean callable now. |
| Prompt browse and render | Preserve browse, render, activation, and resulting projection as distinct operations. Defer new metadata until a recorded discovery path requires it. |
| Recovery, extraction, replay, queue | Preserve preview, adoption, execution, and authorization boundaries. Defer broad renaming; reopen on a concrete help link that implies execution or approval incorrectly. Existing recovery slices are evidence, not proof of one canonical workflow. |
| Documentation and acceptance | Use scenario outcomes as the synthesis check. New prose or more corpus files alone do not demonstrate improved discoverability. |

### First concrete handoff

Current source inspection of
`src/toas/runtime/operator_command_config_help.py` establishes that bare
`/config` already routes to inspection; `/config --help` has no dispatch branch
and raises usage; `_config_set_result` renders the entire flattened config.
`src/toas/step.py:render_help_config` already supplies focused guidance. Thus
the first child can improve a known seam without inventing a help framework.
The workboard's 2026-09-04 priority vote supplies the desired behavior; source
inspection supplies the before-state. No runtime probe was performed in this
steering pass.

### Stop collecting; finish the synthesis

The next survey turn should record three bounded discovery scenarios using
existing evidence plus only the missing observations:

1. Human: `/help` → config guidance → inspect state → inspect choices → set one
   value → understand what changed and how long it lasts.
2. Human: CLI help → choose among heads/history/transcript/llm-input for one
   stated inspection intent, with no state mutation needed for discovery.
3. Model: overview → focused `capture_task_thread` lookup → recover full callable
   shape and distinguish availability from operating guidance.

For each, record entry point, user question, actual onward link, expected
answer, observed outcome, and any remaining failure with evidence. Do not
claim success from the presence of prose alone. These scenarios test the help
model; they do not require all three implementations to land before synthesis.

The parent can close when this nine-family disposition table and those three
scenario outcomes form a usable design reference, selected children have
bounded acceptance criteria, and remaining gaps are explicitly deferred with
reopening triggers. It stays open until those scenario outcomes are recorded.
No validator, exhaustive inventory, or universal vocabulary agreement is a
prerequisite. Reopen collection only for a specific missing fact that would
change a product decision.

## Collaborative synthesis — 2026-09-04

The configuration discussion narrows the help model without requiring a
global runtime registry. The survey corpus and its proposed inventory shape
are useful inspiration: they expose concepts, aliases, relationships,
audiences, and surface-specific behavior that can inform a smaller curated
configuration-help catalog. They remain evidence and design material, not an
automatic source of executable help output.

Configuration help and configuration operation should be treated as two entry
points into the same domain:

```text
/help config [topic-or-query]
  discover configuration concepts, keys, relationships, and next actions

/config
  compact usage and navigation hints, optimized for continued use

/config --help
  exact config-interface usage and syntax

/config show [filter]
  inspect effective live configuration, with filters
```

`/help config <query>` should combine a small curated topic vocabulary with
implicit apropos-like search over configuration key names and descriptions.
Curated topics provide semantic recall and a compact up-front explanation;
lexical matches provide broader discovery when the topic has not been
explicitly curated. A topic result should lead with the explanation, then
show related keys and onward operations. A search-only result may show ranked
matches and why each match was found.

The intended progression is:

```text
curated concept → compact explanation → related keys → exact config actions
keyword query  → ranked matches → descriptions → exact config actions
```

The same vocabulary may be shared by help search and `/config show` filters,
but their outputs must remain distinct: help explains what a setting means;
`show` reports current state. Help should not silently become a state dump.

The token `help` should remain meta-syntax rather than become a configuration
subcommand or topic. `/config --help` is the command-interface form, while
`/help config` is the conceptual discovery form. `/config` itself should
advertise both paths. Whether `/config help` is rejected with a diagnostic or
later accepted as a compatibility alias remains an explicit product choice;
it should not acquire a third semantic meaning.

The minimum conceptual record for a curated configuration topic is therefore
likely compact: a topic name, aliases, a short explanation, related config
keys, and onward inspection/value/mutation links. Exact key names and live
values should continue to come from the configuration system; descriptions
and topic relationships need an intentionally chosen static source rather
than accumulating independently in help prose, README text, and design notes.

### Optional help facets

Plain help and configuration help are best understood as optional facets of a
topic, not as a required one-to-one pair. Where a domain has both stable
behavioral invariants and user-adjustable behavior, the facets should share a
topic identity and cross-link:

```text
topic: extraction
  /help extraction
  /help config extraction

topic: history
  /help history
  (no config facet)

topic: shell
  /help shell
  /help config shell
  (possibly a capability facet)
```

Plain help explains what the domain does, what it guarantees, and which
distinctions matter. Its config cross-link is selective rather than a full
settings dump. Config help explains what is mutable, which keys and aliases
control it, what values are allowed, and when changes take effect. A
configuration area may temporarily have no mature plain-help counterpart;
the relationship is earned by semantic overlap rather than matching names.

The current major open questions are now bounded:

1. What is the smallest curated domain-topic set, and which lower-frequency
   config areas should remain search-only initially?
2. What static source owns topic summaries, key descriptions, aliases, and
   cross-links, while live schema and state remain owned by configuration
   code?
3. How should implicit search rank exact keys, key prefixes, descriptions,
   aliases, and curated-topic matches, especially for ambiguous queries?
4. What filter language should `/config show` use, and how much of that
   vocabulary should it share with `/help config` search?
5. How should dynamic facts—current values, provenance, available models,
   and timing/availability—be labeled so they are not mistaken for static
   help?
6. Should `/config help` be rejected with guidance or retained only as a
   compatibility alias for `/config --help`? It should not become a third
   semantic help surface.
7. Which plain-help topics need to be added before configuration topics can
   explain their invariants, particularly around extraction, execution,
   shell, and runtime timing?

The shared asset-library direction is now a candidate architecture rather
than an immediate relocation plan. Prompts, procedures, and help may move
under a common `assets/` package with a narrow shared loader for resource
identity, safe lookup, metadata, listing, and provenance. Their family
loaders should retain distinct semantics. The migration target and staged
posture are tracked in `260905-common-asset-library-migration`: old paths may
survive temporarily during bounded moves, but the intended final form has no
remaining compatibility adapters.

## Scenario evidence — configuration path, 2026-09-07

The configuration path now supplies a concrete discovery result for the
design model. The completed config UX slice and its acceptance coverage show
the following progression:

```text
/help config [topic-or-query]
  conceptual explanation, related keys, and next actions
      ↓
/config
  compact usage and navigation card
      ↓
/config show [filter] [--sources]
  effective values and winning provenance
      ↓
/config values KEY
  categorical choices where available
      ↓
/config set KEY VALUE
  compact effective before/after feedback and session boundary
```

This establishes a useful disclosure rule: guidance explains, inspection
reports state, and mutation reports effective change. It also confirms that
the same domain can have related surfaces without collapsing them into one
item. In particular, bare `/config` is navigation, while `/config show` is
state inspection; the former must not inherit the latter's full dump.

The scenario does not settle the global help vocabulary, universal indexing,
or the relationship between all prompt/procedure assets and help. It does
provide a product-level test for those decisions: a new help surface should
make its disclosure role and next operation clear without duplicating a
neighboring surface's entire output.

The next most informative rationalization slice is the human history path:
CLI help → an inspection intent → the appropriate heads/history/transcript/
llm-input view. It exercises the same separation between orientation and
state, while adding selection, lineage, and projection distinctions. The
focused capability lookup can follow as the contrasting model-facing case,
where runtime availability and operating guidance must remain separate.

## Scenario evidence — history inspection path, 2026-09-07

The existing history slices provide enough evidence to run the second
discovery scenario without another broad collection pass.

```text
toas help / toas --help
  lists heads, history, graph, transcript, and llm-input
      ↓
operator asks: which view answers my inspection question?
      ↓
toas heads       branch-tip/navigation targets
toas history    bounded root-to-head message lineage
toas graph      history topology
toas transcript history-backed executable-context reconstruction
toas llm-input  model-visible conversation or generation envelope
```

The command descriptions are individually accurate, and the corpus
establishes that these are distinct read-only projections with different
selection and disclosure roles. The scenario nevertheless fails at the
choice point: top-level CLI help names the neighboring commands but does not
explain which inspection question each one answers or link the user onward
with that distinction.

This is a navigation gap, not evidence that the commands should be merged or
renamed. The current evidence supports a compact history/projections
orientation item that preserves the five meanings and routes to exact CLI
usage. Whether that belongs in `toas help`, `/help cli`, a new plain-help
topic, or a combination remains open; the important acceptance condition is
that a user with an inspection intent can choose without already knowing the
projection vocabulary.

## Scenario evidence — capability lookup path, 2026-09-07

The capability slice uses `capture_task_thread` as a deliberately configured
and runtime-conditioned example. Its evidence crosses the registry, config,
focused `capability_help`, and dynamic prompt surfaces.

```text
capability overview
  what is advertised for the current profile
      ↓
capability_help(topic: "capture_task_thread")
  exact required/optional arguments and callable detail
      ↓
dynamic capability prompt
  operating policy, side-thread fork rule, and return behavior
```

The scenario establishes five separate claims:

- registry identity describes what the capability is;
- `capability_advertisement.profile` and `hidden_tools` affect configured
  exposure;
- effective profile state determines runtime visibility;
- `capability_help` supplies callable argument shape and defaults;
- prompt policy explains how the visible capability should be used.

Configured presence is therefore not equivalent to currently callable
availability. This is the capability analogue of keeping `/config show`
state separate from `/help config` explanation.

## Consolidated synthesis — 2026-09-07

The three scenarios now provide a usable product decision boundary:

| Scenario | Established help rule | Remaining gap |
| --- | --- | --- |
| Configuration | Guidance explains; bare entrypoints navigate; inspection reports live state/provenance; mutation reports effective change and durability. | Continue adding paired facets only where invariant/config distinctions are real. |
| History inspection | Related read-only projections should be chosen by the operator's question, then linked to exact commands. | Top-level CLI help still lists neighboring projections more effectively than it orients their choice. |
| Capability lookup | Static identity, configured exposure, runtime visibility, callable shape, and operating policy must remain separately labeled. | The model-facing overview and focused lookup do not yet share one explicit runtime-availability status contract. |

Across all three, help assets are the right home for stable conceptual
explanations, distinctions, aliases, and next actions. Runtime/configuration
owners remain authoritative for effective values, provenance, visible tools,
and callable schemas. A universal registry is not required to make this
boundary work.

The immediate design choices are now narrow:

1. Decide whether the concrete history navigation gap merits one more small
   orientation touch in top-level `toas help`, in addition to `/help history`
   and `/help cli`.
2. Decide whether capability availability needs a runtime status projection,
   or whether the current labeled distinction is sufficient until a stale or
   misleading prompt scenario appears.
3. Defer global help indexing, universal vocabulary, and broad asset
   migration until a concrete cross-family discovery failure requires them.

The parent survey now has evidence for all three required scenarios. Its
remaining value is to preserve these dispositions and reopening triggers,
not to authorize another general collection batch.
