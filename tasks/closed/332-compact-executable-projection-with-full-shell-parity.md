## Goal

Reduce transcript bloat for executable proposals while retaining full shell capability (single-line, multiline, pipes, heredocs).

## Why Now

Structural markers and verbose wrappers can overwhelm flow. We need compact projection defaults without losing expressiveness or correctness.

## Scope

- define compact default projection for executable shell content
- preserve multiline shape by default when multiline is proposed
- keep structured/verbose projection as optional debug mode
- ensure no capability regressions for heredoc/pipe flows

## Intended Behavior

- user-facing transcript remains compact and editable
- executable content retains original shape where practical
- verbose representation remains available for debugging/introspection

## Constraints

- no lossy projection that breaks copy/edit/run ergonomics
- preserve durable event fidelity independently of compact projection

## Done When

- compact projection is default and documented
- multiline, pipes, and heredocs are parity-tested in compact mode
- optional verbose projection remains available

## Progress

- 2026-04-24: First compact-projection slice landed for executable shell proposals.
- Single-shell tool plans now project compactly by default (`$ ...` for single-line commands; raw multiline text for multiline/heredoc forms).
- Non-shell tool plans preserve existing verbatim YAML extract/adopt behavior.
- Verbose/debug path remains available via explicit preview helper option (`render_plan_preview(..., verbose=True)`).
- Added parity tests for compact single-line and multiline shell projection plus shell auto-stage expectations.
- 2026-04-24: Completion slice landed for multi-call shell-plan compact projection and explicit verbose extract mode.
- Compact projection now applies to executable shell-only tool-plan lists (including mixed `shell` + `shell_script`) while mixed/non-shell plans remain YAML.
- `/extract --verbose` now exposes and adopts canonical YAML projection for compactable tool plans.
- Added parity coverage for compact multi-shell projection, mixed-plan YAML fallback, and verbose extract preview/adopt behavior.

## Status

Closed 2026-04-24.
