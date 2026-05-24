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
- code-file edits (spawn follow-on implementation task(s) after Step 5 audit)

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
5. Annotation-gap audit (non-code in this task):
   - identify files that need short rationale comments or doc notes to preserve intent
   - spawn follow-on implementation task with exact file/line targets; do not edit code files in `553`
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

## Source Inventory And Classification (Step 1)

| Artifact | Role | Classification | Notes / Action |
| --- | --- | --- | --- |
| `.codex-local/handoff-2026-05-24-stream-timeout.md` | Rich failure/discovery log for burst/timeout behavior | contributing (raw source) | Keep as scratch source only; extract durable conclusions into tasks/docs, do not treat as final resting place |
| `.codex-local/HANDOFF-2026-05-21-vim-local-host-stdio.md` | Early implementation plan + parity intent | contributing (raw source) | Mine for rationale only where not already captured elsewhere |
| `tasks/open/542-vim-primary-surface-local-rpc-parity-matrix.md` | Parity ledger and transition breadcrumbs | contributing -> close/reframe candidate | Contains historical forward-looking text now partially stale after cutover; trim and close or convert to brief parity artifact |
| `tasks/open/552-vim-stdio-contract-phase8-callback-push-and-marked-region-rendering.md` | Late-phase experiment/task narrative | active follow-on candidate | Re-scope language so it is explicitly a contributing slice under architecture shift, not the umbrella story |
| `tasks/closed/551-local-host-push-forwarding-flush-and-vim-default-cutover.md` | Landing marker for flush + default flip | close-ready (already closed) | Keep as concrete completion anchor referenced by roadmap/task narrative |
| `docs/roadmap.md` | Global planning and status surface | active cleanup target | Needs pass for stale pre-cutover next actions and open/closed consistency |
| `docs/capabilities.md` | Current capability contract | active cleanup target | Verify wording reflects local_host default and RPC opt-back semantics clearly |
| `vim/plugin/toas.vim` | Runtime behavior truth for Vim transport | contributing implementation anchor | May need concise rationale comments at transport-mode and subscribe-pump seams |
| `src/toas/runtime/session_host_process.py` | Host stdio subscribe forwarding behavior | contributing implementation anchor | Keep behavior notes aligned with push lifecycle contract |
| `tests/vim/streaming_local_host_*.vader` | Regression and parity evidence | contributing evidence set | Audit for redundancy vs essential invariants; keep minimum comprehensive set |

## Initial OBE Candidates
- Any task text asserting Vim default should remain RPC-first is now OBE after `551`/cutover commit.
- Any roadmap "next" items that prescribe implementing local-host transport adapter/cutover as future work are OBE if already landed.

## Initial Active Follow-On Candidates
- RPC compatibility lane retirement criteria and soak evidence (`541` adjacency).
- Pruning/normalizing Vim local-host streaming tests without losing key regressions.
- Durable narrative consolidation so architecture-shift context is preserved outside `.codex-local` scratch artifacts.

## Progress Log
- 2026-05-24: Step 1 executed: inventory/classification table added with initial OBE/follow-on candidates.

## Architecture-Shift Narrative Spine (Step 2)

### 1) Problem Shape (pre-shift)
Vim streaming UX was constrained by daemon/RPC/polling-era behavior:
- progress visibility depended on poll/follow cadence instead of transport-push immediacy
- async watch paths could appear idle despite backend activity
- operationally, ownership/lifecycle coupling for editor-driven sessions was weaker than desired

This produced user-visible mismatch between "work is happening" and "buffer is updating now," especially during long prompt-processing/token-decode phases.

### 2) Target Shape (shift intent)
The transition objective became:
- editor/session-owned runtime path (`toas host serve` child process)
- stdio framed transport
- subscribe-and-receive stream semantics (`stream_subscribe` with push lifecycle frames)
- Vim consuming pushed events directly for progressive rendering

This reframes poll/follow as compatibility adapters, not primary semantics.

