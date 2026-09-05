Filed as: 260901-help-system-design-survey
FKA:
AKA: help system design; help inventory; help discoverability
Legacy index:

Parent: `260823-projection-discoverability`
Related: `260628-heads-selected-history-leaf-framing`; `260627-history-affordances-semantic-restaging`

keywords: docs, investigation, active, usability, discoverability, parity, surface

# Help System Design Survey

## Objective

Describe the current TOAS help and discoverability surfaces in design/docs
space, drawing on their existing behavior before proposing implementation
structure.

This task deliberately does not introduce a structured runtime registry,
generated help, or a synchronization mechanism.

## Current phase

The product-family coverage gate is recorded as closed with gaps. Current work
is product synthesis and bounded handoff, not another collection batch. The
2026-09-04 steering review in the design note supersedes historical “next slice”
sign-posts below. The gate establishes sampled family coverage, not exhaustive
command coverage, independent validation, or resolved product semantics.

First implementation follow-on: `260904-config-help-state-feedback`. It is
ready to start from the existing operator priority vote and does not depend on
closing this parent. Ordinary process/schema work remains deferred unless a
specific defect prevents a product decision.

## Acceptance criteria

- Inventory the current CLI, slash-command, tool, capability-prompt, config,
  and documentation surfaces.
- Record confirmed overlaps, omissions, terminology differences, and likely
  sources of drift.
- Propose a conceptual help model and progressive-disclosure shape without
  choosing an implementation yet.
- Produce a gap list that can be turned into narrow implementation tasks later.
- Preserve the distinction between current behavior, design inference, and
  unresolved product questions.
- Define and exercise a repeatable bounded-slice collection process with
  explicit source coverage, review level, subdivision, and exit status.
- Keep product-surface collection separate from process/schema review.
- Do not begin ordinary process review until the declared product-surface
  families have all been examined and the product-coverage gate is recorded.

## Deliverable

`docs/notes/2026-09-01-help-system-design.md`

## First collection pass

The first bounded collection run is recorded at
`docs/notes/help-corpus/2026-09-01-slash-help-config/`. It follows the design
note's `/help config` starting slice and includes a manifest, source ledger,
typed observations, candidate adjudication, conflicts, and a run report.

The pass establishes `/help config` as a human-facing slash-help orientation
item. It keeps the linked `/config` command family separate because its
subcommands have different state effects and durability. The live probe also
confirms that the help response is a slash-command result projected as an
inert fenced view, which should be represented as behavior rather than inferred
from the prose alone.

Retrospective lessons and light critique are collected in
`docs/notes/2026-09-02-help-survey-lessons.md`; they are not repeated here so
they do not become accidental slice prescriptions.

Run result: collection complete with unresolved semantics and self-review;
the remaining divergence is represented as explicit open questions rather than
silently resolved. The next prescribed slice is `toas history`, compared with
the top-level CLI help and the history/projection explanation in
`docs/capabilities.md`. Its boundary excludes other history commands and
runtime transport behavior.

## Second collection pass

The second bounded collection run is recorded at
`docs/notes/help-corpus/2026-09-01-history-command/`. It compares the
executable `toas history` CLI item with the documentation-facing explanation
of its root-to-head lineage projection, and includes a manifest, source ledger,
typed observations, candidate adjudication, conflicts, and a run report.

The live probe confirms that `toas history` is a read-only message-lineage
projection: the selected lineage is bounded to the newest requested rows, an
explicit anchor changes the endpoint, and an empty source renders a `(-)` head.
The record keeps the documentation explanation related but distinct from the
CLI item, and leaves neighboring `heads`, `graph`, `transcript`, and `llm-input`
surfaces outside the slice except as navigation context.

Run result: collection complete with unresolved semantics and self-review; the
remaining product questions concern projection vocabulary, advanced option
disclosure, and relationships among neighboring history surfaces.

## Next slice sign-post

The next bounded collection run is the callable-tool comparison prescribed by
the design note:

- slice: one tool across registry help, `capability_help`, and prompt
  advertisement;
- primary questions: what is currently visible, how is “core” determined, and
  which descriptions or examples drift across surfaces;
- required evidence: tool registry/reference, capability-help detail, dynamic
  capability prompt output, and at least one runtime/profile observation;
- boundary: excludes the complete tool inventory, unrelated prompt assets, and
  human-only CLI/slash help except where needed to establish terminology.

The slice should specifically test whether profile visibility, audience, and
callable shape remain independent dimensions, and should record any resulting
schema changes before expanding to additional tools.

## Third collection pass

The third bounded collection run is recorded at
`docs/notes/help-corpus/2026-09-01-capture-task-thread/`. It compares the
`capture_task_thread` callable across registry-derived tool help, direct
`capability_help`, and the dynamic capability overview, with a runtime/profile
probe and targeted behavior tests.

