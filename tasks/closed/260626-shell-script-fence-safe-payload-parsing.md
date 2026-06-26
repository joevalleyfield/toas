Filed as: 260626-shell-script-fence-safe-payload-parsing
FKA:
AKA: shell_script triple-backtick heredoc bug; markdown fence safe shell payloads; shell_script fenced yaml here-doc truncation
Legacy index:

keywords: tooling, investigation, historical, correctness, shell, projection, boundaries

Parent: `260614-architecture-follow-through-coordination`
Related: `260626-multiline-user-shell-command-spans`; `510`; `660`

# Shell Script Fence-Safe Payload Parsing

## Current Reality

This investigation started from a report that assistant-turn `shell_script`
here-doc payloads containing normal Markdown triple-backtick YAML fences were
failing while `write_file` preserved the same content.

## Desired Reality

Once a `shell_script` payload is entered, the script body should remain opaque
to generic Markdown fence recognition. A literal payload line of `````,
````yaml`, or similar must not truncate, reshape, or otherwise perturb the
outer tool call unless it exactly matches the actual tool framing contract.

## Gap Analysis

The key question was whether assistant-turn execution still had a fence-local
parsing bug distinct from `write_file`'s structured content path.

## Known Facts

- A direct assistant-turn repro using `shell_script`, `cat <<'EOF'`, a Markdown
  heading, an inner fenced YAML metadata block, and following prose now
  executes successfully on current code when routed around an unrelated
  assistant relative-`cwd` issue.
- The Markdown file written by that repro preserves the triple-backtick YAML
  fence intact.
- The originally suspected fence bug could not be reproduced in the completed
  assistant-turn path we exercised.
- Triage uncovered separate follow-up issues around assistant relative-`cwd`
  handling and multiline `shell_script` allowlist segmentation.

## Assumptions

- The primary defect is in parsing or projection before shell execution.
- A minimal repro should be possible without invoking external tools or broad
  end-to-end setup.

## Unknowns

- If the original reported failure existed, it may have already been fixed by
  earlier multiline/frontier changes before this triage pass.
- A narrower historical streaming or incremental-frontier-only repro may once
  have existed, but it was not reproduced here.

## Investigations

- Reproduced the exact assistant-turn shape as closely as possible:
  `shell_script` + `cat` heredoc + Markdown heading + inner fenced YAML block +
  following prose.
- Confirmed that current code executes that assistant turn successfully and
  writes the expected file content.
- Explored adjacent blocked-command shapes and discovered follow-up issues not
  equivalent to the original report.

## Models

- `write_file`: content is data.
- `shell_script`: payload may currently be treated as both data and framing
  syntax.

## Forecasts

No production fix is justified from this task alone because the originally
reported fence failure did not reproduce on current code.

## Risks

- Over-correcting for a non-reproducing bug would risk regressing currently
  working assistant-turn shell behavior.

## Transformations

- Added and used a targeted assistant-turn repro to confirm current behavior.
- Deferred broader test hardening and production changes in favor of opening
  focused follow-up tasks for the newly discovered real defects.

## Evidence

- User report: `write_file` works with triple backticks; `shell_script` does
  not.
- Nearby historical task: `260626-multiline-user-shell-command-spans`.
- Current repro outcome: assistant-turn fenced-heredoc Markdown file creation
  succeeds on current code when not blocked by the separate relative-`cwd`
  issue.

## Decisions

- Close this investigation without a production fix because the original
  failure could not be reproduced on current code.
- Track the newly discovered assistant relative-`cwd` bug and multiline
  `shell_script` allowlist gap as separate follow-up tasks.

## Open Fronts

- None for this task; follow-up defects were split out.

## Next Actions

- Closed. See follow-up tasks for assistant relative-`cwd` handling and
  multiline `shell_script` allowlist segmentation.

## Outcome

Closed. The original assistant-turn fenced-heredoc failure was not reproducible
on the current tree. A faithful repro using `shell_script`, `cat`, a Markdown
heading, an inner fenced YAML metadata block, and ordinary following prose now
executes successfully and writes the expected file content. Triage did uncover
two distinct follow-up issues: assistant relative-`cwd` resolution does not
appear to honor the step command cwd as expected, and multiline `shell_script`
validation does not appear to enforce allowlist policy across later
newline-separated commands the way a reader might expect.