### 3) What Failed During Transition (and why it mattered)
During cutover experiments, several regressions/failure modes surfaced:
- timeout with no first pushed frame despite active backend work
- delayed/burst rendering where frames arrived only after run completion
- decode/pump edge cases (single-line gating, missing ids on push frames) that starved visible updates

These were not cosmetic issues; they directly threatened the core promise of live progress fidelity in Vim.

### 4) What Landed
Key implementation and behavior landings now in place:
- Vim transport default flipped to `g:toas_transport_mode='local_host'` with explicit RPC opt-back lane
- host subscribe path now forwards push frames incrementally (no full-list buffering before write)
- push lifecycle convergence hardened (`push_ack`, `push_event*`, `push_complete`)
- local-host follow/cancel/parity regressions expanded in Vader coverage

Net effect: work-progress and decoded-token visibility now tracks runtime activity in real time in primary Vim flow.

### 5) Current State Classification
- Architecture shift is functionally landed for primary Vim flow.
- RPC path remains compatibility/opt-back lane, not primary default.
- Narrative/planning artifacts still contain mixed-era language that must be triaged for clarity.

### 6) Remaining Work (narrative-driven)
Remaining work should focus on cleanup and governance, not re-implementing cutover:
- remove or mark OBE pre-cutover planning text
- preserve high-value discovery rationale in durable docs/tasks (not scratch-only)
- define explicit RPC-lane retirement/soak criteria (`541` adjacency)
- reduce redundant test artifacts while preserving critical regressions

## Progress Log
- 2026-05-24: Step 2 executed: architecture-shift narrative spine added (problem, target, failures, landings, remaining work).

## Step 3 Triage Execution Notes (2026-05-24)

Task updates applied:
- `542`: marked as contributing parity ledger and close/reframe candidate; updated stale RPC-first language; converted pre-cutover execution sequence to historical/completed framing.
- `552`: reframed as contributing phase slice (not umbrella); tied explicitly to architecture-shift umbrella cleanup in `553`.
- `541`: updated Vim exception rows from RPC-only primary exceptions to compatibility-lane exceptions post-cutover.

Preliminary status calls:
- `542`: likely ready to close after roadmap/doc cleanup pass confirms no remaining open action owned solely by this task.
- `552`: keep open short-term as rationale artifact unless remaining concrete work is removed or moved.
- `541`: remains active as retirement-governance lane for RPC opt-back compatibility.

## Progress Log
- 2026-05-24: Step 3 executed: triage edits applied to `542`, `552`, and `541` to align with post-cutover architecture reality.

## Step 4 Roadmap Cleanup Notes (2026-05-24)

Roadmap updates applied in `docs/roadmap.md`:
- execution-policy arc references updated to emphasize active post-cutover governance lanes (`525`/`541`/`553`)
- added `553` to active open list and marked `542` as contributing close/reframe candidate
- removed stale "next" items that described already-landed Vim local-host adapter/cutover implementation work
- replaced next-step list with post-cutover sequence centered on:
  - architecture-shift cleanup (`553`)
  - RPC compatibility-lane retirement governance (`541`)
  - trimming migration-era stale planning text (`542`/`552`)

## Progress Log
- 2026-05-24: Step 4 executed: roadmap sequencing and active-lane framing updated to post-cutover state.

## Step 5 Annotation-Gap Audit (Non-Code) (2026-05-24)

Audit scope covered:
- `vim/plugin/toas.vim`
- `src/toas/runtime/session_host_process.py`
- `docs/protocols/vim-host-stdio.md`

### Gap Findings (with targets)

1. `vim/plugin/toas.vim:70-72`
- Gap: default transport flip to `local_host` is not accompanied by a durable rationale note tying it to post-cutover architecture policy.
- Suggested annotation intent: explain why local-host is primary default and why RPC remains explicit opt-back.
- Follow-on task target: `554`.