The probe confirms that registry membership, effective profile visibility, and
prompt policy are separate dimensions: the tool is visible in the default
`core` profile and in `full`/`debug`, can be hidden explicitly, and causes the
dynamic task-capture policy to appear only when visible. The focused
`capability_help` view currently reports only required arguments, while the
registry help and prompt shape expose optional arguments/defaults and the
prompt adds operational policy.

Run result: collection complete with unresolved semantics and open
surface-detail divergence; independent review was not performed.

## Next slice sign-post

The next bounded collection run should examine one prompt asset together with
one related projection, as prescribed by the design note:

- primary questions: whether item identity, intent, and disclosure role remain
  independent when the asset teaches a workflow and the projection changes
  what is visible;
- required evidence: prompt-asset source and rendered content, projection
  implementation and runtime behavior, plus any related acceptance or
  documentation claim;
- boundary: excludes broad prompt-library enumeration and unrelated projection
  families; select one asset/projection pair with an explicit relationship.

The slice should use structural multiplicity for any item exposed across
several surfaces or audiences, and should record whether the prompt is
instructional, executable-context, or projection-oriented content.

## Fourth collection pass

The fourth bounded collection run is recorded at
`docs/notes/help-corpus/2026-09-01-concept-graph-projection/`. It compares the
`concept-graph/projection_v1` prompt asset with `/concept-graph`, its generated
projection message, and the durable concept-graph record/artifact.

The run keeps the instructional prompt, activation command, and generated
projection as related but distinct items. It confirms that provenance,
artifact materialization, and continuation ordering are behavior evidence, not
properties of the prompt asset itself.

Run result: collection complete with unresolved semantics and open projection
detail; self-review only.

## Fifth collection pass

The fifth bounded collection run is recorded at
`docs/notes/help-corpus/2026-09-01-compaction-handoff/`. It compares the
`compaction/handoff_v1` prompt asset with `/compact` and the durable
`compaction_projection` handoff record.

The run establishes compaction as a recovery/continuation projection rather
than merely a text-shortening prompt. It records source-transcript
preservation, handoff provenance, and explicit successor-context behavior as
separate help fields.

Run result: collection complete with unresolved terminology and open handoff
detail; self-review only.

## Sixth collection pass

The sixth bounded collection run is recorded at
`docs/notes/help-corpus/2026-09-01-prompt-browse-render/`. It examines prompt
browsing and rendering across static and dynamic assets through `toas prompt`,
`toas prompts`, `/prompt`, and `/prompts`.

The run confirms that parent-prefix browsing and leaf rendering are separate
disclosure operations over shared asset identities. Dynamic assets share the
same navigation surface but have runtime-conditioned content, and the slash
compatibility alias remains a surface concern rather than a new asset.

Run result: collection complete with unresolved navigation semantics and open
metadata divergence; self-review only.

## Follow-on sign-post

These three slices add evidence for prompt roles, recovery intent, durability
layers, browse/render operations, and invocation-surface effects. Before
expanding the corpus further, the next bounded slice should test one adjacent
history/projection family and explicitly compare its navigation vocabulary with
prompt discovery. No implementation task is proposed yet; the remaining gaps
are still suitable for narrow design follow-ons.

## Seventh through sixteenth collection passes

Ten further bounded collection runs are recorded under
`docs/notes/help-corpus/2026-09-01-graph-projection/` through
`docs/notes/help-corpus/2026-09-01-session-continue/`:

- `graph-projection` compares temporal/consequence topology views with prompt
  prefix navigation and adds an explicit navigation crosswalk.
- `transcript-projection` records durable-history reprojection as an
  executable-context/recovery view distinct from step-time reconciliation.
- `llm-input-projection` separates the core model-visible body from optional
  envelope shaping.
- `heads-leaf-set` records heads as compact graph-leaf navigation targets,
  distinct from bounded lineage history.
- `ancestry-diff` compares message-to-parent and head-to-head diagnostics and
  adds a diagnostic-axis field.
- `intents` records non-message intent inspection as its own durable-state
  family.
- `async-watch-cancel` records run creation, event observation, and
  cancellation as one lifecycle workflow, including cursor and policy gates.
- `backend-lifecycle` keeps backend process health/ownership separate from
  asynchronous run lifecycle.
- `surface-binding` records named transcript routing and durable selection
  controls, including rebind provenance.
- `session-continue` records explicit CLI/editor continuation and its
  non-generating behavior.

All ten runs passed the manual collection gates: five declared sources per
run, no pending/blocked/excluded sources, typed observations, adjudication for
each candidate, typed evidence, and parseable control artifacts. Each remains
self-reviewed only and reports open terminology or disclosure questions where
the sources do not settle product intent.

Retrospective lessons from this batch are consolidated in
`docs/notes/2026-09-02-help-survey-lessons.md`.

Batch result: ten collections complete with unresolved semantics and open
divergence status; no implementation task is proposed yet. The next bounded
slice should cover replay/extraction surfaces, with explicit separation of
preview, adoption, execution, queue authorization, and malformed-content
salvage.

