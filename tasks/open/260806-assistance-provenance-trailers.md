Filed as: 260806-assistance-provenance-trailers
FKA:
AKA: codex provenance; commit assistance trailers; toas transcript provenance
Legacy index:

keywords: docs, governance, inception, provenance, transcript, history

Related: `260626-events-jsonl-multiplicity-and-merge-provenance`; `260804-automatic-hot-journal-rollover`

# Assistance Provenance Trailers

Capture a durable, truthful commit-provenance convention that distinguishes a
Codex task UUID from TOAS's source-qualified event and familiar transcript
references, without inventing a shared global identifier.

## Current Reality

Commit authorship identifies the human repository owner even when an assisted
task substantially shaped the change. Codex tasks have UUIDs, while TOAS has
rotating journals with journal-local node ids and transcript files that are
transitory but commonly retained by the operator.

## Desired Reality

Commits can optionally carry machine-readable trailers that identify the
assisting system and point an investigator to the corresponding durable
conversation/history material. The convention should work across journal
rollover and must not imply that journal-local node ids are globally unique.

## Initial Direction

The parked design note is `docs/notes/2026-08-06-assistance-provenance-trailers.md`.
It records the proposed locator shapes and the questions that must be settled
before automation or enforcement is introduced.

## Evidence To Promote

- a concrete review/recovery workflow that uses the trailers successfully;
- a decision on which tool owns trailer injection and on opt-in/default policy;
- a stable source-qualified TOAS event-reference syntax that survives journal
  rollover; and
- a privacy/retention review for committing transcript references.

