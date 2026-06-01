# 569 Frontier Empty Transcript Block Normalization
keywords: projection, hardening, active, correctness, transcript, frontier, parser, normalization

## Summary

Intermittent frontier instability appears when consecutive transcript markers create empty parsed message nodes (for example an empty `## TOAS:USER` block after a projected `## RESULT`).

## Problem

`parse_transcript()` currently emits zero-content blocks when a role marker is followed immediately by another role marker. These empty nodes can become durable candidates in step lineage and perturb frontier role/parent selection.

## Desired Outcome

- Empty transcript role blocks are ignored during parsing.
- Frontier/runtime behavior remains stable across repeated `toas step` invocations after failed tool projections.
- Regression coverage exists for consecutive-marker empty block cases.

## Scope

- `src/toas/transcript.py`
- `tests/test_transcript.py`

## Notes

Repro evidence: repeated `toas step` around assistant shell projection failures can introduce empty `## TOAS:USER` markers and duplicated result behavior at frontier.

## Progress

- runtime tool-result projection no longer injects an empty synthetic `user` prefix before `render_transcript_blocks()` adds the result-owned user-lane marker
- CLI and runtime seam regressions now assert the single-marker shape `## TOAS:USER\n\n## RESULT\n\n...` for callable tool results