2. `vim/plugin/toas.vim:1871-1884`
- Gap: `s:toas_transport_mode()` fallback behavior (`local_host` on unknown/non-string values) is non-obvious and can be misread as accidental.
- Suggested annotation intent: clarify this is intentional fail-safe toward primary transport and how operators force compatibility mode.
- Follow-on task target: `554`.

3. `vim/plugin/toas.vim:1896-1903`
- Gap: request routing rules are compact but missing a short boundary comment describing which ops stay local-host routed vs RPC-routed and why.
- Suggested annotation intent: preserve routing contract for future maintenance.
- Follow-on task target: `554`.

4. `vim/plugin/toas.vim:2026-2084`
- Gap: `s:toas_local_host_subscribe_frames()` currently blocks and accumulates a frame list; this helper is now a compatibility bridge while primary progressive behavior is callback/pump-driven elsewhere.
- Suggested annotation intent: mark this helper as compatibility path and point maintainers to primary push-follow path.
- Follow-on task target: `554`.

5. `vim/plugin/toas.vim:2290-2338`
- Gap: follow-watch prefers subscribe frames then falls back to poll/watch on certain failures, but fallback rationale is only partially documented in catch block.
- Suggested annotation intent: make fallback policy explicit (resilience over strict path purity) and list accepted fallback-trigger classes.
- Follow-on task target: `554`.

6. `src/toas/runtime/session_host_process.py:223-243`
- Gap: dual behavior in `_handle_stdio_json_request_line()` (streaming callback emission vs list-return compatibility) is critical but not explained at boundary.
- Suggested annotation intent: explicitly document why streaming path is used in serve loop and list-return path retained for tests/back-compat consumers.
- Follow-on task target: `554`.

7. `src/toas/runtime/session_host_process.py:257-355`
- Gap: `_stream_stream_subscribe_request()` encodes nuanced semantics (defer `push_ack` until first successful upstream read; emit single error frame on immediate reject; include `push_complete.reason`).
- Suggested annotation intent: codify these protocol decisions inline to prevent accidental regression.
- Follow-on task target: `554`.

8. `docs/protocols/vim-host-stdio.md` (new subsection needed)
- Gap: protocol doc states flush/order principles but does not explicitly call out `stream_subscribe` lifecycle frame sequence and immediate-forwarding expectation that resolved burst buffering.
- Suggested annotation intent: add concise normative subsection for `push_ack`/`push_event*`/`push_complete` lifecycle and immediate per-frame flush requirement in subscribe context.
- Follow-on task target: `554`.

### No-Change Confirmations
- No functional code changes were made in Step 5.
- Step 5 output is audit findings only, consistent with `553` scope correction.

## Progress Log
- 2026-05-24: Step 5 executed as audit-only; annotation implementation deferred to follow-on task `554` with explicit file/line targets.

## Step 6 Close/Reframe Decisions (2026-05-24)

Decisions executed:
1. Close `542`:
   - moved to `tasks/closed/542-vim-primary-surface-local-rpc-parity-matrix.md`
   - rationale: objective is materially landed; task now serves historical/contributing parity ledger role rather than active implementation scope.

2. Close `552`:
   - moved to `tasks/closed/552-vim-stdio-contract-phase8-callback-push-and-marked-region-rendering.md`
   - rationale: scope is contributing phase-slice rationale; no remaining standalone implementation obligations in this task.

3. Keep active follow-ons:
   - `541`: RPC compatibility-lane retirement governance
   - `553`: architecture-shift narrative + planning hygiene consolidation
   - `554`: annotation implementation follow-on from Step 5 audit

Roadmap stitching applied:
- removed `542` from active open list
- added closed-item blurbs for `542` and `552`
- adjusted next-step wording to treat `542`/`552` as closed historical artifacts

## Progress Log
- 2026-05-24: Step 6 executed: `542` and `552` closed; remaining active follow-ons narrowed to `541`/`553`/`554`.
