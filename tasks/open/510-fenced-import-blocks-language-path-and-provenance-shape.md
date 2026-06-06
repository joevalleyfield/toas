# 510: Fenced import blocks with language/path/provenance shape
keywords: docs, governance, parked, contract, fence, import-blocks, provenance, metadata

Add a first-class transcript projection shape for imported content blocks that is safe, syntax-highlightable, model-readable, and future-friendly for reload/diff/writeback flows.

## Why

Imported file content currently lacks a consistent fenced-block contract with explicit metadata. We need deterministic structure so the human operator and the model can both identify boundaries, file path, language, and identity without brittle parsing.

The projection should preserve the working illusion that useful artifacts appear in the transcript through the user's agency, regardless of whether the user or model asked for them. Metadata should be just enough to help the model reason confidently about what the user can provide or act on; it should not foreground internal tool-call mechanics.

## Serialization Priorities

- preserve normal Markdown syntax highlighting for the payload language
- keep block metadata attached to the opening fence when practical, using simple parser-compatible info-string attributes
- make imported blocks visibly bounded and hard to confuse with executable transcript intent
- expose path/source/detail enough for hierarchical reasoning and later reload/diff/writeback
- distinguish full files, excerpts, generated/proposed content, and command-derived content without noisy "tool called" narration
- keep the shape simple enough for weaker models and common Markdown parsers

## Candidate Shape

Prefer ordinary language fences. Metadata is optional and should be as quiet as possible:

````text
```python
...
```
````

When path/source context is known, attach it directly to the opening fence:

````text
```python path=src/toas/step.py
...
```
````

For command-derived file content, prefer source language and path when confidence is high:

````text
```python path=src/toas/step.py source="sed -n '1,80p' src/toas/step.py"
...
```
````

When the output cannot be confidently associated with a file/language, fall back to a shell/output-oriented fence while keeping the command as source context:

````text
```shell source="rg -n render_transcript_blocks src tests"
...
```
````

## Model Imitation Note

The model will likely emit a mix of ordinary code fences and locally enriched fences depending on how much TOAS-style projection it has seen in the transcript. That is acceptable. `510` defines the shape TOAS should emit for imported artifacts; later parsing/adoption tooling can use heuristics to tolerate both plain fences and enriched fences when model output imitates this convention.

## In scope

- wrap imported file/content payloads in markdown code fences
- infer fence language from filename/extension with override table and fallback to `text`
- include structured path metadata on each imported block when known
- track subtle source/provenance metadata without namespacing or exposing unnecessary internal tool mechanics
- cover obvious import sources:
  - direct file reads
  - command-derived file output when a single path/language can be confidently inferred
  - search/file excerpts with path and optional line metadata
  - generated/proposed file content when path/language is known
- dynamically size fences to safely contain embedded backticks
- evaluate and define stable block IDs for graph identity/provenance stitching

## Out of scope

- full writeback/diff tooling implementation
- broad transcript renderer redesign outside imported-block projection
- general non-file command output fencing except as fallback shape for ambiguous command-derived imports
- robust parsing/adoption of model-authored plain-vs-enriched fence variants

## Acceptance Criteria

- imported content projection consistently emits fenced blocks
- each block includes explicit path metadata and provenance metadata
- language inference uses override table and defaults to `text`
- serialization preserves ordinary Markdown highlighting for the payload language
- metadata stays attached to the block without making the transcript read like internal tool logs
- fence sizing is robust against embedded backticks in payload
- tests cover language inference, fence sizing, and metadata projection shape
- stable ID strategy is either implemented or explicitly specified with follow-on if deferred

## Progress

- started implementation at the tool-result projection boundary in `tools_cluster.rendering`
- added reusable import-block rendering with language inference, path/source info-string metadata, quoted attribute formatting, and dynamic backtick fence sizing
- changed `read_file` success projection from raw payload text to fenced imported content (`path=... source=workspace`)
- added conservative shell stdout import projection for obvious single-file reads (`cat`, `sed -n`, `head`, `tail`) with command text preserved as `source=...`
- covered helper shape, fence sizing, language inference, direct `read_file`, shell file-output inference, and ambiguous-shell fallback in focused tests

Remaining:

- define whether `search` results should render as one shell/search fence, per-file excerpt fences, or stay line-oriented until richer match structure exists
- cover generated/proposed file content once a concrete producer path is selected
- implement or explicitly defer stable block IDs for graph identity/provenance stitching
