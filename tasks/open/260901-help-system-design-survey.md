Filed as: 260901-help-system-design-survey
FKA:
AKA: help system design; help inventory; help discoverability
Legacy index:

Parent: `260823-projection-discoverability`
Related: `260628-heads-selected-history-leaf-framing`; `260627-history-affordances-semantic-restaging`

keywords: docs, exploration, inception, usability, discoverability, parity, surface

# Help System Design Survey

## Objective

Describe the current TOAS help and discoverability surfaces in design/docs
space, drawing on their existing behavior before proposing implementation
structure.

This task deliberately does not introduce a structured runtime registry,
generated help, or a synchronization mechanism.

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

Lessons and light critique are captured in the slice record. In brief, the
procedure's provenance/completeness gates were useful immediately, but the
worked fixture is slightly too coarse for the first slice: it treats “config
help” as one candidate even though the help topic and the executable command
family already diverge in audience intent, disclosure role, and state effect.
The procedure also leaves the independent-review threshold unspecified; this
run marks itself as self-reviewed rather than implying a stronger review.

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

Lessons and light critique are captured in the slice record. In brief, the
procedure's comparison step usefully separates executable behavior from
conceptual documentation, while the short CLI help under-explains how to
choose among neighboring history projections. The phrase “bounded readable
window” is also less precise than the implementation and capabilities wording,
which identify the underlying message lineage.

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

Lessons and light critique are captured in the slice record. In brief, a
single callable item can have multiple disclosure levels without becoming
multiple item identities. “Core” is an exposure-profile term, not established
priority, and the current direct tool lookup is the clearest description-drift
point because it omits registry metadata already available elsewhere.

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

Lessons and light critique are captured in the slice record. In brief, the
prompt/projection pairing required a third linked item—the slash command—to
explain activation, and the current help grouping under “prompt surfaces”
understates the durable projection effect.

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

Lessons and light critique are captured in the slice record. In brief, the
user-facing transition is more specific than the generic word “projection,”
and the threshold option is exposed without explaining its relationship to
RESULT blocks and durable continuation evidence.

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

Lessons and light critique are captured in the slice record. In brief, prompt
progressive disclosure already has a useful list-versus-render shape, but the
relationship among `/help`, `/prompt`, and projection discovery is implicit;
CLI and slash metadata/navigation contracts also differ without a documented
shared shape.

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

Lessons and light critique across this batch: the history family benefits from
explicit projection roles and navigation targets; “projection,” “view,”
“diagnostic,” and “recovery” currently overlap in user-facing wording. Runtime
ownership, state effect, and non-generation safety are more discriminating
than command grouping. The procedure scales to ten small runs, but the lack of
an executable validator still makes source/candidate/orphan checks manual,
and the repeated five-source ledger is useful ceremony that should eventually
be generated or checked mechanically.

Batch result: ten collections complete with unresolved semantics and open
divergence status; no implementation task is proposed yet. The next bounded
slice should cover replay/extraction surfaces, with explicit separation of
preview, adoption, execution, queue authorization, and malformed-content
salvage.
