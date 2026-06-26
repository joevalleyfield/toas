Filed as: 260626-multiline-user-shell-command-spans
FKA:
AKA: multiline shell shorthand; quoted dollar-tail commands; heredoc user shell spans
Legacy index:

keywords: runtime, implementation, historical, correctness, transcript, frontier, shell

Parent: `260614-architecture-follow-through-coordination`
Related: `260530-shell-lane-spawn-semantics`; `260621-enable-shell-globbing`

# Multiline User Shell Command Spans

## Current Reality

User-turn shell shorthand currently treats a trailing `$ ...` command as a
single physical line. Valid shell commands that continue through multiline
quotes, trailing backslashes, or heredoc bodies are cut early and either lose
payload or fail extraction entirely.

## Desired Reality

TOAS recognizes a user-turn shell shorthand command as one logical shell span.
Once a line begins with `$ `, following physical lines remain part of the same
command until the shell text is syntactically complete for the bounded cases we
support.

## First Increment

Land a conservative span scanner that preserves exact embedded newlines for:

- open single-quoted strings
- open double-quoted strings
- trailing unescaped backslash continuation
- heredoc bodies

Do not split on blank lines while continuation state is active.

## Constraints

- preserve command text byte-for-byte after the prompt marker, including
  embedded newlines
- emit exactly one shell consequence for one logical `$` command span
- stop before following prose once the shell command is complete
- keep the first pass conservative rather than implementing full shell grammar

## Exit Evidence

- quoted multiline `$ ...` commands extract as one command string
- backslash continuations and heredocs extract as one command string
- plain prose after a completed command is not absorbed into the shell span
- graph-level extraction produces one `shell` call whose `command` field matches
  the authored multiline text

## Outcome

Closed. User-turn shell shorthand now preserves logical multiline command spans
across quoted payloads, backslash continuations, and heredoc bodies, while
keeping incomplete spans non-executable. Intent arbitration and graph-level
shell extraction were aligned to the same span model, inert fenced regions were
hardened against nested-fence leakage, and host-stdio tests now seed
`PYTHONPATH` explicitly when spawning `python -m toas` from temporary
workspaces.
