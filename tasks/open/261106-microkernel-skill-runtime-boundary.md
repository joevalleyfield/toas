Filed as: 261106-microkernel-skill-runtime-boundary
FKA:
AKA: microkernel runtime boundary; code-only skills; fast-path skills; operator sugar decoupling; skill-backed slash commands
Legacy index:

keywords: runtime, microkernel, architecture, skills, operator-commands, fast-path, policy, active

Parent: `261106-standard-agent-skills-integration`
Related: `261106-skill-specialization-and-script-distillation`; `261106-bounded-step-quiescence`

# Microkernel Runtime Boundary and Fast-Path Code-Only Skills

## Intent

Decouple high-level operator command sugar (e.g. `/model select`, `/config set`,
`/endpoint`, `/prompt`) from the core TOAS execution engine by re-architecting
them as deterministic, fast-path code-only skills that emit structured policy
events, reducing engine complexity and establishing a clean microkernel
architecture.

## Context & Motivation

As detailed in `docs/notes/2026-11-06-microkernel-skill-runtime-boundary.md`, the
TOAS runtime currently hosts thousands of lines of administrative command
formatting and argument parsing in `src/toas/runtime/operator_command_*.py` and
a static table in `src/toas/step.py`.

This architecture introduces substantial bloat into the core engine and creates
an asymmetry between what human operators can do via transcript slash commands
and what models or subagents can execute programmatically.

By establishing a minimal kernel:
- **Kernel Core**: Append-only event store (`events.jsonl`), transcript-to-graph
  synchronization, single-layer consequence stepping (`step_state_once`), LLM
  transport (`llm.py`), and low-level OS tools (`read_file`, `write_file`,
  `replace_block`, `shell`).
- **Userland Skills**: All higher-level workflows, including operator sugar,
  configuration tools, prompt browsers, and task recorders.

When an operator enters `/model select target-id`, instead of routing through a
monolithic function in `operator_command_prompt_workspace.py`, the dynamic skill
aliasing system routes directly to a bundled, fast-path skill (`toas-model`) that
validates arguments and emits a standard `policy_update` result node.

## In Scope

- **Fast-Path Skill Execution Contract**:
  - Define `mode: deterministic` in `SKILL.md` frontmatter for skills that
    execute entirely via companion scripts without requiring an LLM turn.
  - Return structured consequence nodes (result blocks, policy updates, or
    session events) directly to the transcript/graph synchronization loop.
- **Microkernel Boundary Definition**:
  - Audit and define the minimal public API boundary for the TOAS core engine.
  - Remove hardcoded slash command tuples in `src/toas/step.py` in favor of the
    dynamic skill registry dispatch table.
- **Prototype Migration (`/model` as a Skill)**:
  - Implement `toas/assets/skills/toas-model/` with `SKILL.md` (aliased to `/model`)
    and companion script `scripts/model_ctl.py`.
  - Replicate full existing functionality:
    - `/model`: overview of active target and endpoints.
    - `/model targets`: list configured targets.
    - `/model select <target>`: validate and emit `llm.target` policy update.
    - `/model select <endpoint> <model>`: select ad-hoc endpoint model.
- **Backward Compatibility & Parity**:
  - Ensure all existing CLI commands (`toas model select ...`) and transcript
    shorthand (`/model select ...`) produce identical stdout, transcript markers,
    and events.

## Out of Scope

- Removing core storage or graph primitives from Python.
- Migrating basic file-editing primitives (`replace_block`, `read_file`) to
  external skills (these remain foundational kernel primitives).

## Acceptance Criteria

1. **Deterministic Fast-Path Execution**: A skill marked `mode: deterministic`
   executes its companion script and returns result nodes without making an
   LLM call or burning inference tokens.
2. **Dynamic Dispatch Parity**: `/model select <target>` functions identically
   to the legacy implementation, updating active target policy and emitting
   canonical consequence records.
3. **Core Engine Slimming**: `SLASH_COMMANDS` in `src/toas/step.py` delegates to
   the skill registry for all non-kernel commands.
4. **Subagent & Parallel Lane Accessibility**: Subagents operating in isolated
   scratch workspaces can execute `/model select` using standard tool-calling
   mechanisms without specialized host branching.
5. **Full Test Suite Green**: The entire TOAS test suite passes with zero
   regressions on model selection and configuration commands.
