# Executable Grant Policy And Matcher Development

Status: CURRENT  
Applies to: Assistant execution of `shell`, `shell_script`, `python_script`, `powershell_script`, and `interpreter_script`.

---

## 1. Overview

TOAS provides a centralized, post-resolution authorization seam for all assistant-directed code and process execution. Rather than relying on rigid string allowlists or ad-hoc shell parsing, TOAS evaluates resolved executable invocations against an **ordered, prefix-indexed policy of Python matchers**.

### Key Principles

1. **Post-Resolution Authorization**:
   Policy evaluates the actual command line that the runtime resolved to execute (e.g. `['git', 'status']` or `['/usr/bin/python3', '-c', '...']`), not ambiguous pre-expansion transcript text.
2. **Tri-State Decision Model**:
   Matchers return `True` (allow), `False` (deny), or `None` (abstain).
3. **Fail-Closed by Default**:
   If no matcher yields an explicit decision, policy evaluation falls back to the configured `default` (typically `False`).
4. **Authority Separation**:
   Assistant tool calls are subject to policy evaluation; direct user intent execution (e.g. prompt `$ ...` shorthands) deliberately runs under user authority and bypasses assistant policy.
5. **Standard Python**:
   Policies are written in standard Python and run in-process with ordinary language semantics. There is no custom DSL to learn.

---

## 2. Policy Discovery And Export Contract

### File Location

By default, TOAS discovers the workspace policy module at:

```text
.toas/policy.py
```

You may override this location in your project's `toas.toml` (or user config):

```toml
[runtime]
policy_module = "scripts/security_policy.py"
```

If the policy file does not exist, TOAS falls back to the legacy string grant policy defined in `shell.allowed_commands`.

### Export Contracts

A policy module must export one of three supported interfaces:

#### Option A: Explicit `policy` Instance (Recommended)

Export a top-level `policy` (or `POLICY`) instance of `ExecutableGrantPolicy`:

```python
from toas.runtime.executable_grants import ExecutableGrantPolicy
from toas.runtime.matchers import allow_subcommands, deny_flags

policy = ExecutableGrantPolicy(
    default=False,
    prefix_matchers={
        "git": (
            deny_flags("--force", "-f"),
            allow_subcommands("status", "diff", "log", "branch"),
        ),
        "uv": (
            allow_subcommands("run"),
        ),
    },
)
```

#### Option B: Dynamic Factory `get_policy()`

Export a factory function named `get_policy(config=None)` (or `GET_POLICY()`):

```python
from toas.runtime.executable_grants import ExecutableGrantPolicy
from toas.runtime.matchers import allow_all

def get_policy(config=None) -> ExecutableGrantPolicy:
    # Dynamically adjust policy based on workspace config or environment
    return ExecutableGrantPolicy(default=False, prefix_matchers={"ls": (allow_all(),)})
```

#### Option C: Mapping of `prefix_matchers`

Export a dictionary named `prefix_matchers` (or `PREFIX_MATCHERS`) and an optional `default` boolean:

```python
from toas.runtime.matchers import allow_subcommands

default = False

prefix_matchers = {
    "git": (allow_subcommands("status", "diff"),),
    "pytest": (allow_subcommands(),),
}
```

---

## 3. Tri-State Evaluation

When a tool prepares to invoke a command with `argv: Sequence[str]` (where `argv[0]` is the executable prefix):

1. The policy looks up the tuple of matchers registered for `argv[0]`.
2. Matchers are executed in left-to-right order.
3. For each matcher:
   - **`True`**: The invocation is **allowed immediately**. Evaluation stops; source is recorded as `matcher`.
   - **`False`**: The invocation is **denied immediately**. Execution raises an authorization `RuntimeError`; source is recorded as `matcher`.
   - **`None`**: The matcher **abstains**. Evaluation advances to the next matcher.
4. If all matchers abstain (or no matchers are registered for `argv[0]`), the decision falls back to `policy.default`.

---

## 4. Standard Matcher Library (`toas.runtime.matchers`)

TOAS includes a library of composable matchers for common security and operational rules:

### Flag and Option Rules

