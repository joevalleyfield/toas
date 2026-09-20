Filed as: 260920-transcript-control-state-survey
FKA:
AKA: settings delta survey; transcript control state; branch-forward settings; policy state inventory; settings checkpoint reconnaissance
Legacy index:

keywords: design, survey, transcript, settings, config, precedence, lineage, branching, environment, grants, policy

Parent: `260614-architecture-follow-through-coordination`
Related: `325-config-override-lifecycle-load-save-restore-and-unset`; `310-transcript-env-modifiers-as-execution-surface`; `330-semi-durable-shell-grants-transcript-and-config-lanes`; `260912-config-execution-facet-design`; `260621-windows-shell-launcher-and-path-resolution`; `260620-retire-host-session-path-env-coupling`

# Survey Transcript Control State And Resolution Order

Establish the status quo for all operator-controlled state that can affect a
future TOAS step before proposing a generalized settings-delta or checkpoint
implementation.

The center of this survey is transcript control deltas. Child-process
environment is one transcript-control domain alongside grants and ordinary
configuration; it must not be conflated with environment variables that
control TOAS itself.

## Why Now

TOAS already has several partially overlapping policy and settings surfaces:

- project and global `OperatorConfig` files;
- durable `config_override` records;
- transcript `/config`, `/shell`, `/env`, model, endpoint, and related
  controls;
- lineage-aware grants and process-environment modifiers;
- host/bootstrap environment compatibility inputs;
- runtime, transport, session, surface, and selection state.

Some of these can be serialized to global or workspace files, while others are
meaningful only as transcript/history deltas. The system also contains
intentional source-order exceptions and legacy environment-variable paths.
Concrete checkpoint or inline-fence proposals would be premature until those
facts are assembled into one comparison.

## Confirmed Direction

- Transcript control deltas are the primary policy layer under consideration.
- Deltas are lineage-bound and branch-forward by default.
- An inserted delta should affect the inserted branch and downstream work,
  with same-step downstream visibility where the current config lifecycle
  contract already provides it.
- A full settings block, if retained, is an optional checkpoint/projection;
  it does not replace individual deltas as the canonical history shape.
- Child-process environment belongs in the transcript-control inventory, but
  host environment variables used to control TOAS belong in a distinct domain.
- Scope cuts happen after the broad inventory reveals what would be culled.

## Survey Scope

Inventory every operator-controlled value or operation that can affect a future
step, including at least:

- every `OperatorConfig` field and its file/config-override representation;
- transcript commands and control deltas;
- shell grants and other capability/authority controls;
- child-process environment profiles, `/env` modifiers, and future fence-local
  environment inputs;
- model, endpoint, target, and provider selection;
- extraction, generation, runtime, shell, session, storage, prompt, backend,
  diagnostics, and health controls;
- surface/session bindings, frontier selectors, and other lineage-adjacent
  state;
- secrets and observations as metadata/provenance subjects only, without
  copying secret values into the survey.

The inventory must distinguish these domains rather than assuming one global
precedence ladder:

1. TOAS control-plane environment compatibility inputs;
2. global and workspace configuration files;
3. durable transcript/session overrides;
4. lineage-bound transcript control deltas;
5. child-process environment resolution;
6. runtime, transport, host-lifecycle, and diagnostic state.

## Required Record For Each Control

For every inventoried control, record:

- canonical key/domain and operator-facing command or file surface;
- current owner and implementation locations;
- current durable representation, if any;
- current resolution order and winning-source/provenance behavior;
- same-step timing behavior;
- branch, replay, and lineage behavior;
- whether it serializes to global/workspace files;
- whether it belongs in a future transcript checkpoint;
- environment-variable compatibility status: authoritative, fallback-only,
  legacy, or intentionally exceptional;
- known inconsistencies or unresolved contradictions;
- candidate disposition after survey: retain, unify, migrate, project-only,
  or cull.

## Branch And Checkpoint Questions

The survey must make the following explicit without deciding them prematurely:

- Does the current record resolve from transcript lineage or accidentally from
  storage/history tip?
- Does an inserted delta become visible to later operations in the same step?
- Does it remain active for branch descendants until overridden?
- Which full-state views are authoritative records versus derived checkpoints?
- How are multiple checkpoints validated against intervening deltas?
- Which settings can be exported without pretending that a transcript delta is
  a project/global default?

## Non-Goals

- No implementation of a generalized settings-delta schema in this survey.
- No decision that all settings share one precedence order.
- No assumption that every `TOAS_*` environment variable is user-facing
  configuration; classify those variables first.
- No checkpoint format, inline fence grammar, or migration plan until the
  status quo and cull set are documented.
- No deletion or deprecation of existing controls in this pass.

## Acceptance Evidence

- A durable design note or equivalent survey artifact covers the broad scope
  above and links each claim to implementation, test, or existing design-note
  evidence.
- A per-domain resolution table names source order, timing, durability,
  lineage behavior, and exceptions.
- The survey separately describes TOAS control-plane environment and
  child-process environment semantics.
- Existing precedent is reconciled, including the config precedence contract,
  config override lifecycle, environment-policy modes, shell-grant scopes,
  branch-parent laws, and host-session environment retirement.
- Candidate out-of-scope categories are listed only after the inventory, with
  reasons and any follow-on task needed to preserve the excluded behavior.
- The survey ends with a concrete implementation/decomposition recommendation
  or a clearly stated unresolved decision set.

## Likely Ownership

- Policy and source precedence: `src/toas/runtime/policy.py`, `src/toas/config.py`,
  `src/toas/config_overrides.py`, and `docs/notes/2026-05-09-config-precedence-principles.md`.
- Durable transcript/control records and lineage: `src/toas/graph.py`,
  `src/toas/step.py`, and `src/toas/runtime/step_runtime.py`.
- Grants and child environment: `src/toas/shell_grants.py`,
  `src/toas/runtime/environment_policy.py`, and `src/toas/tools_cluster/`.
- Operator surfaces and provenance: `src/toas/runtime/operator_command_*`,
  config/help assets, and existing config/grant/environment tests.

## Follow-On Actions

The survey work above is complete. Implementation can now be split into
lineage-aware reducers, config round-trip/provenance repair, record-specific
branch-forward deltas, child-environment inspection/inline support, and a
validated checkpoint projection, as described in the durable note.

## Survey Result

Status: Complete (survey; implementation intentionally deferred).

The durable survey is documented in
[`docs/notes/2026-09-20-transcript-control-state-survey.md`](../../docs/notes/2026-09-20-transcript-control-state-survey.md).
It confirms the broad inventory before scope cuts, separates TOAS control-plane
environment from child-process environment, and records the current
history-forward behavior of non-message control reducers. The recommended
implementation order is lineage-aware reducers, complete config round-trip and
provenance, record-specific branch-forward deltas, child-environment inspection
and inline support, then a validated checkpoint projection.
