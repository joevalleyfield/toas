# 510: Fenced import blocks with language/path/provenance shape
keywords: docs, governance, parked, contract, fence, import-blocks, provenance, metadata

Add a first-class transcript projection shape for imported content blocks that is safe, machine-readable, and future-friendly for reload/diff/writeback flows.

## Why

Imported file content currently lacks a consistent fenced-block contract with explicit metadata. We need deterministic structure so downstream tooling can identify origin, file path, language, and identity without brittle parsing.

## In scope

- wrap imported file content in markdown code fences
- infer fence language from filename/extension with override table and fallback to `text`
- include structured path metadata on each imported block
- track provenance metadata (`source=fs`, `source=llm`, etc.)
- dynamically size fences to safely contain embedded backticks
- evaluate and define stable block IDs for graph identity/provenance stitching

## Out of scope

- full writeback/diff tooling implementation
- broad transcript renderer redesign outside imported-block projection

## Acceptance Criteria

- imported content projection consistently emits fenced blocks
- each block includes explicit path metadata and provenance metadata
- language inference uses override table and defaults to `text`
- fence sizing is robust against embedded backticks in payload
- tests cover language inference, fence sizing, and metadata projection shape
- stable ID strategy is either implemented or explicitly specified with follow-on if deferred
