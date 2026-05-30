# 661: Event-Only Subscribe and Lane/Phase Terminality Cleanup

## Goal

Complete the post-571 protocol cleanup by making `stream_subscribe` semantics explicitly event-first in the 2D lattice (`lane`, `phase`) and removing remaining mixed-channel ambiguity.

## Why

Recent streaming failures exposed an unstable compromise:
- daemon/watch could advance `chunk` without advancing semantic events;
- host subscribe could stall or degrade when transport progression and semantic progression diverged;
- mixed raw stdout labeling (`llm_delta` for non-LLM text) obscured true lane ownership.

We landed tactical repairs (chunk projection at host and source-lane cleanup in async runner), but the durable protocol target is still not fully encoded end-to-end.

## Scope

- Define and enforce `stream_subscribe` as event-first transport semantics:
  - push lifecycle remains `push_ack` -> `push_event*` -> `push_complete`
  - `push_event` carries lane/phase-tagged semantic events
  - no dependence on unlabeled text channels for primary semantics
- Keep `watch` compatibility fields (`chunk`, cursors) during transition, but bound them to compatibility adapters rather than primary semantics.
- Make terminality explicitly lane/phase aware:
  - authoritative end events by lane (`llm_answer:end`, `tool:end`)
  - avoid generic completion inference from raw text/cursor behavior
- Tighten sequence/cursor invariants:
  - monotonic seq across emitted subscribe events
  - no duplicate re-emit loops without forward-progress controls
- Update protocol docs and contract tests to reflect the final lattice contract and compatibility boundaries.

## Non-Goals

- Rewriting unrelated daemon/backend lifecycle ownership.
- Large UI redesign in Vim projection beyond lane/phase consumption contract.
- Removing all legacy fields in one shot; compatibility shims may remain temporarily but must be explicitly scoped.

## Done When

- `stream_subscribe` contracts/tests validate event-first behavior with explicit lane/phase events for all streamed deltas.
- Terminal completion behavior is exercised via lane-aware end semantics, not text heuristics.
- Compatibility use of `chunk` is documented as adapter-only and no longer required for primary semantic flow.
- Docs reflect the final 2D protocol lattice and projection rules.

## Notes

- This task intentionally captures the “next layer” after the streaming recovery in 660/571 follow-through.
- Immediate symptom fix is done; this task is about making the model coherent and durable.

## Progress

- 2026-05-30 (slice 1):
  - Host `stream_subscribe` compatibility chunk projection was relabeled from synthetic `llm_delta` to explicit `compat_chunk` (`lane=compat`, `phase=delta`) so adapter-originated transport bytes are no longer represented as primary LLM-lane semantics.
  - Host synthetic terminal fallback projection was relabeled from synthetic `llm_done` to explicit `compat_terminal` (`lane=compat`, `phase=end`) with source tags for adapter-originated terminal completion.
  - Host terminal detection logic was tightened from payload-status heuristics to lane/phase terminal policy via `_is_lane_phase_terminal_event`, requiring explicit `phase=end` on recognized terminal lanes.
  - Host subscribe tests were updated to require explicit lane/phase on terminal semantic events and to assert compatibility terminal event shape for adapter fallback paths.
- 2026-05-30 (slice 2):
  - Protocol docs were updated to codify compatibility projection boundaries: watch `chunk`/adapter terminal fallback are now explicitly represented as `compat_chunk`/`compat_terminal`, not primary semantic lanes.
  - Added host contract coverage asserting watch `chunk` fallback maps to explicit `compat_chunk` with `lane=compat`, `phase=delta`.
- 2026-05-30 (slice 3):
  - Daemon run-store response shaping now applies lane/phase defaults for known event types so terminal events remain lane/phase explicit even when older fixtures omit those fields.
  - Host subscribe cursor progression now enforces monotonic `since_seq` (`max(seen_seq, prev_seq, next_seq)`) to prevent backwards cursor regressions and duplicate re-emit loops from malformed upstream `next_seq`.
  - Added contract coverage for event-only success path (no `compat_*` synthesis when semantic events are complete) and seq monotonic guard behavior.
- 2026-05-30 (slice 4):
  - Host subscribe compat-chunk emission now suppresses only when true LLM semantic deltas are present (`llm_delta`/`llm_reasoning`), eliminating double assistant projection while preserving tool/result incremental compatibility paths.
  - Added targeted host contract coverage: no `compat_chunk` when LLM delta is present; keep `compat_chunk` when only tool-lane stage/result events are present.
- 2026-05-30 (slice 5):
  - Vim `ToasWatch` poll/follow fallback path now prefers lane/phase event text extraction (`s:toas_collect_event_text` over event payloads) and only falls back to raw watch `chunk` when no event text is present, reducing active dependence on unlabeled chunk transport.
  - This aligns manual watch rendering with event-first semantics used by subscribe-driven local-host follow while preserving a bounded compatibility fallback.
- 2026-05-30 (slice 6):
  - Host `stream_subscribe` no longer synthesizes `compat_chunk` from watch `chunk` bytes in normal subscribe flow; push semantics are now event-only for streamed deltas.
  - Removed split compat-chunk gating helper and replaced compat-chunk-focused host tests with event-only assertions (`chunk` ignored both with and without semantic events).
- 2026-05-30 (slice 7):
  - Correlated host and Vim logs showed full multi-step tool output remained in watch `chunk` while event stream carried only sparse tool text lines after compat removal; this caused apparent dropped first-page tool streaming in host-serve flows.
  - Host subscribe now projects non-empty watch `chunk` into a semantic tool-lane delta (`tool_progress` with `payload.source=watch_chunk_projection`) only when no text-bearing delta events are present in the current poll, preserving event-first transport while preventing duplicate text.
  - Added host contract coverage for watch-chunk-to-tool-delta projection and for suppression when semantic text deltas already exist.
