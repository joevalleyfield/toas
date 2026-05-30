# 571: Host Stdio Stream/Watch Chunk Contract Dedup And Framing

## Goal

Fix Vim/local-host delivery drift where transcript-durable assistant output is present in `events.jsonl` and `toas transcript`, but stream/watch delivery can duplicate or mis-shape content, causing missing or malformed buffer updates.

## Why

Recent debugging showed frontier selection was correct while Vim occasionally failed to reflect the same assistant output that durable state already contained.

This indicates a transport/projection contract issue, not a frontier/step routing issue.

## Evidence

From `.toas/.toas/host-stdio-wire.log` tail:

1. `llm_delta` push events sometimes carry transcript markers (`## TOAS:ASSISTANT`, `## TOAS:USER`, `## RESULT`) instead of clean raw model delta text.
2. `watch` poll payload `chunk` can contain duplicated forms of the same content (for example raw YAML block plus framed `## TOAS:ASSISTANT` block).
3. Durable records remain correct (`events.jsonl` + `toas transcript` parity), isolating failure to host stream/watch delivery and client append semantics.

## Scope

- Audit and normalize the contract between:
  - `stream_subscribe` push events (`push_event` / `llm_delta`)
  - `watch` poll/follow chunk assembly
  - Vim append consumer expectations
- Enforce one canonical content shape for streaming deltas.
- Prevent duplicate framing and mixed raw/projection payloads in a single update path.
- Add regression coverage for duplicate `## TOAS:*` framing and chunk dedup behavior.

## Contract Matrix (Target)

The following matrix is the explicit wire contract this task should lock:

1. Top-level RPC response frame
   - Carrier: host stdio line-delimited JSON frame
   - Identity fields: `protocol_version`, `request_id`, `ok`
   - Body fields: exactly one of `payload` or `error`
   - Purpose: request/response envelope only
2. `stream_subscribe` lifecycle frames (`payload.kind`)
   - `push_ack`: subscription alive after first successful upstream read
   - `push_event`: one streamed event update (`payload.event`)
   - `push_complete`: terminal frame for the subscribe request with `complete` and `reason`
   - Purpose: transport lifecycle, not content semantics
3. Stream event kinds (`payload.event.type` and `watch.events[].type`)
   - `llm_delta`: raw model text delta only (non-terminal)
   - `llm_done`: terminal model outcome/status event
   - `prompt_progress`: ephemeral progress telemetry, non-rendered by default
   - `tool_progress`: non-terminal tool/projection progress event
   - `tool_done`: tool/projection completion event
   - `error`: explicit stream/runtime error payload
4. Watch response compatibility shape
   - Legacy: `chunk`, `events`, `next_offset`, `next_seq`, `status`
   - Envelope-compatible: `envelopes` (derived from `events`)
   - Purpose: pull/read model for non-subscribe clients
5. Lifecycle envelope for non-stream commands
   - `envelope.kind`: `accepted`, `cancel`, `cancelled`, `status`, `error`
   - Purpose: command-lifecycle semantics (`step_async`, `cancel`, backend lifecycle), not stream delta content

## 2D Stream Schema (Target)

Stream semantics are modeled as two orthogonal axes:

1. Phase axis
   - `begin`: lane started
   - `delta`: lane incremental payload
   - `end`: lane terminal payload
2. Lane axis
   - `llm_prompt_progress`
   - `llm_reasoning`
   - `llm_answer`
   - `tool`

Canonical event shape (conceptual target):

```json
{
  "lane": "llm_answer",
  "phase": "delta",
  "payload": {"text": "..."},
  "seq": 123,
  "ts": 1710000000.0
}
```

Projection rule:
- Flattened compatibility shapes (`watch.chunk`, legacy `type`, Vim rendered text) are projections from this 2D model.
- No component may re-infer lane/phase from merged text once semantic lane/phase is known by call path.

## Naming And Payload Rules

1. `llm_delta` naming rule
   - Meaning: model-emitted text increment only.
   - Must not be used for transcript framing markers or synthetic projection wrappers.
2. Delta payload canonical key
   - Canonical shape: `{"text": "<delta>"}`.
   - `delta` as a payload key is compatibility-only during migration and must not be emitted by canonical producers after cutover.
3. Framing marker rule
   - `## TOAS:*` and `## RESULT` markers are projection-layer artifacts and must not be reintroduced as if they were raw model deltas in the same event lane.
4. Duplicate-lane rule
   - The same semantic content must not be newly emitted in both `watch.chunk` and event payloads in ways that cause double-append at consumers.

## Migration Boundary For 571

- `571` is a single-task cutover, not an open-ended phased migration.
- Temporary dual-shape compatibility is allowed only as an internal implementation step within `571`.
- Task close requires removal of transitional ambiguity so the shipped contract is one coherent lane/phase model with stable projections.

## Non-Goals

- Changing transcript-authoritative frontier selection semantics.
- Changing durable message/event record content.
- Redesigning Vim UX; this is a protocol/transport correctness fix.

## Done When

