Filed as: 260628-durable-derived-history-previews
FKA:
AKA: stored history previews; durable derived message summaries; LLM-enriched preview records
Legacy index:

keywords: design, inception, history, preview, storage, records, llm, projection

Parent: `260627-history-surface-user-intent-alignment`
Related: `260628-history-preview-heuristic-selection`; `260627-history-affordances-semantic-restaging`

# Durable Derived History Previews

## Current Reality

The heuristic preview improvement can make common history surfaces noticeably
better without changing storage, but it does not answer the richer question:

```text
if we want much better previews later, where should that derived material live?
```

An LLM-assisted preview path would be expensive and awkward if it had to run on
every read and then be thrown away. If TOAS wants richer operator-facing
previews to become cheap to rediscover and reuse, the result likely needs to be
stored durably as derived history material rather than recomputed ad hoc.

## Desired Reality

TOAS should have a clear design for durable preview material that preserves
message immutability while making richer previews:

- cheap to write when chosen
- cheap to discover
- cheap to retrieve again from later surfaces
- explicit about derivation method and provenance

That design should keep "derived preview" separate from canonical message-event
content and from mutating transcript reconstruction.

## Focus

- decide whether richer previews belong in a new non-message record family or
  as an extension of an existing derived-artifact pattern
- define the minimal stored fields
- define write triggers: manual command, explicit background update, step-time
  generation, or later workflow
- define lookup rules for surfaces that may consume stored preview material
- define invalidation/versioning expectations when prompts/models/heuristics
  change

## Key Questions

- Should durable previews be keyed to source message id, lineage node, or some
  higher-level slice?
- What provenance must be stored: derivation kind (`heuristic`, `llm`), model,
  prompt/version, timestamp, operator intent?
- Which surfaces are allowed to prefer stored preview material over cheap
  first-pass extraction?
- When does stale-but-useful preview material become misleading enough to need
  refresh or visibility markers?

## Exit Evidence

- [x] `docs/notes/2026-07-16-durable-history-preview-contract.md` proposes a
  separate append-only `history_preview` record rather than overloading
  canonical messages or context-shaping lens artifacts.
- [x] Durable State owns the record/query seam; Projection And Rendering owns
  an explicit margin-style reader; Operator Semantics owns explicit authoring.
- [x] The note supplies explicit write, discovery, source-validity, and
  margin-rendering examples.
- [x] The cheap deterministic history-preview heuristic remains the default;
  rich previews are opt-in and do not block it.

## Disposition

The design is complete. No implementation child is opened yet because no
operator-facing history surface has been selected to author and display these
records. Opening storage without that reader would create inert decoration.

Status: Closed (2026-07-16)
