Filed as: 260830-result-following-shell-position-fix
FKA:
AKA: result-command miss; inert-result shell extraction; shell offset mismatch
Legacy index:

keywords: runtime, correctness, active, shell, projection, boundaries, regression

Parent: `260830-exec-grant-policy-matchers`
Related: `260803-language-exec-fenced-block-lane`

# Preserve Source Positions Through Inert Result Filtering

Fix user `$` shell extraction when a command follows a projected inert result
block in the same user turn.

## Observed failure

In `.toas/session-20260830-2101-result-command-miss.md`, `$ find . -name
"README.md"` is correctly recognized by the shell-tail extractor but is then
discarded by intent arbitration. Inert-result stripping produces a position
relative to the filtered text, while fence exclusion compares it with offsets
from the original text. The filtered position falls inside the original result
fence, so the command is treated as fenced content and generation produces an
assistant turn instead of a user/result pair.

## Acceptance criteria

- Extracted shell span positions are explicitly relative to the original
  source content, even when inert regions are removed.
- A user shell command after an inert projected result is selected as a shell
  candidate and executes in user context.
- `$` commands inside active executable fences remain excluded from the user
  shell candidate stream.
- Existing shell extraction, result projection, and multi-command ordering
  behavior remains unchanged.
- A regression test covers the recorded result-following `$ find` shape.
- Targeted coverage, Ruff, and the project check set are recorded.

## Guardrails

- Do not compare offsets from filtered content with offsets from original
  content.
- Keep source-position semantics documented at the extraction boundary.
- Preserve inert-result stripping as an extraction filter; do not make result
  output executable merely to recover following user input.

## Completion evidence

- 2026-08-30: Added `_retained_lines_with_offsets()` so inert-region
  filtering preserves offsets into the original source. Shell span positions
  now remain comparable with original-content Markdown fence offsets.
- 2026-08-30: Added regression coverage for the recorded result-following
  `$ find . -name "README.md"` shape and for candidate arbitration after an
  inert result. Existing inert/nested-fence and shell extraction tests remain
  green.
- 2026-08-30: Focused regression suite passes: 50 tests. Changed shell
  extraction module reaches 100% targeted coverage; Ruff passes. The elevated
  project check was launched after the fix; its known Vim/plugin subprocess
  environment checks are outside this bug’s behavior.
