Filed as: 260626-multiline-shell-script-allowlist-segmentation
FKA:
AKA: shell_script later command allowlist gap; multiline shell_script python slip
Legacy index:

keywords: tooling, investigation, historical, correctness, shell, policy

Parent: `260614-architecture-follow-through-coordination`
Related: `260626-shell-script-fence-safe-payload-parsing`

# Multiline Shell Script Allowlist Segmentation

## Current Reality

A single multiline assistant `shell_script` can contain an allowed first
command followed by a later newline-separated command such as `python -V`, and
current validation may allow the entire script to run successfully instead of
blocking the later command.

## Desired Reality

If assistant `shell_script` policy is meant to be bounded by allowlisted
commands, validation should account for later command boundaries in multiline
scripts rather than only obvious first-token or operator-delimited cases.

## Known Facts

- A multi-call plan with an allowed `shell_script` followed by a blocked
  `shell` call behaves coherently: the first call runs, the second is blocked,
  and TOAS stages an adopted user continuation.
- A single multiline `shell_script` containing the same heredoc followed by
  `python -V` currently executes successfully and returns Python stdout.
- That behavior suggests later newline-separated commands are not being
  segmented the way a strict allowlist reader would expect.

## Next Actions

- Closed. Next manual priority advances to
  `260627-segmented-event-journal-storage-contract`.

## Progress

- 2026-06-27: Confirmed the bug seam in `shell_script_segment_commands()`: the
  existing `shlex` segmentation treated newlines as ordinary whitespace, so a
  later physical-line command like `python -V` was not seen as a new command
  boundary.
- 2026-06-27: Reworked shell-script segmentation to split scripts into logical
  shell spans first, preserving quoted multiline payloads, backslash
  continuation, and heredoc bodies before extracting command leaders within
  each span.
- 2026-06-27: Added regression coverage for newline-separated blocked
  commands, heredoc/quoted-newline preservation, unterminated-quote parse
  failure, and incomplete logical spans at EOF.

## Decisions

- Treat newline-separated complete shell spans as distinct command boundaries
  for assistant `shell_script` allowlist policy.
- Keep the fix narrow at the command-segmentation seam rather than expanding
  tool-level special cases or changing user-shell semantics.

## Outcome

Closed. Assistant `shell_script` validation now treats later newline-separated
commands as real allowlist boundaries while preserving intended multiline shell
shape such as quoted newlines, backslash continuation, and heredoc bodies.
Focused regression coverage reaches 100% for the touched shell-grant and
shell-script validation seams.
