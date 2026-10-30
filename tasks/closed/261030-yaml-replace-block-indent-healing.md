Filed as: 261030-yaml-replace-block-indent-healing
FKA:
AKA: yaml replace_block indent healing; broken yaml recovery; block scalar outdent healing; replace_block pipe indent
Legacy index:

keywords: runtime, extraction, yaml, healing, replace_block, indentation, parsing

Parent:
Depends on:
Blocks:
Blocked by:
Related:

# Broken YAML replace_block Indentation and Outdent Healing

Heal broken YAML tool call candidates in assistant turns where `replace_block`
(and related multiline code operations) suffer from indentation and outdent
errors that cause standard PyYAML parsing to fail.

## Current Reality

1. When models output `replace_block` in YAML fences, they frequently produce
   indentation structures that fail strict PyYAML scanning:
   - Sibling indent: `search_block: |` or `replacement_block: |` followed by code
     at the same indentation column as the key, rather than indented deeper.
   - Child mapping outdent: `- operation: replace_block` at column 0 followed by
     `arguments:` or `path:` also at column 0 instead of indented under the list item.
   - Internal outdent / missing `|N`: A block scalar begins with lines at some indent
     (e.g. column 6), but subsequent lines outdent (e.g. column 4 or column 0 top-level
     functions, decorators, or comments). Without an explicit `|N` indent indicator,
     YAML interprets the first line as the block baseline and crashes on any line that
     outdents relative to that first line.
2. In `extract_frontier_assistant_candidates()` (`src/toas/runtime/frontier_resolution.py`),
   any `yaml.YAMLError` causes callable candidate extraction to skip the block with
   `yaml parse error near ...`.
3. The operator is forced to manually intervene in `session.md` to re-indent the blocks
   or add explicit `|2` indicators before `toas step` will recognize the tool call.

## Desired Reality

1. When `yaml.safe_load(block)` fails on a block that looks callable (e.g. containing
   `replace_block` or `operation:` / `arguments:`), TOAS invokes a structural line-level
   healer before discarding the candidate.
2. The healer inspects and normalizes the line structure:
   - Aligns child mapping keys (`arguments:`, `path:`, `search_block:`, etc.) under
     list items (`- operation:`) or bare mappings.
   - Identifies block scalar boundaries (`search_block:`, `replacement_block:`) using known
     sibling/parent keys as delimiters.
   - Inspects the lines within the scalar block to find the global minimum indentation $m$.
   - Re-indents the block scalar lines so that the shallowest line is indented deeper than
     the parent key (e.g. key indent + 2 or 4), ensuring any internal outdents remain
     strictly deeper than the key line and do not crash PyYAML.
   - Normalizes block scalar headers (`|`, `|-`, `|+`), preserving or adjusting explicit
     indentation indicators as needed.
3. Once healed, the block parses cleanly via PyYAML.
4. Downstream `file_ops.py` indent-inference and shift-matching seamlessly handles any
   uniform leading whitespace when matching against the target file in the workspace.
5. All existing and new tests pass with 100.00% statement coverage via `./scripts/check.sh`.

## Acceptance Criteria

- [x] Sibling-indented `search_block: |` / `replacement_block: |` (where code is at the same indent as the key) heals and parses into a valid `replace_block` candidate.
- [x] Internal outdents within block scalars (where later lines have less indent than earlier lines, including column 0 comments/functions) heal and parse without PyYAML scanner errors.
- [x] Outdented child mapping keys (e.g. `arguments:` at column 0 under `- operation: replace_block`) heal and nest properly.
- [x] Valid, well-formed YAML blocks continue to parse unchanged without alteration.
- [x] Healed candidates extract successfully into executable tool plans in `extract_frontier_assistant_candidates()`.
- [x] Tests cover all identified failure variants and maintain 100.00% statement coverage across changed modules.

## Verification Evidence

1. Targeted coverage on `toas.runtime.yaml_healing` and test suite:
   - `uv run python scripts/targeted_coverage.py --cov toas.runtime.yaml_healing --fail-under 100 --max-missing-files 0 -- tests/test_runtime_yaml_healing.py`: 100.00% statement coverage (94/94 statements).
2. Full mechanical suite check:
   - `./scripts/check.sh`: 3,630 tests passed, 100.00% statement coverage across 157 source files, ruff lint/format clean, mypy clean.
3. Operator-perspective artifact inspection:
   - Verified end-to-end extraction and execution of an outdented, broken YAML assistant turn containing top-level outdented functions and outdented child keys. Successfully extracted candidate tool plan and executed replace_block on target file.
