# 553 Vim Streaming Architecture Shift Cleanup: RPC/Polling -> Session-Host/Stdio/Subscribe

## Goal
Consolidate and clean up planning/narrative artifacts around the broader Vim streaming architecture shift:
- from daemon/RPC/polling-first behavior
- to session-host child process over stdio with subscribe-and-receive push behavior

## Why
"Phase8" was a late experiment slice, not the whole story. The real scope is the architecture transition and its operational/documentation consequences across runtime, Vim transport, tests, and planning artifacts.

## Scope
In scope:
- narrative consolidation across handoffs/tasks/roadmap for the architecture shift
- classification of artifacts/tasks into:
  - OBE (obsolete by events)
  - contributing (still useful historical or technical context)
  - active follow-on (still needed)
  - ready to close
- roadmap and task-state cleanup to reflect current transport reality
- identify where additional comments/context are needed in code/docs for maintainability

Out of scope:
- unrelated roadmap arc reprioritization
- broad task-system redesign

## Terminology Anchor
Use project-native terms consistently in cleanup output:
- session host (child process): `toas host serve`
- transport: stdio framed protocol
- stream behavior: `stream_subscribe` push lifecycle (`push_ack`/`push_event*`/`push_complete`)
- Vim mode: `g:toas_transport_mode='local_host'` default, RPC as opt-back compatibility lane

## Ordered Execution Plan
1. Source inventory + classification:
   - enumerate key sources (tasks, roadmap, `.codex-local` handoffs, critical tests)
   - classify each as OBE / contributing / active follow-on / close-ready
2. Narrative spine document in task updates:
   - write concise architecture-shift narrative that ties threads together:
     - why daemon/RPC/polling was insufficient for UX
     - what session-host/stdio/subscribe changed
     - what failures surfaced (timeout/burst buffering/decode gates)
     - what landed and what remains
3. Task triage updates:
   - update `542`, `552`, and related tasks with explicit status and role
   - mark OBE items clearly rather than leaving stale forward-looking text
4. Roadmap cleanup:
   - align `Now`/`Next`/stabilized sections with the architecture-shift reality
   - remove stale pre-cutover action items
5. Code/doc annotation pass:
   - identify files that need short rationale comments or doc notes to preserve intent
   - add minimal comments where needed
6. Close/reframe decisions:
   - close tasks that are now complete or OBE
   - leave only concrete follow-ons with clear done criteria

## Candidate Artifact Classification (initial)
- `tasks/open/542-vim-primary-surface-local-rpc-parity-matrix.md`: contributing, likely close/reframe after cleanup
- `tasks/open/552-vim-stdio-contract-phase8-callback-push-and-marked-region-rendering.md`: contributing but scope-narrow; needs repositioning under broader architecture shift
- `tasks/closed/551-local-host-push-forwarding-flush-and-vim-default-cutover.md`: close-ready and already closed; key landing marker
- `.codex-local/handoff-2026-05-24-stream-timeout.md`: high-value raw discovery source; not final resting place
- `docs/roadmap.md`: requires consistency cleanup for post-cutover state

## Progress Log
- 2026-05-24: Task opened and retargeted from "phase8 cleanup" to architecture-shift cleanup.
- 2026-05-24: Added explicit OBE/contributing/active/close-ready triage model.

## Done When
- architecture-shift narrative is captured in durable task/docs surfaces
- OBE vs contributing vs active follow-on classification is explicit
- roadmap and task states are consistent with current implementation
- lingering work is represented by a small set of concrete follow-on tasks

## Related
- `525`
- `534`
- `541`
- `542`
- `551`
- `552`
