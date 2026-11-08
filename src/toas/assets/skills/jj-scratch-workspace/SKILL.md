---
name: jj-scratch-workspace
description: Isolated working-copy lifecycle in scratch space for Jujutsu (jj) repos.
alias: scratch
---
# Jujutsu Scratch Workspace Lifecycle

Use this skill when you need an isolated working-copy in scratch space to run tests, spikes, or experimental refactors without dirtying or advancing the primary working copy (`@`).

## Lifecycle Steps

### 1. Create Isolated Scratch Workspace

```bash
jj workspace add --name <scratch-name> <scratch-path>
```
Example:
```bash
jj workspace add --name spike-workspace /tmp/jj-spike
```

### 2. Operate Within Scratch Workspace

Always run commands and edits within the isolated workspace path:
```bash
cd <scratch-path>
jj status
# Perform edits, run tests, verify assumptions
```

### 3. Verify & Compare

Inspect the diff or status against the parent commit:
```bash
jj diff -r @
```

### 4. Tear Down Workspace

When finished, tear down the scratch workspace:
```bash
jj workspace forget <scratch-name>
rm -rf <scratch-path>
```
