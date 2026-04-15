## Goal

Make transcript structural sentinels safe in projected content by escaping on projection and unescaping on extraction, so literal content never collides with structural markers.

## Why Now

Literal `## TOAS:*` strings can appear in docstrings/tool output/assistant content and currently risk being interpreted as transcript structure when rendered into `session.md`.

## Scope

- define a transcript-safe escaping scheme for structural sentinel lines
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
