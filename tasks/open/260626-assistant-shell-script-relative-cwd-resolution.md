Filed as: 260626-assistant-shell-script-relative-cwd-resolution
FKA:
AKA: assistant shell_script cwd dot mismatch; assistant callable relative cwd bug
Legacy index:

keywords: runtime, investigation, inception, correctness, shell, boundaries

Parent: `260614-architecture-follow-through-coordination`
Related: `260626-shell-script-fence-safe-payload-parsing`

# Assistant Shell Script Relative Cwd Resolution

## Current Reality

Assistant-turn `shell_script` calls using a relative `cwd` such as `.` appear
to resolve against process workspace state rather than the step command cwd a
caller would expect. In triage this caused a successful-looking repro to write
outside the temporary test workspace unless the tool call used an absolute cwd.

## Desired Reality

Relative assistant tool cwd values should resolve consistently with the step
execution context so `cwd: .` means “the current step command cwd,” not some
other ambient base.

## Known Facts

- A direct assistant-turn `shell_script` repro failed with `tool shell_script
  disallows cwd outside workspace` until routed through `workspace_mode=
  unbounded`.
- After switching to unbounded mode, the same repro succeeded but wrote its
  file outside the temp workspace unless `cwd` was absolute.
- The original fenced-heredoc report proved unrelated once absolute cwd was
  used.

## Next Actions

- Reproduce with a narrow direct test for assistant `shell_script` using
  `cwd: .` and a temp `command_cwd`.
- Determine whether `_workspace_path` is incorrectly anchored to `Path.cwd()`
  rather than the active step command cwd.
- Fix the narrowest boundary that makes assistant relative cwd resolution match
  caller expectations.
