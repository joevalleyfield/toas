Filed as: 240522-enable-shell-globbing
FKA:
AKA: shell globbing; wildcard expansion; user shell shorthand
Legacy index:

keywords: tooling, investigation, closed, compatibility, shell, transcript

# Enable Shell Globbing

## Current Reality

The user-facing shell globbing pass is landed.

- User-context `$ ...` shell shorthand can reach real shell expansion when the
  original command string is preserved and `needs_shell(...)` routes execution
  through `sh -lc`.
- Assistant-callable plain `shell` remains an argv-oriented tool surface.
- Assistant-callable `shell_script` remains the explicit shell-text lane for
  shell-native behavior such as pipelines and glob expansion.

## Desired Reality

User shell shorthand should support normal shell wildcard expansion in the
intended `$ ...` workflow without requiring the operator to manually work
around missing glob behavior.

## Gap Analysis

- The existing task text conflated user-shell shorthand, assistant `shell`,
  and assistant `shell_script`.
- Task metadata drifted: the filename predates the current `YYMMDD` naming
  scheme and the file status conflicted with its location.

## Known Facts

- `run_user_shell(...)` will execute via `sh -lc` when given a `command`
  string whose content `needs_shell(...)`.
- The implementation work to preserve the original user command string and
  route glob-requiring cases through a real shell is now landed.
- A direct operator repro now succeeds:
  - `$ echo src/*`
  - projects expanded paths rather than a literal `*`.

## Assumptions

- Preserving search continuity for the old task handle matters more than
  pretending it never existed.

## Evidence

- `src/toas/tools_cluster/shell_ops.py`
- `tests/test_tools_shell_ops.py`
- prior task handle: `240522-enable-shell-globbing`

## Decisions

- Rename the task into the current naming scheme.
- Scope this task to the user-facing `$ ...` shell-intent lane rather than to
  every assistant-callable shell surface.
- Treat assistant-callable plain `shell` as intentionally narrower than
  shell-text execution; use `shell_script` when true shell semantics are
  required for assistant-driven execution.
- Record the prior handle in `Filed as:` for continuity.

## Outcome

- [x] User `$ ...` shell shorthand preserves command text well enough to route
  glob-requiring cases through a real shell.
- [x] User-facing wildcard expansion works again for the intended operator
  workflow.
- [x] Task scope is narrowed so assistant plain `shell` semantics are not
  misrepresented as unfinished work under this task.

## Closure

Closed 2026-06-22. The implementation goal that motivated this task was user
shell shorthand globbing, and that path is now substantively working. Any
future changes to assistant-callable shell semantics should be tracked
separately from this user-shell recovery task.
