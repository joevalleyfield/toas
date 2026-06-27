Filed as: 260627-shell-script-control-word-and-assignment-grants
FKA:
AKA: shell_script builtin grant seam; control-word allowlist parsing; assignment prefix command grant
Legacy index:

keywords: tooling, investigation, historical, correctness, shell, policy

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

- Closed. Manual priority remains on the segmented-storage proof chain.

## Progress

- 2026-06-27: Spiked current behavior and confirmed the false positives at the
  command-segmentation seam: `for x in 1; do echo hi; done` produced
  `["for", "do", "done"]`, `if true; then echo hi; fi` produced
  `["if", "then", "fi"]`, and `FOO=bar echo hi` produced `["FOO=bar"]`.
- 2026-06-27: Added narrow regression tests for control-word skipping,
  assignment-prefix skipping, and `shell_script` validation behavior for
  allowed `FOO=bar echo hi` versus blocked `FOO=bar python -V`.
- 2026-06-27: Reworked command-leader extraction to skip shell control words,
  skip leading assignment words, and ignore `for` loop headers until `do`.

## Decisions

- Keep scope focused on misleading shell control words and assignment prefixes
  rather than attempting a full shell grammar parser.
- Continue to treat actual command-position tokens like `true` as command
  leaders unless a later task explicitly revisits shell builtin policy.

## Outcome

Closed. Assistant `shell_script` allowlist validation no longer asks for
grants on `for`, `if`, `then`, `do`, `done`, or leading `NAME=value`
assignment prefixes. It now validates the actual invoked command leaders for
the covered shell shapes, with targeted regression coverage at 100%.