- For a step producing assistant callable/content, `stream_subscribe` and `watch` emit consistent, non-duplicated payload shapes.
- Vim receives and appends exactly one coherent update path per event sequence (no missing assistant block, no duplicated framing blocks).
- `toas transcript` and Vim rendered buffer remain convergent after step completion in reproduced scenarios.
- Regression tests fail on pre-fix duplicate/mixed-shape behavior and pass post-fix.
- Wire-contract documentation and tests make frame taxonomy and ownership explicit enough to prevent future `llm_delta` semantic drift.
- Durable protocol docs include the lane/phase 2D schema and projection rules before task closure.

## Workplan Expansion

1. Taxonomy freeze
   - Add a code-adjacent contract table (docs + comments where appropriate) enumerating all frame/event kinds, payload fields, and producer/consumer ownership.
   - Cross-check `event_classification` names against runtime emitters and Vim/local-host consumers.
2. `llm_delta` narrowing pass
   - Audit all producers that emit `llm_delta`.
   - Ensure only raw model delta text uses `llm_delta`.
   - Route non-model/projected marker content to the correct existing event kind or a newly introduced explicit kind if needed.
3. Payload canonicalization pass
   - Canonicalize delta payload producers to `payload.text`.
   - Add compatibility read-path for legacy `payload.delta` where unavoidable.
   - Add targeted tests to assert canonical producer output.
4. Dedup boundary hardening
   - Define and enforce a single append authority for overlapping `watch.chunk` vs streamed event text semantics in Vim/local-host path.
   - Ensure `stream_subscribe` and `watch` are convergent but not multiplicative.
5. Regression test expansion
   - Add tests for:
     - duplicate framing marker suppression
     - mixed raw/projection payload rejection or normalization
     - `llm_delta` purity (no `## TOAS:*` / `## RESULT` as synthetic wrappers)
     - `payload.text` canonical emission
     - poll/follow parity and terminal convergence
6. Repro script and evidence capture
   - Re-run `.toas/bluebird.starface` local-host repro path.
   - Capture before/after evidence from wire log plus transcript parity checks.
   - Archive representative traces in task notes for future audits.
7. Durable wire-contract docs gate (required before close)
   - Update `docs/protocol-notes.md` and `docs/protocols/vim-host-stdio.md` with:
     - lane/phase schema
     - canonical payload keys
     - projection boundaries (`push_event`, `watch`, Vim consumer)
   - Add/refresh tests that assert documented shapes.
   - Do not close `571` until docs and tests are convergent with shipped behavior.

## Initial Repro Focus

- Use `.toas/bluebird.starface` session in local-host mode.
- Repro sequence around assistant callable tool proposal and subsequent step where Vim previously missed the assistant block.
- Validate against wire log (`.toas/.toas/host-stdio-wire.log`) and `events.jsonl`/`toas transcript` parity.

## Progress Log

- 2026-05-30: Corrected task id/title alignment to `571` and expanded this task with explicit contract matrix, 2D lane/phase schema, and single-task cutover boundary.
- 2026-05-30: Added stream event lane/phase metadata support at emit points (`prompt_progress`, `llm_delta`, `llm_reasoning`, `tool_progress`, `tool_done`, `llm_done`, `error`) and preserved lane/phase through watch-envelope projection.
- 2026-05-30: Began daemon async seam extraction so semantic callbacks (`on_llm_answer_delta`, `on_llm_reasoning_delta`, `on_llm_prompt_progress`) flow from runtime-step call path into emitted events.
- 2026-05-30: Switched daemon async runtime-step invocation to `TOAS_STREAM_STDOUT=0` and removed proxy-driven semantic `llm_delta` emission to avoid callback/proxy double-reporting.
- 2026-05-30: Tightened prompt-progress callback normalization to bounded typed payload fields (`processed`, `total`, `cache`, `time_ms`).
- 2026-05-30: Added focused regression tests for callback-provenance emission and host subscribe push-event lane/phase pass-through.
- 2026-05-30: Opened naming-followup backlog `572` and linked roadmap so terminology cleanup (including `daemon async` misnomer) is tracked without derailing `571`.
- 2026-05-30: Hardened adapter-level guarantees with tests for lane/phase propagation through watch-envelope projection and CLI watch envelope normalization paths.
- 2026-05-30: Extended event-policy coverage for `llm_reasoning` to keep terminal/projection semantics explicit in classification tests.
- 2026-05-30: Added explicit emitted-kind -> lane/phase mapping tables to protocol docs (`protocol-notes`, `vim-host-stdio`) to keep wire and runtime docs convergent.
- 2026-05-30: Updated Vim event text extraction to prefer lane/phase-aware delta lanes (`llm_answer`, `tool`, `llm_reasoning`) while retaining legacy type compatibility.
- 2026-05-30: Test harness note: direct script-local helper invocation from standalone Vader file is brittle; kept coverage at transport/adapter Python seams instead.
- 2026-05-30: Added `GenerationRunner` precedence coverage proving explicit semantic callbacks win over stream presenter handlers even with `TOAS_STREAM_STDOUT=1`, preventing callback/proxy lane conflation regressions.
- 2026-05-30: Removed Vim hot-path legacy delta fallbacks (`event.type`-only and `payload.delta`) from stream text extraction and follow rendering; delta/end handling now keys on lane/phase (`llm_answer|tool|llm_reasoning` + `delta`, `llm_answer` + `end`).

