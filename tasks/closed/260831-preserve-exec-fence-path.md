Filed as: 260831-preserve-exec-fence-path
FKA:
AKA: exec fence PATH loss; inherited PATH; fenced runtime environment
Legacy index:

keywords: runtime, shell, exec-fence, environment, path, regression

Parent: `260803-language-exec-fenced-block-lane`
Related: `260621-windows-shell-launcher-and-path-resolution`

# Preserve Inherited PATH In Exec Fences

Runtime executable fences must inherit the caller/runtime environment
faithfully. A fence that receives environment overrides must not replace the
caller environment with only those override keys.

The important observable contract is that an equivalent `echo $PATH`,
`bash -c 'echo $PATH'`, or `cmd /c 'echo %PATH%'` invocation sees essentially
the same search path, subject to shell-specific formatting. Only an explicit
environment-policy `replace` request may remove inherited variables.

## Acceptance criteria

- Partial environment mappings are treated as overrides on the inherited
  process environment at the shared subprocess boundary.
- The inherited `PATH` survives shell and interpreter fence execution.
- Explicit environment-policy replace/merge behavior remains unchanged.
- A regression test proves a small override mapping does not drop `PATH`.

## Status

Closed: 2026-08-31

## Progress

- 2026-08-31: Added the shared subprocess overlay fix and focused regression
  coverage.
