# Windows Search Rendering and File Edit Portability

Filed as: 261015-search-rendering-file-edit-portability
FKA:
AKA: drive-letter search results; file edit newline fixtures; safe overwrite bytes
Legacy index:

keywords: tooling, hardening, historical, compatibility, windows, search, coverage

Parent: `261015-windows-compatibility-restoration`

Status: CLOSED 2026-10-15; restore grouped search rendering and portable file-edit tests

## Findings and Changes

- Grouped search rendering used native separators instead of the portable
  workspace-relative paths required by the compact output protocol. Convert
  rendered relative paths with `Path.as_posix()`.
- The match parser partitioned on the first colon, rejecting native drive-letter
  paths and losing grouped output. Recognize `path:line:text` with a numeric
  line delimiter, preserving the drive colon and additional colons in text.
  New drive-path and actual-host absolute-path tests reproduced this red/green.
- Two file-edit tests wrote LF text through native Windows translation but
  expected LF metadata. Write explicit LF bytes; retain existing CRLF-preservation
  tests and assert physical LF output for the range edit.
- Two safe-overwrite tests mocked LF repository bytes while their on-disk
  fixtures contained CRLF. Parameterize matching LF/CRLF byte fixtures for both
  jj and Git. Keep production overwrite safety byte-exact; a new negative test
  verifies that newline-only differences still refuse overwrite and preserve
  the original file.
- Escape a literal native path used in the structure-read error regex.

Seven baseline failures are addressed by this slice. An initial broad three-module
run had 11 failures and 187 passes, including shell execution failures beyond
this slice (environment propagation, executable launch, and shell cwd cases).
Those remain under the master's shell/environment work; do not count this slice
as a green run of the whole tools module.

## Verification

- 110 passes across complete rendering, file-ops, and basic-ops modules plus
  the two original search-rendering regressions, with `-o addopts= -q --tb=short`.
- 74 passes with targeted coverage for `toas.tools_cluster.rendering` and
  `toas.tools_cluster.basic_ops`: 566 statements, **100%**, zero missing files.
- Ruff passes for all four changed Python files.
- Inspected actual `run_search` output using rg in a temporary workspace whose
  native absolute path contains spaces: one inert block, one `src/sample.py`
  heading, two numbered matches, stable block ID. Actual `run_replace_range`
  reported success and retained exact CRLF bytes after replacing the second line.
- Complete suite and POSIX-host execution remain master-task closure gates.
