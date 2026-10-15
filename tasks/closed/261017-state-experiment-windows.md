# Windows State-Execution Experiment Restoration

Filed as: 261017-state-experiment-windows
FKA:
AKA: experiment Bash selection; jj fixture path length; junction containment
Legacy index:

keywords: tooling, hardening, active, compatibility, windows, experiments

Parent: `261015-windows-compatibility-restoration`

Status: CLOSED 2026-10-17; six experiment failures repaired and independently verified

## Evidence and Scope

2026-10-17 reproduction: 6 failed, 19 passed. Bash script execution hardcodes
`/bin/bash`; Windows symlink creation fails with privilege error 1314; four real
jj/CLI tests exceed legacy Windows path lengths when jj appends 128-character
object filenames. Keep real repositories, review-before-execution behavior,
fixture containment, and the independent evaluator intact.

Use explicit configured shell prefixes where provided, otherwise discover a
real Bash runtime. Keep test repository paths short enough for jj on Windows;
report overly long caller output paths clearly. Exercise link containment with
a real directory junction if Windows cannot create a symlink.

Planning review: skimmed roadmap and manual workboard triage for the first
261017 task. Their reproducible-check and narrow evidence-driven priorities still
apply; strategic prose is unchanged. Existing working-copy edits are the related,
verified restoration slices from this chat and remain in place.

## Restoration and Verification

- Replaced hardcoded /bin/bash with configured runtime.shell_runtime or discovered
  Bash. Pin the discovered executable path: Windows subprocess lookup otherwise
  selected the System32 WSL shim despite Git Bash winning PATH discovery.
- Real jj fixtures use short temporary directories. Caller paths that would
  exceed Windows jj object path limits receive an actionable preflight error.
- Containment tests use a real directory junction when Windows rejects symlink
  creation with privilege error 1314; no containment assertion or test is skipped.
- Normalize jj file-list and summary paths in the independent evaluator so native
  separators do not falsely reject valid commit/task boundaries.
- Initial reproduction: six failures, 19 passes. Final Git Bash launched targeted
  run: 27 passes, 394 statements, 100% coverage, zero missing files. Ruff passes.
  The added absolute-executable regression assertion also passes independently.
- Ran the actual module CLI and inspected pair.json: both arms finished, initial
  snapshots and model inputs matched, and every independent evaluator check passed.
- Full suite before the last executable-pinning correction: 3,532 passed,
  32 failed, nine skipped, 17 deselected in 153.77 seconds; 99.97% coverage,
  six missing statements. One experiment failure exposed the Windows executable
  lookup mismatch above and then passed in the final complete focused run.
  Other failures: task capture (one) and Vim harness (30). Do not infer a newer
  full-suite aggregate; static, acceptance, and full-spine gates remain open.