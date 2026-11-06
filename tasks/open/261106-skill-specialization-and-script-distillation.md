Filed as: 261106-skill-specialization-and-script-distillation
FKA:
AKA: skill compilation; prompt-to-script distillation; meta-skill specialization; project skill tailoring
Legacy index:

keywords: runtime, skills, distillation, specialization, code-generation, ergonomics, active

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
     - A deterministic companion script in `.agents/skills/<name>/scripts/` (e.g. `record_task.py`).
3. **Stage 3: Deterministic Execution (Workspace-Tailored)**
   - Future agent turns (including autonomous `step n` runs) invoke the companion
     script directly via shell.
   - Low token footprint, instant execution, zero formatting hallucinations.

## Key Open Question: Harness Feature vs. Meta-Skill

A primary architectural decision for this task is the ownership boundary of
the specialization pass:

### Option A: Built-in Harness Feature (`toas skill specialize <name>`)
- **Pros**:
  - Direct access to TOAS runtime discovery paths, workspace roots, and
    environment boundaries.
  - Can enforce automated verification gates (e.g. running syntax checks or
    dry-runs on the generated Python script before writing it).
  - Clean CLI operator ergonomics.
- **Cons**:
  - Bakes prompt generation and specialization heuristics into the core Python
    binary/harness.
  - Harder to customize across different LLM backends or unusual project shapes.

### Option B: Ecosystem Meta-Skill (e.g. `skills/skill-specializer/SKILL.md` like `/learn`)
- **Pros**:
  - Fully recursive and self-hosting: uses TOAS's standard skills runtime to
    create and refine skills.
  - Ecosystem-portable: works identically in Antigravity, Claude Code, and TOAS.
  - Can be upgraded, edited, or forked without modifying the TOAS harness.
  - Natural fit for agent conversational reasoning: uses standard `read_file`,
    `write_file`, and `shell` (to test the generated script).
- **Cons**:
  - Relies on the driving model having sufficient code-generation capability
    to write clean Python utilities.
  - Requires standardized knowledge of where project skills reside (`.agents/skills/`).

### Option C: Generalized Skill Aliasing Architecture (Antigravity Parity)
- Rather than implementing special-case harness logic for specialization, **Option C
  generalizes across all skills through a dynamic aliasing and dispatch system**.
- In this model, the harness does not hardcode procedural intelligence for
  `/record-task`, `/specialize`, `/review`, or `/learn`. Instead:
  1. **Dynamic Slash Command Aliasing**: Every discovered skill automatically
     registers a slash command alias (defaulting to `/<skill-name>`, or customized
     via an `alias:` frontmatter field in `SKILL.md`).
  2. **Thin Harness Dispatcher**: When the operator runs a slash command (e.g.
     `/specialize <target-skill>` or `/record-task <intent>`), the harness:
     - Resolves the alias through the skill discovery hierarchy (workspace $\to$ global $\to$ bundled).
     - If the skill has a deterministic companion script, routes arguments directly to the script.
     - If the skill is prose-only, activates the skill runbook into the transcript.
  3. **Self-Hosting Meta-Skill**: The specialization logic itself is simply a standard
     meta-skill (`skills/specialize-skill/SKILL.md`) mapped to the `/specialize` alias.
- **Antigravity Parity**: This mirrors Antigravity's own architecture, where slash
  commands like `/automation`, `/plugin`, `/plan`, and `/learn` are not hardcoded
  engine routines, but lightweight command aliases bound to progressive-disclosure
  skills. In TOAS, this keeps `src/toas/step.py` and `cli_dispatch.py` completely
  thin and generalizable.

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

1. **Tradeoff Analysis Documented**: The harness vs. meta-skill trade-off is
   evaluated with a concrete recommendation and prototype.
2. **Specialized Artifact Generation**: A specialization run on `record-task`
   produces a functioning workspace skill in `.agents/skills/record-task/`
   with an executable Python script.
3. **Verification Before Staging**: Generated scripts are syntax-checked
   (`python3 -m py_compile`) and dry-run tested before being declared active.
4. **Token & Reliability Benchmark**: The compiled script path demonstrates a
   measurable (>80%) reduction in input/output tokens per task-recording event
   compared to reading `tasks/README.md` and writing tasks ad hoc.
