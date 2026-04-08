## Goal

Establish message provenance as a first-class durable fact, capture user corrections as preference signal, and improve the operator's ability to inspect and navigate branching history.

## Why Now

- provenance is high-value signal that degrades if not captured at creation time — user corrections of LLM-generated messages are preference data; the original/correction pair is exactly what matters for training and system revision
- the storage design rationale is now documented in `docs/storage-notes.md`
- `llm_call` attribution is a small change with large downstream value for any inspection or audit use case
- the current branch UX is minimal and accumulates friction as sessions grow

## Scope

Sub-tasks (291 onward):

- **291**: historical replay command — `/replay` for re-executing historical callable messages; the use case `/extract` explicitly shed (task file already written)
- **292**: provenance model foundation — `provenance` inline attribute on message events; sources: `user_authored`, `llm_generated`, `user_correction`, `adopted`; `message_id` on `llm_call` records
- **293**: correction capture — step-time detection of user edits replacing LLM-generated messages; write `provenance.source = user_correction` with `corrects` pointer
- **294**: byte-offset index — fixed-size seekable companion index to `events.jsonl`; enables O(1) access for provenance queries and ancestry walks
- **295**: ancestry inspection — expose lineage walk as a CLI surface; richer `toas heads` output
- **296**: divergence summary — common ancestor computation; `toas diff <head_a> <head_b>`

## Design Notes

See `docs/storage-notes.md` for:
- original implicit-ID design intent and current drift
- byte-offset index design rationale
- provenance model: inline attributes, correction pointer semantics, `llm_call` attribution direction

## Constraints

- provenance is written at creation time; no retroactive assignment
- messages are the primary content store; no content duplication into `llm_call` or provenance records
- the graph is the truth; indices are performance aids, not sources of truth
- sub-tasks should be independently landable
