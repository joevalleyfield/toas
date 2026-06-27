Filed as: 260627-shell-script-control-word-and-assignment-grants
FKA:
AKA: shell_script builtin grant seam; control-word allowlist parsing; assignment prefix command grant
Legacy index:

keywords: tooling, investigation, active, correctness, shell, policy

Parent: `260614-architecture-follow-through-coordination`
Related: `260626-multiline-shell-script-allowlist-segmentation`

# Shell Script Control-Word And Assignment Grants

## Current Reality

Assistant `shell_script` allowlist validation currently treats the first token
of a logical shell span as the command needing a grant. For shell grammar
shapes like `for`, `if`, `while`, or leading assignment forms such as
`FOO=bar echo hi`, that means validation may look for a grant on the shell
syntax token instead of the actual invoked executable.

## Desired Reality

Allowlist validation should distinguish shell control words and assignment
prefixes from the executable command actually being invoked within each logical
shell span.

## Gap Analysis

The recent newline-boundary fix made command spans more faithful, but the
command-leader extraction inside each span still has a text-first bias rather
than a shell-grammar-aware one.

## Known Facts

- The prior text-based behavior could ask for grants on shell builtins like
  `for` and `if`, and even on assignment prefixes.
- `shell_script_segment_commands()` is the current seam used by assistant
  `shell_script` validation.
- The previous fix intentionally stayed narrow and did not alter how command
  leaders are identified within one logical shell span.

## Risks

- Over-correcting could accidentally stop enforcing grants for genuinely
  unbounded shell entry points.
- Shell grammar is wider than the current helper contract, so the next change
  should stay focused on the specific misleading leading-token cases.

## Next Actions

- Spike the current segmentation behavior for shell control words and
  assignment prefixes to pin down the exact false-positive shapes.
- Add narrow failing tests for the supported follow-on cases.
- Repair command-leader extraction in the smallest seam that keeps current
  bounded-policy intent intact.
