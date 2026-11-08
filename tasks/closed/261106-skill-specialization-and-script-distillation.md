Filed as: 261106-skill-specialization-and-script-distillation
FKA:
AKA: skill compilation; prompt-to-script distillation; meta-skill specialization; project skill tailoring
Legacy index:

keywords: runtime, skills, distillation, specialization, code-generation, ergonomics, closed

Parent: `261106-standard-agent-skills-integration`
Related: `261106-bounded-step-quiescence`

# Skill Specialization and Script Distillation Pipeline

## Intent

Establish a progression mechanism where generic, high-inference skills (which
rely on fuzzy prompt instructions and reading repository documentation ad hoc)
can be compiled into repository-tailored workspace skills accompanied by
deterministic companion scripts, reducing ongoing token expenditure and
eliminating schema formatting errors for lightweight models.

## Context & Motivation

Generic skills in the ecosystem (e.g. a generic `record-task` or `code-review`
skill) operate primarily through natural-language prompts. To execute in a given
project, they require the agent to:
1. Locate and read repository lore (e.g. `tasks/README.md`, `CONTRIBUTING.md`,
   formatting guides).
2. Spend hundreds to thousands of reasoning tokens computing dates, parsing
   schemas, formatting headers, and formatting tables.
3. Manually reconstruct files or command strings via general-purpose tools.

This "inference tax" is particularly penalizing for lightweight, local, or
obnoxious models (e.g., 7B–14B models or fast flash tiers):
- They burn substantial context and generation time.
- They frequently exhibit cognitive drift, dropping mandatory schema headers
  (e.g., forgetting `Filed as:`, `keywords:`, or relationship links).
- They produce inconsistent output across consecutive turns.

In contrast, once a project's conventions are understood, the mechanical act
of creating a task, running a check, or scaffolding a change can be executed by
a 50-line deterministic Python script in milliseconds with zero thinking tokens
and 100% schema fidelity.

## The Specialization Progression

1. **Stage 1: Generic Explorer (Global / Bundled)**
   - Broad compatibility, zero upfront setup.
   - High token cost: reads repo lore, reasons over formatting on every turn.
2. **Stage 2: Specialization Pass (The Distiller)**
   - An intentional, one-time agent turn (or interactive command) that inspects
     the repository's conventions and extracts the invariant rules into code.
   - Emits:
     - A project-specific `.agents/skills/<name>/SKILL.md` (which shadows the global skill).
     - A deterministic companion script in `.agents/skills/<name>/scripts/` (e.g. `mint_task.py`).
3. **Stage 3: Deterministic Execution (Workspace-Tailored)**
   - Future agent turns (including autonomous `step n` runs) invoke the companion
     script directly via shell.
   - Low token footprint, instant execution, zero formatting hallucinations.

## Architectural Tradeoff & Synthesis

Documented in `docs/notes/2026-11-08-skill-specialization-and-script-distillation.md`:
- Synthesis adopted: **Dynamic Aliasing with Thin Dispatcher and Harness-Enforced Verification Gate**.
- Specialization operates purely in the **Data Plane (Workspace Capabilities)**, emitting artifacts into `.agents/skills/<name>/`.
- The harness enforces strict verification gates (syntax compilation + dry-run execution) before staging.
- The resulting workspace skills cleanly shadow bundled skills in `discover_skills()`.

## In Scope

- Define the specialization workflow and artifact contracts:
  - How generic skills declare their "specialization target" (what information
    they need to extract from a repository).
  - The contract for generated companion scripts (CLI arguments, stdin/stdout,
    exit codes).
- Implement a prototype distillation of `record-task`:
  - Inspects TOAS's own `tasks/README.md`.
  - Generates `.agents/skills/record-task/scripts/mint_task.py` handling
    `YYMMDD` prefixing, continuity fields, keywords, and relationship headers.
  - Generates the shadowing `.agents/skills/record-task/SKILL.md`.
- Evaluate the token economics and reliability differences between:
  - Ad-hoc markdown lore synthesis.
  - Compiled companion script execution.

## Out of Scope

- Fully autonomous background self-modification without operator triggering or review.
- Arbitrary binary compilation (focus strictly on standard scripting languages: Python / Bash).

## Acceptance Criteria

1. [x] **Tradeoff Analysis Documented**: The harness vs. meta-skill trade-off is
   evaluated with a concrete recommendation and prototype in `docs/notes/2026-11-08-skill-specialization-and-script-distillation.md`.
2. [x] **Specialized Artifact Generation**: A specialization run on `record-task`
   produces a functioning workspace skill in `.agents/skills/record-task/`
   with executable Python script `scripts/mint_task.py`.
3. [x] **Verification Before Staging**: Generated scripts are syntax-checked
   (`py_compile`) and dry-run tested before being declared active.
4. [x] **Token & Reliability Benchmark**: The compiled script path demonstrates a
   measurable (>80%) reduction in input/output tokens per task-recording event
   (measured 95.1% reduction from ~3,330 tokens to ~165 tokens, with ~190x latency improvement).

## Outcome & Evidence

- Implemented `src/toas/skills/specialization.py` with `specialize_skill`, `inspect_tasks_conventions`, `distill_record_task`, and `verify_companion_script`.
- Integrated operator API (`skill_specialize`), CLI surface (`toas skill specialize <name>`), and slash commands (`/skill specialize <name>` and `/specialize <name>`).
- Executed `toas skill specialize record-task` creating `.agents/skills/record-task/` containing `SKILL.md` and `scripts/mint_task.py`, verified with syntax and dry-run checks.
- Verified workspace shadowing in `discover_skills()`: `record-task` is recognized as `[workspace]` and shadows `[bundled]`.
- Created comprehensive test suite in `tests/test_skills_specialization.py` and updated `tests/test_skills_cli.py`.
- Documented tradeoff analysis and token economics in `docs/notes/2026-11-08-skill-specialization-and-script-distillation.md`.
