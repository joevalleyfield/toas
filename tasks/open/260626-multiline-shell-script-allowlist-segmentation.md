Filed as: 260626-multiline-shell-script-allowlist-segmentation
FKA:
AKA: shell_script later command allowlist gap; multiline shell_script python slip
Legacy index:

keywords: tooling, investigation, inception, correctness, shell, policy

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

- Add a narrow regression test for multiline `shell_script` with a later
  blocked command on a new physical line.
- Decide whether newline-separated later commands should be treated as distinct
  command boundaries for assistant allowlist policy.
- If yes, repair `shell_script` command segmentation in the smallest policy
  seam that preserves existing intentional behavior.
