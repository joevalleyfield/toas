# 676 Transport Equivalence Certification and Shared Adapter Follow-up
keywords: transport, investigation, parked, parity, rpc, stdio-host, certification, adapter

## Goal

Only if and when it becomes worthwhile, push beyond task `669`'s contract-bounding bar toward stronger transport-equivalence proof and possibly a more unified subscribe/watch adapter shape.

## Why

`669` closed at the right bar for current work:
- shared runtime semantics are explicit
- routed daemon/RPC subscribe path no longer blocks parity
- legacy top-level `chunk` behavior is bounded and non-authoritative
- the key cursor/terminality/lane invariants are pinned in focused tests

That is enough to make parity possible without forcing a broader transport abstraction rewrite right now.

There may still be future value in going further if:
- transport-specific drift reappears
- stronger end-to-end certification is needed for confidence
- a single shared subscribe engine becomes simpler than maintaining parallel outer loops

## Scope

- evaluate whether stdio-host subscribe and daemon/watch outer-loop mechanics should converge further
- add stronger end-to-end transport-equivalence fixtures only where they provide real confidence rather than duplicated test noise
- consider a deeper shared subscribe adapter only if it reduces behavioral divergence without dragging result-node/runtime boundary work from `674` into this lane
- keep Vim and CLI consumers on the event-first contract while avoiding new legacy `chunk` dependencies

## Non-Goals

- reopening the already-closed legacy `watch_chunk_projection` bug path from `669`
- broad architecture cleanup for its own sake
- forcing identical transport internals when contract-level parity is already sufficient

## Done When

- we either decide the existing post-`669` state is sufficient and close this task as not needed, or
- we land one of the following with clear value:
  - stronger end-to-end RPC/stdio-host equivalence fixtures for the critical streaming contract
  - a genuinely shared subscribe/watch outer-loop seam that reduces duplicated mechanics without obscuring ownership
- any resulting implementation keeps `chunk` compatibility bounded and preserves event-first semantics

## Notes

- This is intentionally a follow-up, not unfinished `669`.
- If future work starts to look more like runtime/result-node or `step.py` boundary clarification, prefer `674` or `400` instead.
