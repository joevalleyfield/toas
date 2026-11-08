---
name: jj-scratch-workspace
description: Isolated working-copy lifecycle in scratch space for Jujutsu (jj) repos.
alias: scratch
---

# Jujutsu Scratch Workspace Management

This skill enables agents and operators to spin up temporary, isolated Jujutsu
workspaces inside Antigravity and TOAS scratch spaces.

Because Jujutsu stores all commits, operations, and revsets in a centralized
`.jj/repo`, a secondary workspace gives you an independent working copy (`<name>@`)
while preserving full access to the repo's history—without touching the user's
in-progress work in `default@`.

---

## 1. When to Use This Skill

* Whenever working on disruptive refactors, tests, spikes, or isolated tasks.
* Running test suites or builds while uncommitted changes exist in `@`.
* Delegating tasks to subagents that need their own isolated working copy.

---

## 2. Workspace Lifecycle

### A. Location

Scratch workspaces live inside the conversation or session scratch directory:
```
~/.gemini/antigravity/brain/<conversation-id>/scratch/workspaces/<workspace-name>
```
or `/tmp/jj-scratch/<repo>/<workspace-name>`.

### B. Creation (Using Companion Script)

Use the companion script `jj_scratch.py`:

```bash
python3 <path-to-scripts>/jj_scratch.py create <workspace-name> [-r <parent-revision>]
```

* **Parent revision (`-r`)**: Defaults to `@-` (the parent of the current working copy). This ensures the new workspace branches from clean, committed state rather than inadvertently inheriting dirty edits from `@`.

### C. Manual Creation (Direct CLI)

If running `jj` directly:

```bash
jj workspace add "<scratch-path>" --name <name> -r @-
```

---

## 3. Working in the Scratch Workspace

1. **Change Directory (`cd`)**:
   ```bash
   cd /path/to/scratch/workspace
   uv run pytest
   jj describe -m "test: spike implementation"
   ```

2. **Repository Path Flag (`jj -R`)**:
   ```bash
   jj -R /path/to/scratch/workspace status
   jj -R /path/to/scratch/workspace log -r @
   ```

---

## 4. Teardown & Cleanup

Always forget the workspace before concluding:

```bash
python3 <path-to-scripts>/jj_scratch.py forget <workspace-name> --delete
```
Or manually:
```bash
jj workspace forget <workspace-name>
rm -rf "/path/to/scratch/workspace"
```
