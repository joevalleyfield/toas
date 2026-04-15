## Goal

Make transcript structural sentinels safe in projected content by escaping on projection and unescaping on extraction, so literal content never collides with structural markers.

## Status

Closed (2026-04-15)

## Why Now

Literal `## TOAS:*` strings can appear in docstrings/tool output/assistant content and currently risk being interpreted as transcript structure when rendered into `session.md`.

## Scope

- define a transcript-safe escaping scheme for the closed-set structural role marker lines only:
  - `## TOAS:SYSTEM`
  - `## TOAS:USER`
  - `## TOAS:ASSISTANT`
- apply escaping at projection/render boundaries (tool output, assistant content, any transcript-rendered payload)
- apply unescaping at the inverse boundary before content is given to LLM/tools
- keep escaping as transport-level representation only (never semantic content)
- add tests for round-trip invariants and non-counting behavior in fenced/verbatim regions where applicable

## Intended Behavior

- transcript parser only treats genuine structural markers as structural
- literal sentinel-like content remains intact to LLM/tools after extraction
- users do not need to manually escape/unescape content

## Constraints

- avoid high-complexity parser rewrites in this task
- preserve existing durable history and projection invariants
- do not leak escape artifacts to tool/LLM-facing payloads

## Done When

- projected transcript content cannot accidentally create structural headers via literal text
- extraction path restores canonical content for model/tool consumption
- tests cover projection->extraction round-trip and mixed-content cases

## Completed

- transcript escaping narrowed from broad `## TOAS:*` prefix handling to exact closed-set role markers only
- unescaping similarly narrowed to exact escaped closed-set role markers only
- added tests verifying:
  - closed-set markers are escaped in rendered transcript content
  - non-closed-set markers like `## TOAS:THINKING` are not escaped by this mechanism
  - round-trip render/parse restores canonical content for model/tool-facing paths

## Notes

- `## RESULT` is intentionally out of scope for this task.
