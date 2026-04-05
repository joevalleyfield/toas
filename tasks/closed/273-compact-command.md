## Goal

Implement a `/compact` command that reduces transcript working size by collapsing verbose RESULT blocks, without touching durable history.

## Why Now

Long sessions accumulate large RESULT blocks (shell output, file reads) that inflate the projected transcript and increase LLM input size. The operator has no mechanical way to trim this today other than manual editing. `/compact` gives a deterministic, inspectable path.

## Scope

- `/compact [--dry-run] [--threshold <n>]`
  - `--dry-run`: report which RESULT blocks would be collapsed and their sizes; no writes
  - `--threshold <n>`: only collapse RESULT blocks whose content exceeds `n` characters (default TBD, suggest 500)
  - without `--dry-run`: rewrite `session.md` with matching RESULT blocks replaced by a single-line summary (`[RESULT: <n> chars, collapsed]` or similar)
- compaction is purely transcript-level: no writes to `events.jsonl`, no new message events, no modification of durable records
- the collapsed form is stable — running `/compact` twice produces the same result as once
- collapsed markers should be recognizable by the parser as non-content (not mistaken for real RESULT blocks in future projections)

## Open Design Questions

- Should collapsed markers be re-expandable (i.e., can the operator get the original content back)? The durable history always has the original, so `rebuild` can restore it — this is probably sufficient.
- Should compaction operate on the raw `session.md` or go through projection? Projection is safer but more complex; raw edit is simpler.
- Should threshold be in characters, lines, or tokens? Characters is simplest and backend-agnostic.

## Intended Inputs

- `session.md` and `events.jsonl`
- RESULT block parsing from `transcript.py`
- operator-command record model

## Intended Outputs

- `/compact` command with dry-run and threshold options
- deterministic, idempotent compaction of verbose RESULT blocks
- `command_request`/`command_result` records written on execution (not dry-run)
- tests covering dry-run reporting, threshold filtering, idempotency, and non-mutation of history

## Constraints

- never writes to `events.jsonl` (transcript-level only)
- must not collapse RESULT blocks that are below the threshold
- collapsed markers must be syntactically inert to the transcript parser
- `rebuild` from durable history should restore the full uncompacted transcript

## Non-Goals

- no LLM-assisted summarization of collapsed content
- no compaction of message content (only RESULT blocks in this pass)
- no automatic triggering of compaction
