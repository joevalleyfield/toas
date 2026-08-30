Filed as: 260829-bash-exec-fence-lane
FKA:
AKA: bash exec parser; shell executable fence; executable shell block
Legacy index:

keywords: runtime, implementation, active, correctness, shell, frontier, projection

Parent: `260803-language-exec-fenced-block-lane`
Depends on: `260829-executable-fence-activation`
Related: `260829-ordered-frontier-item-stream`; `260829-action-plan-envelope`

# Bash Executable Fence Lane

Parse active `bash exec`/`sh exec` fences into the existing normalized
`shell_script` capability shape and route them through the current candidate,
authority, execution, and result paths.

## Scope

- parse active Bash-family fences from the shared scanner;
- preserve multiline script bodies and recognize prompted `$ ` lines;
- produce one normalized `shell_script` plan per fence;
- interleave fence plans with existing YAML, shell, and operator candidates;
- preserve user/assistant authority profiles and explicit step boundaries;
- add focused parser, arbitration, and runtime tests.

## Non-Goals

- adding a subprocess runner or new shell policy;
- treating arbitrary `bash` fences as active;
- implementing Python, PowerShell, JSON, or `toas-tool` bodies;
- changing shell staging/recovery semantics;
- bypassing capability validation or durable recording.

## Acceptance

- only explicitly active Bash-family fences become candidates;
- one fence maps to one `shell_script` plan with preserved body semantics;
- fenced shell candidates do not duplicate `$ ` lines inside their body;
- user and assistant fences use existing authority behavior;
- existing YAML/shell/operator tests remain green;
- completion evidence records unsupported language handling.

## Outcome

Implemented the Bash-family executable-fence lane. Active `bash exec` and
`sh exec` fences now produce one normalized `shell_script` plan per fence,
preserving prompted and unprompted multiline bodies. Fence plans participate
in the existing ordered candidate stream, while `$ ` lines inside a fence are
excluded from standalone shell discovery so they cannot duplicate the plan.
Inactive, unsupported, and non-Bash fences remain inert.

Verification: 382 focused tests passed across the executable-fence, arbitration,
scanner, runtime, and step suites; Ruff passed for all changed source and test
files.
