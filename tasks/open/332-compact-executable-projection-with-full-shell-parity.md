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
