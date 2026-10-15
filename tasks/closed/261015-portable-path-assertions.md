# Portable Path and Physical Offset Assertions

Filed as: 261015-portable-path-assertions
FKA:
AKA: Windows path test portability; CRLF index offsets
Legacy index:

keywords: tooling, hardening, historical, compatibility, windows, graph

Parent: `261015-windows-compatibility-restoration`

Status: CLOSED 2026-10-15; repair eight platform-dependent test failures

## Classification and Changes

The five-module reproduction yielded eight failures and 200 passes on Windows.
No production change was needed for these eight failures:

- Three CLI path tests compared `Path` results with POSIX string spellings.
  Assert exact `Path` equality instead.
- Two async stale-host tests expected `/tmp` instead of the native string
  supplied by their dependency's cwd resolver. Assert the exact resolver value.
- Backend lifecycle writer testing checked a slash-containing substring.
  Assert the exact event path under the request workdir instead.
- A corrupt-source diagnostic test interpolated a native path into regex syntax,
  failing on `\U`. Escape the literal diagnostic with `re.escape`.
- An index offset test wrote text with Windows newline translation but counted
  untranslated LF bytes. Parameterize LF and CRLF byte fixtures, assert the
  exact physical offset, and seek/read the second record to verify usability.

These changes preserve precise path and diagnostic checks; they do not normalize
runtime output or change persisted history. Production `/cd` parsing, shell
behavior, search rendering, file edits, and symlink handling remain separate
master-task work.

## Verification

`uv run pytest tests/test_cli_commands.py tests/test_cli_async_commands.py
tests/test_graph_index_edges.py tests/test_history_scale_models.py
tests/test_model_backend_lifecycle.py -o addopts= -q --tb=short`:
**209 passed** (one extra case from explicit LF/CRLF parameterization).

Ruff passed for all five changed modules. This is a test-only repair; no
user-facing behavior changed. POSIX execution remains part of master-task closure.
