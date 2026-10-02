Filed as: 261002-cli-subcommand-help-and-step-usage
FKA:
AKA: step subcommand help; cli subcommand help routing; step flag documentation
Legacy index:

Parent: `260901-help-system-design-survey`
Related: `260912-config-execution-facet-design`; `260905-plain-help-facet-route`; `260926-state-step-requirements`; `260929-state-sequence-inference-affordance`

keywords: cli, help, usability, discoverability, step, execution, documentation

# CLI Subcommand Help Routing And Step Usage Documentation

Status: COMPLETE; implemented centralized subcommand help dispatch across all subcommands, authored structured step usage documentation, removed preview/stdin/control parser conflicts, and verified 100% test and coverage pass.

## Problem Context

`toas step` is the core operator loop of TOAS, driving transcript synchronization,
frontier consequence execution, and LLM inference. Over time, it has accumulated
eight separate flags:
- `--preview-request` (and `--preview`)
- `--preview-response`
- `--stdin`
- `--infer-from <state-label>`
- `--control <slash_command>`
- `--session <transcript_path>`
- `--surface <surface_id>`
- `--async`

However, the command's discoverability has broken down:
1. `toas step --help` and `toas step -h` fail with `unknown option: --help`.
2. `toas help step` and `toas --help step` ignore the target command argument and
   dump the entire 150-line global manual index.
3. The single-line `STEP_USAGE` string has sprawled into an unreadable syntax blob,
   yet gives zero explanation of what each flag does, what preconditions apply
   (e.g. `--infer-from` requiring a typed state transcript), or which flags are
   mutually exclusive (`--preview` with `--control`, `--session` with `--surface`).
4. This disconnect was diagnosed during the September help system survey
   (`docs/notes/help-corpus/2026-09-02-help-cli/slice.yaml`), which noted that
   "The CLI dispatcher defines commands whose names and option forms exceed the
   compact slash CLI topic" and that "Human help needs a link from family selection
   to exact CLI usage." While session-side `/help <topic>` was refactored with
   asset-backed facets, CLI subcommand help was never implemented in the dispatcher.

## Relationship to the Help System Architecture

This work directly connects with the September help triage and design survey:
- **Progressive Disclosure**: Global help (`toas --help`) should remain an orientation
  index; specific command guidance belongs in subcommand-level help (`toas step --help`).
- **Execution Facet Alignment** (`260912-config-execution-facet-design.md`): Stepping
  and frontier authority are operational semantics and invariants, not mutable
  configuration. Documenting `step` must make these invariants explicit: frontier
  intent resolution precedes tool execution, and tool execution precedes model inference.
- **Bi-directional Feedback**:
  - *Informed by the survey*: Employs the survey's question-oriented disclosure
    structure (purpose -> grouped options -> constraints -> examples).
  - *Informing the survey*: Establishes the reusable CLI subcommand help dispatch
    pattern across the dispatcher (`toas <cmd> --help` and `toas help <cmd>`).

## Acceptance Criteria

- [x] Subcommand help dispatch in `cli_dispatch.py`:
  - Support `toas <command> --help` and `toas <command> -h`.
  - Support `toas help <command>` and `toas --help <command>`.
  - Route to specialized subcommand help when registered, falling back cleanly to general command usage or global help where unspecialized.
- [x] Structured `toas step` help text:
  - Explain operational purpose (session synchronization, consequence execution, generation).
  - Categorize flags by operator intent:
    - Input & Ingress: `--session <path>`, `--stdin`, `--control <cmd>`
    - Inspection & preview: `--preview-request`, `--preview-response`
    - Trajectory steering: `--infer-from <state-label>` (state mode only)
    - Deprecated: `--async`, `--surface <id>`
  - Removed artificial parser barrier between preview and stdin/control.
  - Document prerequisites and deprecation notices explicitly.
  - Provide concise, practical workflow examples.
- [x] Legible `STEP_USAGE` and error output:
  - Keep `STEP_USAGE` concise as a clean syntax reference, appending a pointer:
    `Run 'toas step --help' for details and examples.`
- [x] Test Verification:
  - Add unit and acceptance tests covering `toas step --help`, `toas help step`, `toas --help step`, and unknown/general subcommand help dispatch.
  - Maintain 100.00% statement coverage across all modified and covered modules.
  - `./scripts/check.sh` passes 100% clean.

## Progress

- 2026-10-02: Opened task, linked to `260901-help-system-design-survey` and
  `260912-config-execution-facet-design`, and established acceptance criteria.
- 2026-10-02: Implemented centralized subcommand help dispatch in `cli_dispatch.py`
  and `cli_usage.py`, supporting `toas <cmd> --help`, `toas <cmd> -h`, `toas help <cmd>`,
  and `toas --help <cmd>` across all 24 subcommands with fallback to global help.
- 2026-10-02: Authored structured `STEP_HELP` grouping options by true intent (Input &
  Ingress, Inspection & Previews, Trajectory Steering, Deprecated).
- 2026-10-02: Removed artificial restriction in `cli_dispatch_ops.py` preventing preview
  flags from combining with stdin or control.
- 2026-10-02: Verified entire test suite via `./scripts/check.sh` (3,422 unit tests,
  17 acceptance tests, 100.00% statement coverage, clean ruff and mypy).

