Filed as: 260710-vim-command-transcript-dedup
FKA:
AKA: vim command duplication; full transcript command followup; tool projection tail dedup
Legacy index:

keywords: surface, hardening, historical, correctness, vim, transcript, stream, projection

Parent: `260614-architecture-follow-through-coordination`
Related: `260620-host-stdio-reasoning-terminality-ux`; `260705-host-subscribe-terminal-event-parity`

# Vim Command Transcript Dedup

## Current Reality

The Vim local-host watch path now correctly avoids clipping assistant tool
prelude text when the terminal payload includes projected `## RESULT` content
followed by hallucinated extra turns. That fix exposed a neighboring failure:
some command-execution completions stream provisional tool text first, then
finish with a richer canonical projection that includes extra result markup.

When Vim finalizes success text from the accumulated stream, it can keep both
the provisional streamed tool text and the richer projected tool transcript,
producing a duplicate-looking final render instead of preferring the canonical
projection tail.

## Desired Reality

When a tool run finishes with an embedded canonical projection after provisional
streamed tool text, final success rewrite should prefer the projection tail so
the final render keeps one canonical tool/result view with its richer markup.

## Spike Findings

- this duplication is about tool/result rendering, not assistant-answer
  deduplication
- the provisional streamed tool text and the richer final projection are not
  necessarily byte-identical; the post-stream projection can carry extra
  markup/content that should win
- the underlying smell is not just finalize-time dedup but mixed ownership:
  provisional tool text and canonical projection want separate buffers/state
  even if the final surface ultimately prefers projection
- command execution made the problem visible often on Windows, but the more
  important distinction appears to be stream/render ownership rather than an
  inherently Windows-only semantic fork

## Scope

- prefer canonical tool projection tails over provisional streamed tool text in
  Vim success finalization
- preserve the recent no-clipping behavior for command/result projections
- cover the regression with a Vim-focused finalize helper test

## Exit Evidence

- [x] streamed provisional tool text plus richer projected result markup render
      as one canonical tool/result view in Vim
- [x] projected `## RESULT` content remains visible after success finalization
- [x] existing hallucinated-follow-on protection still passes

## Outcome

Closed on 2026-07-10.

Vim success finalization now prefers the canonical tool/result projection tail
over provisional streamed command text when both arrive in one accumulated
payload. The focused Vim finalize helper regression passes, the neighboring
hallucinated-follow-on protection remains green, and the behavior was confirmed
on Windows against the originally reported manifestation.
