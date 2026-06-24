# Message timestamps and TOAS provenance

Filed as: 260624-message-timestamps-and-toas-provenance
Related: `260624-large-event-graph-render-performance`
keywords: graph, provenance, timestamps, durability, diagnostics

## Goal
Add lightweight writer-era clues to durable history so future debugging can tell whether odd records were produced by current TOAS code or older versions.

## Problem
Large dogfood logs can contain old durable shapes such as duplicate message ids. Without message creation times or a sparse TOAS writer boundary, it is hard to distinguish current bugs from historical artifacts.

## Scope
- Add integer UTC epoch-second timestamps to newly materialized message events.
- Preserve explicitly supplied message timestamps during materialization.
- Add a compact `toas_provenance` record shape with timestamp, writer, schema, and git SHA when available.
- Keep provenance sparse; do not add git metadata to every message event.

## Acceptance
- Newly materialized message events carry integer `timestamp` values.
- Tests can inject a deterministic timestamp clock.
- `toas_provenance` records can mark sparse writer boundaries.
- Missing git SHA is omitted rather than represented as null.