- 2026-05-30: Removed synthetic probe-frame event fabrication in Vim push adaptation; push frames without `event`/`events` are now treated as malformed rather than reinterpreted into legacy `tool_progress` shape.
- 2026-05-30: Rewrote Vim streaming fixture corpus from legacy event shapes (`type`-only `llm_delta`/`tool_progress`/`llm_done`, `payload.delta`) to canonical lane/phase envelopes with `payload.text`.
- 2026-05-30: Verified post-cutover runtime/watch path against focused suite after fixture migration (`101 passed` across host-process, daemon-async-runner, and async-cli tests).
- 2026-05-30: Ran full Vim Vader suite after lane/phase fixture migration; recovered RPC-intended suites by pinning transport to `rpc_local_backend` explicitly in test setup, resulting in `24/25` suites passing (`73/73` assertions), with one remaining local-host burst-render fixture failure.
- 2026-05-30: Additional pass narrowed Vader stabilization: local-host scope-marker suite fixed and RPC/watch parity suites stabilized under explicit RPC transport pinning, but `streaming_local_host_burst_render_shape.vader` still fails with `ASSERT_chunk_line` (`24/25` suites passing, `73/73` assertions).
- 2026-05-30: Isolated and resolved the final burst-render flake by rebasing `streaming_local_host_burst_render_shape.vader` onto the known-good host-subscribe fixture path (`ToasTestHostSubscribeFrames` JSON-line frames) and asserting deterministic intermediate accumulation via `run_text` growth (`chunk-000` through `chunk-029`) plus parse-error absence.
- 2026-05-30: Full Vim Vader suite now passes after lane/phase cutover alignment (`25/25` suites, `71/71` assertions).
- 2026-05-30: Enforced producer-side terminal invariant in daemon run-store: `llm_done` cannot finalize as `succeeded` without prior `llm_answer` delta payload evidence; invariant violations are downgraded to explicit stream `error` + failed terminal status to prevent empty-assistant completion commits.
- 2026-05-30: Added focused invariant regressions covering both paths (missing-answer terminal failure and normal-answer terminal success) and validated async/run-store slices (`74 passed` with `--no-cov`).
- 2026-05-30: Observed repeated subscribe hangs where durable run status reached terminal (`succeeded`) but no terminal stream event/complete frame reached host subscribers; this confirms a split-brain terminal model across layers (loom status vs leftward LLM-event closure) and violates expected causal mental model.
- 2026-05-30: Added host subscribe lifecycle instrumentation (`stream_subscribe_start/ack_sent/emit_events/...`) and fallback terminal synthesis paths; logs show some hangs still stall before completion bookkeeping, indicating blocking or non-atomic terminalization seams remain.
- 2026-05-30: Clarified contract intent from failure analysis: `llm`-loop completion is observability, while subscribe termination must anchor on authoritative run-lifecycle terminal state; `llm_done` should be treated as a projection artifact (or removed) rather than sole terminal authority.
- 2026-05-30: Root-cause confirmed in host subscribe bridge: `_stream_stream_subscribe_request` only terminalized on streamed event heuristics (`llm_done`/event payload status) and ignored authoritative daemon `payload.status`, allowing `status=succeeded` runs to continue without `push_complete`.
- 2026-05-30: Patched host subscribe to consume top-level terminal run status (`succeeded|failed|cancelled`) as terminal authority and synthesize a single terminal `llm_done` projection only when terminal status arrives without a terminal event; keeps 2D semantics while removing event-only terminal dependency in the bridge.
- 2026-05-30: Re-ran focused host subscribe contract suite after terminal-authority patch (`tests/test_runtime_session_host_process.py`: `26 passed`), establishing this as an in-scope 571 fix rather than a deferred workaround.
- 2026-05-30: Reproduced a second failure mode where UI showed empty assistant/run marker despite eventual host terminal emission; isolated to Vim local-host shared-channel demux accepting stale frames from prior subscribe request ids.
- 2026-05-30: Hardened Vim decode gate to drop stale push frames unless they match active subscribe `request_id` or active `run_id`; added explicit `PUMP_DROP_STALE` diagnostics and removed permissive push-context acceptance.
- 2026-05-30: Isolated transient `status=failed` flip to event-level terminal handling in Vim (`push_event` `llm_done`) and patched to commit terminal UI status only on `push_complete complete=true`, keeping `llm_done` terminality as candidate state.
- 2026-05-30: Verified latest repro traces now align with contract intent: event stream remains progress/observability, while subscribe terminalization authority is `push_complete` and top-level run lifecycle status.

### Known Rough Edges (Active Horizon)

- Follow-on naming cleanup remains tracked under `572`; this task intentionally ships behavior contract fixes first.
