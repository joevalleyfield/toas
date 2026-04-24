# 438: Vim msysgit path normalization compatibility

## Summary
Fix Windows path normalization in the Vim plugin so msysgit-style Vim environments receive paths they can resolve correctly.

## Problem
Current conversion to Windows-style paths in the Vim plugin breaks file/path handling for Vim running under msysgit environments, where POSIX-like path forms may be required or already expected.

## Goals
- Preserve working path behavior for non-Windows environments.
- Preserve working path behavior for native Windows Vim hosts.
- Make msysgit-hosted Vim path handling reliable for TOAS plugin commands.

## Proposed Direction
- Audit current Vim plugin path normalization points where `C:\...` conversion is forced.
- Detect msysgit-style Vim runtime/host conditions before applying Windows path rewriting.
- Apply conditional or strategy-based normalization so plugin calls use host-compatible paths.
- Add regression tests (or plugin-level fixture checks) covering native Windows vs msysgit path shapes.

## Acceptance Criteria
- Plugin commands that pass file paths work in msysgit Vim without manual path rewriting.
- Existing path behavior remains correct on non-Windows hosts.
- Existing path behavior remains correct on native Windows hosts.
- Automated coverage exists for the msysgit compatibility branch.

## Notes
- Scope is limited to compatibility behavior in the Vim plugin path conversion layer.
- Do not widen scope to broader runtime/path abstraction work in this task.