- **`deny_flags(*flags: str) -> Matcher`**  
  Denies (`False`) if any named flag appears in `argv[1:]`. Inspects exact flags (`--force`), options with assignments (`--network=none`), and short flag bundles (`-rf` matches `-f` or `-r`). Abstains (`None`) if no prohibited flags appear.

### Subcommand Rules

- **`allow_subcommands(*subcommands: str, flag_options_with_args: Sequence[str] | None = None) -> Matcher`**  
  Extracts the first non-flag positional argument after `argv[0]`. If it matches one of `subcommands`, returns `True` (allow); otherwise returns `None` (abstain).
- **`deny_subcommands(*subcommands: str, flag_options_with_args: Sequence[str] | None = None) -> Matcher`**  
  If the extracted subcommand matches one of `subcommands`, returns `False` (deny); otherwise returns `None`.

### Absolute and Pattern Rules

- **`allow_all() -> Matcher`**: Always returns `True`.
- **`deny_all() -> Matcher`**: Always returns `False`.
- **`allow_pattern(pattern: str) -> Matcher`**: Returns `True` if `' '.join(argv)` matches the glob/fnmatch pattern, else `None`.
- **`deny_pattern(pattern: str) -> Matcher`**: Returns `False` if `' '.join(argv)` matches the glob/fnmatch pattern, else `None`.

### Composition Helpers

- **`all_of(*matchers: Matcher) -> Matcher`**  
  Requires all sub-matchers to not deny (`False`). Returns `False` immediately if any sub-matcher denies; returns `True` if at least one allows and none deny; returns `None` if all abstain.
- **`any_of(*matchers: Matcher) -> Matcher`**  
  Returns `True` if any sub-matcher allows; returns `False` if no sub-matcher allows but at least one denies; returns `None` if all abstain.
- **`not_matcher(matcher: Matcher) -> Matcher`**  
  Inverts `True` to `False` and `False` to `True`; preserves `None`.

---

## 5. Authoring Custom Matchers

Any Python callable accepting `Sequence[str]` and returning `bool | None` is a valid matcher:

```python
from collections.abc import Sequence
from pathlib import Path

def require_workspace_path_only(argv: Sequence[str]) -> bool | None:
    """Deny commands referencing paths outside the repository."""
    workspace = Path.cwd().resolve()
    for token in argv[1:]:
        if "/" in token or "\\" in token:
            candidate = Path(token).expanduser()
            resolved = candidate.resolve() if candidate.is_absolute() else (workspace / candidate).resolve()
            if workspace not in resolved.parents and resolved != workspace:
                return False  # Deny out-of-workspace references
    return None  # Abstain, let subsequent matchers decide
```

---

## 6. Comprehensive Example: `.toas/policy.py`

Here is a full production example of a workspace policy:

```python
"""Workspace execution policy for assistant tool calls."""
from __future__ import annotations

from toas.runtime.executable_grants import ExecutableGrantPolicy
from toas.runtime.matchers import (
    all_of,
    allow_all,
    allow_pattern,
    allow_subcommands,
    deny_flags,
    deny_pattern,
    deny_subcommands,
)

policy = ExecutableGrantPolicy(
    default=False,
    prefix_matchers={
        # Safe read inspection tools: allow all
        "ls": (allow_all(),),
        "pwd": (allow_all(),),
        "cat": (allow_all(),),
        "head": (allow_all(),),
        "tail": (allow_all(),),
        "wc": (allow_all(),),
        "rg": (allow_all(),),

        # Git: permit read-only subcommands, strictly forbid destructive flags
        "git": (
            deny_flags("--force", "-f", "--hard", "--delete"),
            deny_subcommands("push", "clean", "reset", "rebase"),
            allow_subcommands("status", "diff", "log", "branch", "show", "rev-parse"),
        ),

        # Package manager: permit test runs without network or upgrades
        "uv": (
            deny_flags("--network", "--upgrade", "-U"),
            allow_subcommands("run"),
        ),
        "pytest": (
            deny_flags("--network"),
            allow_all(),
        ),

        # Shell scripts: forbid interactive or network calls
        "/bin/sh": (
            deny_pattern("*curl*"),
            deny_pattern("*wget*"),
            allow_all(),
        ),
    },
)
```
