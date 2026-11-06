Filed as: 261106-standard-agent-skills-integration
FKA:
AKA: ecosystem skills support; skill standard; SKILL.md runtime; record task skill; extensible task capture; skill discovery
Legacy index:

keywords: runtime, tooling, skills, ecosystem, standards, capture_task_thread, procedure, active

Related: `261106-bounded-step-quiescence`; `261106-target-coupled-generation-settings`

# Standard Agent Skills Support and Extensible Task Recording

## Intent

Transition TOAS from rigid, built-in procedural mechanisms (specifically
`capture_task_thread` and static YAML `procedure` assets) to the modern de facto
**Agent Skills Standard** (`skills/<name>/SKILL.md` + progressive disclosure +
companion scripts). Ship a curated set of high-utility bundled skills (including
a flexible `record-task` skill) while making ecosystem skill discovery and
activation a first-class TOAS capability.

## Context & Motivation

TOAS currently has two procedural automation mechanisms that feel rigid and
isolated from the broader agent ecosystem:

1. **`capture_task_thread` Tool**:
   Implemented as a hardcoded Python tool in `src/toas/tasks.py`. It forces a
   rigid schema (`title`, `kind`, `evidence`, `blocks_progress`, `scope_hint`,
   `capture_id`) into a fixed template. It cannot adapt to differing repository
   task conventions (such as TOAS's own `tasks/open/YYMMDD-slug.md` format with
   continuity fields, keyword lines, and relationship headers), nor can users
   easily tailor how tasks are captured.

2. **`procedure` Tool**:
   Interpolates static YAML plans (`src/toas/procedures.py`). These lists lack
   instructional depth, progressive disclosure, conditional logic, and alignment
   with modern agent tooling.

Meanwhile, the agent ecosystem has converged on a clear standard for modular
capabilities:
* Directory layout: `skills/<name>/SKILL.md` with YAML frontmatter (`name`, `description`).
* **Progressive Disclosure**: Model prompts only include lightweight skill
  summaries (name and intent). The full runbook is loaded on-demand only when
  activated, conserving token context.
* **Executable Companions**: Optional `scripts/`, `examples/`, and `references/`
  subdirectories allow skills to bundle reusable utilities.

Adopting this standard allows TOAS to seamlessly tap into the growing ecosystem
of shared agent skills (including Antigravity, Claude Code, and team-shared
repo skills) while replacing hardcoded procedural tools with adaptable,
file-backed skills.

## In Scope

### 1. Hierarchical Skill Discovery

Discover skills across standard locations (highest to lowest priority):
1. **Workspace Skills**:
   - `.agents/skills/<name>/SKILL.md`
   - `.gemini/skills/<name>/SKILL.md`
   - `.toas/skills/<name>/SKILL.md`
2. **Global User Skills**:
   - `~/.gemini/antigravity/skills/<name>/SKILL.md`
   - `~/.config/toas/skills/<name>/SKILL.md`
3. **Bundled TOAS Skills**:
   - Packaged assets in `src/toas/assets/skills/<name>/SKILL.md`

### 2. Progressive Disclosure & Activation Runtime

- **Prompt Projection**: At model-input projection time, inject only the catalog
  of available skills (name and description) in a compact, inert block.
- **On-Demand Activation**:
  - Provide a `/skill <name>` transcript slash command and a model-addressable
    `activate_skill(name)` or `skill(name)` tool.
  - When activated, inject the full `SKILL.md` content and register any bundled
    scripts into the executable tool context for that turn.

### 3. Extensible `record-task` Skill

- Implement a standard skill `record-task` replacing the inflexible
  `capture_task_thread` tool.
- Inspects local repository conventions (e.g. `tasks/README.md` or `CONTRIBUTING.md`),
  determines naming conventions (e.g. `YYMMDD-<intent>.md`), formats headers,
  and stages task files without hardcoded field limitations.

### 4. Bundled Core Skills

Ship a small, vetted set of default skills in TOAS:
- `record-task`: Flexible repository task recording.
- `jj-scratch-workspace`: Isolated working-copy lifecycle in scratch space.
- `code-review`: Local diff review and verification guidelines.

### 5. Dynamic Slash Command Aliasing & Operator Surface

- **Dynamic Slash Command Aliasing (Antigravity Parity)**:
  - Discovered skills dynamically register slash command aliases (defaulting to
    `/<skill-name>`, or customized via an optional `alias:` frontmatter field in
    `SKILL.md`).
  - Running `/record-task [args]` or `/code-review` dispatches directly through the
    skill runtime without requiring hardcoded slash command entries in
    `src/toas/step.py`.
- **CLI Commands**:
  - `toas skills [filter]`: List discovered skills, source paths, aliases, and collision status.
  - `toas skill <name>`: Display the full instructions and metadata of a skill.
- **Transcript Session Controls**:
  - `/skills`: List all active skill aliases and summaries.
  - `/skill <name>`: Explicitly activate a skill into the transcript.

## Out of Scope

- Implementing an online package manager or remote skill downloading (git
  submodules, sparse checkouts, or repo check-ins handle distribution).
- Replacing the core model-addressable tool registry (`read_file`, `replace_block`,
  `shell`)—skills orchestrate and provide procedures over tools, rather than
  replacing fundamental primitives.

## Acceptance Criteria

1. **Discovery**: TOAS successfully indexes skills across workspace, user-global,
   and bundled directories with correct precedence overrides.
2. **Progressive Disclosure**: Model prompt token counts increase only by the
   skill summary footprint until a skill is explicitly activated.
3. **Activation**: Activating a skill via `/skill <name>` or model tool call
   injects the full `SKILL.md` body and exposes companion script paths.
4. **`record-task` Flexibility**: The bundled `record-task` skill can record tasks
   conforming to the host repository's schema without hardcoded Python schema
   constraints.
5. **Deprecation Path**: `capture_task_thread` remains functional as a legacy
   facade or redirects gracefully to the skill runtime.