## Seventeenth through twenty-sixth collection passes

Ten further bounded collection runs are recorded under
docs/notes/help-corpus/2026-09-02-extract-preview/ through
docs/notes/help-corpus/2026-09-02-replay-script/. They cover extraction
preview, shape selection, adoption, malformed YAML salvage, plan coalescing,
replay discovery, dry-run/force controls, queue authorization, queue controls,
and the standalone replay-script harness. Each run has a manifest, five-source
ledger, typed observations, candidate adjudication, conflicts, and a report.

All ten runs passed the manual collection gates: five declared sources per
run, no pending/blocked/excluded sources, typed observations, adjudication for
each candidate, typed evidence, and parseable control artifacts. They remain
self-reviewed only and report unresolved semantics/open divergence rather than
silently deciding terminology.

Retrospective lessons from this batch are consolidated in
`docs/notes/2026-09-02-help-survey-lessons.md`.

Batch result: ten collections complete with unresolved semantics and open
divergence status; no implementation task is proposed yet. The next bounded
slice should test how these recovery/execution surfaces should be named and
linked from human-facing help topics.

## Twenty-seventh through thirty-sixth collection passes

Ten further bounded collection runs are recorded under
`docs/notes/help-corpus/2026-09-02-help-approvals/` through
`docs/notes/help-corpus/2026-09-02-acceptance-recovery-path/`. They cover the
`/help approvals`, `/help commands`, `/help cli`, and `/help full` topics;
the extraction-to-replay and replay-to-queue help links; the standalone
`toas replay-script` entrypoint; a capabilities terminology crosswalk; and
the operator starter acceptance path.

All ten runs passed the manual collection gates: five declared sources per
run, no pending/blocked/excluded sources, typed observations, adjudication for
each candidate, typed evidence, and parseable control artifacts. They remain
self-reviewed only and retain unresolved semantics/open divergence rather
than silently selecting a canonical vocabulary.

Retrospective lessons from this batch are consolidated in
`docs/notes/2026-09-02-help-survey-lessons.md`.

Batch result: ten collections complete with unresolved semantics and open
divergence status; no implementation task is proposed yet. The next bounded
step is a product-track slice from an unclosed surface family or a narrowly
scoped human-help workflow-link slice. Validator-oriented work is deferred
until the product-coverage gate is closed.

## Thirty-seventh through forty-sixth collection passes

Ten validator-oriented bounded collection runs are recorded under
`docs/notes/help-corpus/2026-09-02-validator-parseability/` through
`docs/notes/help-corpus/2026-09-02-validator-report-contract/`. They examine
artifact parseability, source-ledger closure, candidate adjudication
cardinality, subdivision coverage, accepted-item completeness, typed evidence,
conflict/divergence handling, workflow-reference resolution, independent
surface/audience/intent coverage, and the run-report/exit-code contract.

All ten runs passed the manual collection gates: five declared sources per
run, no pending/blocked/excluded sources, typed observations, adjudication for
each candidate, typed evidence, and parseable control artifacts. They remain
self-reviewed only and retain unresolved semantics/open divergence. A
read-only PyYAML probe loaded all 180 pre-existing corpus YAML files without
parse errors; this establishes structural parseability only and does not
detect duplicate keys or semantic/reference errors.

Retrospective lessons from this batch are consolidated in
`docs/notes/2026-09-02-help-survey-lessons.md`. This validator batch is now
classified as process-track calibration and does not authorize further process
review before the product-coverage gate closes.

Batch result: ten validator-oriented collections complete with unresolved
semantics and open divergence status; no implementation task is proposed yet.
These are process-track calibration artifacts, not evidence that product
coverage is complete. The next step is a product-track slice from an unclosed
surface family, followed by a product-coverage report before any ordinary
process-review synthesis or validator task.

## Product-coverage gate turn

The declared nine product-surface families are now all examined. The gate is
closed with `covered_with_gap` status for every family; no family is pending,
blocked, or empty by design. Evidence, source accounting, and the explicit
gap disposition are recorded in
`docs/notes/help-corpus/2026-09-04-product-coverage-gate/`.

The validator-oriented batch remains process-track calibration only. Ordinary
process review may now be considered, but unresolved product vocabulary and
workflow-link gaps remain follow-on candidates rather than silently resolved
decisions.

## Steering pass — 2026-09-04

Reconciled the stale current phase with the existing coverage-gate update and
checked the config handoff against current handler source. The design note now
contains a decision/disposition table and a finite parent completion contract.
Opened `260904-config-help-state-feedback` for the already prioritized config
UX seam. No runtime changes or new corpus review claims were made.

Close this parent when the synthesis table has a disposition for all nine
covered families, three discovery scenarios have recorded outcomes (config,
history inspection, focused capability lookup), and every selected follow-on
has an owner seam and testable acceptance criteria. Deferred gaps need a reason
and reopening trigger, not speculative child tasks. Child implementation need
not be complete for this design parent to close.
