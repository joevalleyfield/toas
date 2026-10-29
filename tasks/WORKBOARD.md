# TOAS Workboard

> **Status:** Active Development
> **Last Sync:** 2026-10-29

## 0. Manual Triage

### Current read — 2026-10-20

The 46 open tasks are an inventory of implementation, requirements, research,
and deferred work. They are not 46 ready jobs. Several broad parents contain
landed slices and need a remaining-gap audit before further implementation.
The full inventory and review evidence are recorded in
[open-set review](closed/261020-open-set-workboard-review.md).

The present product pressure is making local-model operation dependable:
state-mode request/response quality, visible branch-local policy, faithful
execution/recovery, and practical editor/platform behavior. Architecture and
durable-history invariants constrain that work. The segmented-storage and
corruption-refusal proof chain is complete enough to stop driving the queue.

### Where the open set stands

| Theme | Open | Current disposition |
| --- | ---: | --- |
| State-mode operation | 5 | Alpha exists. Request-composition/resilience has concrete experiments; artifact capture and failure memory need bounded design choices. |
| Policy, authority, and explicit objectives | 5 | Branch reducers and grant machinery largely exist. Provenance inspection and one-shot control ingress have explicit remaining seams; audit broad parents before extending them. |
| Execution ingress and source fidelity | 6 | Native/text ingress, language fences, source references, retry adapters, materialization, and extraction boundaries have mixed landed and prospective scope. |
| Platform and patch behavior | 5 | Native Windows and macOS checks have recorded green baselines. MSYS Vim works for the operator; historical harness failure and current gVim status require separate evidence. Patch research remains parked. |
| Operator projections and provenance | 6 | Discovery, turn IDs, highlighting, focus/map projections, and assistance trailers are mostly design or partial-probe work. |
| Architecture, history, and stream observation | 7 | Coordination and research homes; no new storage or corruption project is implied. Telemetry and stderr separation need a concrete consumer or reproduction. |
| Release operation | 2 | Existing recurring release process plus conditional helper ergonomics; not missing release infrastructure. |
| Parked performance, orchestration, and planning experiments | 10 | Preserve as options. Age and stale markers alone do not promote them. |

### Practical sequence

1. **Audit remaining scope before adding code.** Grant matchers, retry
   materialization, ingress/fence parents, and the state alpha parent describe
   substantial landed work. Compare acceptance criteria with current artifacts;
   close satisfied scope or name the exact remaining gap. Do not mistake a
   historical progress paragraph for a fresh defect.
2. **Choose a concrete operator-facing slice.** The clearest documented fronts
   are `261010-state-inference-response-resilience` (selectable request
   composition; configuration/history policy still needs agreement),
   `260920-effective-policy-provenance-inspection` (projection exists;
   domain reduction/rendering remain), and
   `260920-one-shot-control-ingress-disposition` (caller inventory before
   changing the ingress contract). This is a candidate list, not three
   simultaneous implementation commitments.
3. **Handle platform reports through current reproductions.** Reconcile the
   old launcher task and mixed-runtime harness evidence with the completed
   Windows restoration slices and operator reports. Retest gVim before
   diagnosing it; Linux parity remains unmeasured in this session.
4. **Keep larger capability research conditional.** Transcript parallelism,
   merged-history provenance, alternative frontends, inferred focus, and
   workboard automation should produce one bounded consumer/contract before
   becoming implementation programs.

The September operator vote still supplies useful values: explicit authority,
compact config feedback, and source-preserving recovery. Config-help work and
several fidelity fixes are closed. The August native-ingress/fence ordering is
historical context: executable lanes and `json exec` already have landed slices.
Neither dated vote is a literal current queue.

### Working boundaries

- Direct user execution and assistant capability policy remain distinct.
- Branch-local policy and append-only history remain authoritative; transport
  and editor adapters preserve their meaning.
- Parallelism research remains open, but session/surface identity is already
  implemented and its duplicate task is closed. It is not the next missing
  prerequisite.
- Use `260614-architecture-follow-through-coordination` as the architecture
  reference, `260920-branch-projected-policy-program` for policy decomposition,
  and `260926-state-step-requirements` for state-mode requirements. Their
  existence does not authorize broad refactoring or reopen completed children.
- Release review is recurring operation. Add helpers when a manual review
  exposes repetitive friction, and keep the check gate in `docs/checks.md`.

### Relationship Roots

*Open coordination/requirements homes; inclusion is not execution priority.*

<!-- WORKBOARD:RELATIONSHIP_ROOTS:START -->
- `260926-state-step-requirements`
- `260920-branch-projected-policy-program`
- `260803-tool-intent-ingress-separation`
- `260803-language-exec-fenced-block-lane`
- `260614-architecture-follow-through-coordination`
- `260627-release-process-and-weekly-release-lane`
<!-- WORKBOARD:RELATIONSHIP_ROOTS:END -->

### Active Arc Map

*Generated first-mention relationship tree; repeated tasks use `@task-id`.*

<!-- WORKBOARD:RELATIONSHIP_TREE:START -->
- 260926-state-step-requirements Develop a reviewable implementation contract for an explicitly state-shaped working surface handled by a state-step operation integrated with TOAS run... (depends on `260926-state-simulation-checkpoint`; related `260926-state-step-contract-spike`, `260926-state-experiment-harness`, `260926-state-experiment-plan-tools`, `260803-session-rotation-lifecycle`, `260927-state-step-history-projections`, `260928-state-user-control-turn-lifecycle`, `261002-state-transcript-branching-and-modification`, `261010-state-inference-response-resilience`, `261010-state-result-history-sideslip`)
  - 261010-direct-tool-artifact-capture Status: OPEN; allow tool calls to declare an artifact label and auto-populate state upon execution (related `261009-explicit-reference-expansion-and-report-projection`, `261010-scratch-read-file-ingestion-threshold`)
  - 261010-rolling-tool-failure-memory Status: OPEN; maintain a compact rolling log of recent tool attempts and failures in observation to prevent repeating dead ends (related `261009-batch-tool-non-fatal-execution-mode`)
  - 261010-state-inference-response-resilience Status: ACTIVE requirements and request inspection; clarify state-update output and recover from model format failures (related `261010-preview-request-pretty-inspection`, `261010-rolling-tool-failure-memory`)
- 260920-branch-projected-policy-program Branch-Projected Transcript Policy Program (related `260920-lcp-policy-reevaluation-contract`, `260920-transcript-policy-reinterpretation-examples`, `260920-transcript-control-documentation-contract`, `260831-transcript-source-reference-operations`, `325-config-override-lifecycle-load-save-restore-and-unset`, `330-semi-durable-shell-grants-transcript-and-config-lanes`, `310-transcript-env-modifiers-as-execution-surface`)
  - 260920-effective-policy-provenance-inspection Give an operator a compact inspection surface that explains the effective branch-visible policy for a selected step without claiming a universal setti... (depends on `260920-lcp-direct-policy-deltas`, `260920-config-load-result-reconstitution`; related `260920-transcript-control-documentation-contract`, `260825-visible-transcript-turn-ids`)
  - 260920-one-shot-control-ingress-disposition Determine whether `toas step --control` remains a useful operator-facing convenience, becomes transcript-materializing, is restricted to transient que... (related `260920-lcp-direct-policy-deltas`, `260920-lcp-policy-reevaluation-contract`, `260920-transcript-control-state-contract`)
- 260803-tool-intent-ingress-separation Separate native provider tool calling, TOAS text-callable alternatives, shared step/runtime semantics, and harness observation so any supported callin... (related `260803-language-exec-fenced-block-lane`, `260412-json-callable-lane-parser-and-policy`, `260803-seed-prompt-composition-study`, `260803-first-failure-plan-recovery`, `260628-gemini-endpoint-discovery`, `171`, `174`)
  - 260831-transcript-source-reference-operations Transcript-Native Assistant Source Reference Operations (related `260803-language-exec-fenced-block-lane`, `260803-first-failure-plan-recovery`, `260831-verbatim-staged-plan-restaging`, `260627-history-affordances-semantic-restaging`, `260830-exec-grant-policy-matchers`)
    - 260901-retry-materialization-adapters Representation-Neutral Retry Materialization (related `260901-source-reference-recovery-integration`, `260803-language-exec-fenced-block-lane`, `260831-language-write-materialization-fences`)
- 260803-language-exec-fenced-block-lane Define executable Markdown fence lanes with `<language> exec` as the clear canonical surface while preserving structurally activated and configurable ... (related `260412-json-callable-lane-parser-and-policy`, `260803-first-failure-plan-recovery`, `260803-seed-prompt-composition-study`, `260803-tool-intent-ingress-separation`, `299`)
  - 260830-exec-grant-policy-matchers Create the shared post-resolution authorization seam for assistant-directed executable runtimes. The seam should let user-owned policy express ordered... (related `260530-shell-lane-spawn-semantics`, `260829-configurable-interpreter-runtime-lane`, `260829-generic-interpreter-runtime-lane`)
  - 260831-language-write-materialization-fences Language-Native Write Materialization Fences (related `260831-transcript-source-reference-operations`, `260829-generic-interpreter-runtime-lane`, `260829-canonical-action-ingress-contract`)
- 260614-architecture-follow-through-coordination Architecture Follow-Through Coordination
  - 260614-legacy-and-fidelity-adapter-precedence Legacy And Fidelity-Adapter Precedence
  - 260626-events-jsonl-multiplicity-and-merge-provenance Events.jsonl Multiplicity And Merge Provenance (related `260626-transcript-parallelism-design-pressures`, `260509-multi-operator-orchestration`)
  - 260626-transcript-parallelism-design-pressures Transcript Parallelism Design Pressures (related `561`, `260509-multi-operator-orchestration`, `260524-exploratory-work-representation-model`, `260626-events-jsonl-multiplicity-and-merge-provenance`)
  - 260627-history-affordances-semantic-restaging History Affordances And Semantic Restaging (related `260626-transcript-parallelism-design-pressures`, `260524-exploratory-work-representation-model`)
  - 260811-activity-health-telemetry Define and implement a low-volume activity-health signal that makes runtime and transport stalls diagnosable without using always-on wire logs as the ... (related `260602-transport-equivalence-certification`, `260530-shell-lane-spawn-semantics`)
- 260627-release-process-and-weekly-release-lane Release Process And Weekly Release Lane (related `260628-project-checks-and-ci-posture`, `260627-release-helper-tooling`)
<!-- WORKBOARD:RELATIONSHIP_TREE:END -->

## 1. Open Queue

*Generated inventory. Read Manual Triage for readiness and sequencing.*

<!-- WORKBOARD:NOW:START -->
- **[T260412-transcript-lcp-checkpoint-optimization]** Optimize transcript-modifier resolution (`/shell`, `/env`, related command-derived state) using LCP/checkpoint state recovery plus tail replay. ⚠️ Stale
- **[T260418-weak-model-safe-apply-patch-contract]** Explore and define a weak-model-safe `apply_patch` tool contract that improves first-pass correctness and guided recovery for lower-prior models. ⚠️ Stale
- **[T260428-cross-repo-intent-routing]** Define scope/routing semantics for intents that span multiple repositories/workspaces without violating local history invariants. ⚠️ Stale
- **[T260509-alternative-operator-frontends]** Evaluate and stage a medium-horizon path for operator frontends beyond Vim, including VS Code, Antigravity, and/or Web surfaces. ⚠️ Stale
- **[T260509-multi-operator-orchestration]** Evaluate how TOAS can support an operator/driver relationship in which a human or Codex holds the larger intent and trajectory, while TOAS and its con... ⚠️ Stale
- **[T260515-apply-patch-windows-crlf-hardening]** Investigate and harden `apply_patch` behavior on Windows/CRLF files with explicit diagnostics around newline/context matching. ⚠️ Stale
- **[T260524-attention-focused-workboard-layout]** Design and implement an "Attention-Focused" layout for the Workboard that highlights high-impact tasks and suppresses noise. ⚠️ Stale
- **[T260524-auto-inferred-task-dependencies]** Develop a mechanism to automatically infer task dependencies from code changes and commit history, reducing manual overhead and improving accuracy. ⚠️ Stale
- **[T260524-exploratory-work-representation-model]** Define a flexible task schema that supports both "Verified Implementation" tasks and "Exploratory/Research" tasks without forcing one into the other's... ⚠️ Stale
- **[T260524-workboard-as-control-surface]** Transform `WORKBOARD.md` from a passive report into an active control surface that allows the operator to influence system behavior. ⚠️ Stale
- **[T260530-shell-lane-spawn-semantics]** Track and defer a focused cleanup to eliminate unintended behavior differences between assistant and user shell execution lanes by centralizing spawn ... ⚠️ Stale
- **[T260602-transport-equivalence-certification]** Only if and when it becomes worthwhile, push beyond task `669`'s contract-bounding bar toward stronger transport-equivalence proof and possibly a more... ⚠️ Stale
- **[T260614-architecture-follow-through-coordination]** Architecture Follow-Through Coordination
- **[T260614-legacy-and-fidelity-adapter-precedence]** Legacy And Fidelity-Adapter Precedence ⚠️ Stale
- **[T260621-windows-shell-launcher-and-path-resolution]** Windows Shell Launcher And Path Resolution
- **[T260626-events-jsonl-multiplicity-and-merge-provenance]** Events.jsonl Multiplicity And Merge Provenance ⚠️ Stale
- **[T260626-transcript-parallelism-design-pressures]** Transcript Parallelism Design Pressures ⚠️ Stale
- **[T260627-history-affordances-semantic-restaging]** History Affordances And Semantic Restaging ⚠️ Stale
- **[T260627-release-helper-tooling]** Release Helper Tooling ⚠️ Stale
- **[T260627-release-process-and-weekly-release-lane]** Release Process And Weekly Release Lane
- **[T260803-language-exec-fenced-block-lane]** Define executable Markdown fence lanes with `<language> exec` as the clear canonical surface while preserving structurally activated and configurable ... ⚠️ Stale
- **[T260803-tool-intent-ingress-separation]** Separate native provider tool calling, TOAS text-callable alternatives, shared step/runtime semantics, and harness observation so any supported callin... ⚠️ Stale
- **[T260806-assistance-provenance-trailers]** Capture a durable, truthful commit-provenance convention that distinguishes a Codex task UUID from TOAS's source-qualified event and familiar transcri... ⚠️ Stale
- **[T260811-activity-health-telemetry]** Define and implement a low-volume activity-health signal that makes runtime and transport stalls diagnosable without using always-on wire logs as the ...
- **[T260813-transcript-highlighting-design]** Explore a role-aware syntax-highlighting model for TOAS transcripts in Vim. The transcript remains an ordinary Markdown document, but its role heading... ⚠️ Stale
- **[T260823-conversation-map-projection]** Explore an inspectable conversation-map projection that reifies intent-tracking events, focus changes, and related provenance without adding cognitive... ⚠️ Stale
- **[T260823-intent-tail-focus-trace]** Explore how TOAS can derive a durable or inspectable trace of changing focus from intent-tracking tails and surrounding transcript evidence. ⚠️ Stale
- **[T260823-projection-discoverability]** Develop the discoverability and progressive-disclosure model for TOAS-owned prompt and projection surfaces as the family grows beyond `concept-graph` ... ⚠️ Stale
- **[T260825-visible-transcript-turn-ids]** Define transcript-facing human names and explicit references backed by canonical identity, so users and editor or CLI surfaces can select a turn witho...
- **[T260829-declared-objective-lane]** Replace the dormant `/intent` affordance with a clearly named declared- objective surface for explicit operator-maintained task context. ⚠️ Stale
- **[T260830-exec-grant-policy-matchers]** Create the shared post-resolution authorization seam for assistant-directed executable runtimes. The seam should let user-owned policy express ordered... ⚠️ Stale
- **[T260831-language-write-materialization-fences]** Language-Native Write Materialization Fences ⚠️ Stale
- **[T260831-transcript-source-reference-operations]** Transcript-Native Assistant Source Reference Operations ⚠️ Stale
- **[T260901-retry-materialization-adapters]** Representation-Neutral Retry Materialization ⚠️ Stale
- **[T260907-extraction-execution-boundary]** Trace one representative mixed-intent recovery/execution path from candidate extraction through the adjacent preview, adoption, authorization, and exe... ⚠️ Stale
- **[T260920-branch-projected-policy-program]** Branch-Projected Transcript Policy Program ⚠️ Stale
- **[T260920-effective-policy-provenance-inspection]** Give an operator a compact inspection surface that explains the effective branch-visible policy for a selected step without claiming a universal setti... ⚠️ Stale
- **[T260920-one-shot-control-ingress-disposition]** Determine whether `toas step --control` remains a useful operator-facing convenience, becomes transcript-materializing, is restricted to transient que... ⚠️ Stale
- **[T260926-state-step-requirements]** Develop a reviewable implementation contract for an explicitly state-shaped working surface handled by a state-step operation integrated with TOAS run...
- **[T261010-direct-tool-artifact-capture]** Status: OPEN; allow tool calls to declare an artifact label and auto-populate state upon execution
- **[T261010-rolling-tool-failure-memory]** Status: OPEN; maintain a compact rolling log of recent tool attempts and failures in observation to prevent repeating dead ends
- **[T261010-state-inference-response-resilience]** Status: ACTIVE requirements and request inspection; clarify state-update output and recover from model format failures
- **[T261010-state-result-history-sideslip]** Status: INCEPTION; retain observed state-mode history behavior for future consideration
- **[T261011-streaming-mode-env-leak-parent]** The environment leak is fixed. Retain the design rationale and the prospective question of preserving distinct stdout/stderr in streamed tool results....
- **[T261015-windows-compatibility-restoration]** Status: OPEN; coordinate restoration of native Windows behavior and routine verification
- **[T261017-msys-vim-native-host]** Status: OPEN; reconcile historical harness failure with working operator MSYS Vim
- **[T261029-openai-model-probe-auth-header]** Enable `fetch_models` to transmit the configured/resolved API key as an `Authorization: Bearer <token>` header when probing OpenAI-compatible endpoint...
<!-- WORKBOARD:NOW:END -->

## 2. Task Inbox

<!-- WORKBOARD:INBOX:START -->

<!-- WORKBOARD:INBOX:END -->

## 2a. Pain-Point Log

*Raw current operator friction; resolve or link entries when evidence changes.*

- **Windows editor evidence:** MSYS Vim works in operator use. Windows gVim
  failed historically and has not been retried after recent fixes. The older
  MSYS E282 harness probe is a separate reproduction question under
  `261017-msys-vim-native-host`.
- **State-mode reliability:** Recorded model format/composition failures are
  under `261010-state-inference-response-resilience`; inspect proposal and
  state-maintenance quality as well as format adherence.

The October 5 speculative tool-kind latch failure was fixed under
`261005-vim-frontier-tool-heuristic-and-kind-latch`. The broader latency question
should return only with a current timing reproduction.

## 2b. Unelaborated Backlog

*Conditional pressure; promote only when selected and bounded.*

- **Local model driver:** Optional in-process `llama-cpp` driver when a concrete
  need appears.
- **Routing policy:** Endpoint catalogs, discovery, model selection, and basic
  switching exist. Automatic task-class routing for parallel or summary work
  remains prospective; do not reopen the implemented catalog as missing work.

## 3. System Health

- **macOS:** Full `scripts/check.sh` at `622742c9`: 3,595 passed, nine skipped,
  17 deselected; 100.00% statement coverage; all 17 acceptance scenarios, Ruff,
  and mypy passed. Actual scratch rendering and Vim result buffer inspected.
- **Windows:** The restoration task records a full check with explicit native
  Vim before the latest macOS fixes. This is a platform baseline, not evidence
  that the current revision or gVim has been rechecked there.
- **Linux:** No current run recorded in this review.
- **Check policy:** `docs/checks.md` owns the gated local spine. Ruff and mypy
  are gates, not advisory. Hosted CI has not been adopted.
- **Maintenance:** Generated stale markers measure age; they do not establish
  bugs, urgency, or unfinished implementation. Recurring templates remain
  available under `tasks/recurring/`; this review is not a full docs audit.

## 4. Recent Closures

*Generated recent-task sample, not a complete completion ledger.*

<!-- WORKBOARD:CLOSED:START -->
- **[T261029-serialize-grants-on-session-rotation]** When rotating/continuing a session, serialize custom active shell grants from the predecessor session directly into the successor transcript as an exp...
- **[T261029-preserve-literal-shell-argv]** Preserve pre-tokenized `argv` arguments in assistant-driven `shell` tool execution without Python-side glob expansion, preventing command corruption i...
- **[T261029-configurable-session-continuation-naming]** Make session continuation naming configurable in session policy, defaulting to `session-YYMMDD-HHMM-short-name` while supporting datetime-only and leg...
- **[T261027-stream-bridge-timeout-test]** Status: CLOSED; retained hung-read semantics with a controlled clock.
- **[T261027-stdio-stall-diagnostics]** Status: CLOSED; request failures no longer block on live stderr.
<!-- WORKBOARD:CLOSED:END -->

### Impact Notes (Manual)

- State-step has an integrated alpha; model-fit and observation ergonomics
  are the remaining product questions, rather than whether the alpha exists.
- Branch-local config, grants, target selection, command/workspace context,
  and immutable config-load reconstitution have landed; effective provenance
  inspection remains a separate open surface.
- Segmented history, source-selection parity, and fatal-integrity refusal have
  landed. New history work should identify an observed affordance gap.
- Recent endpoint discovery/selection, continuity, and help fixes improve local
  model setup. Scratch ingestion and Vim control-result scope are now fixed.

## 5. Strategic Arcs

The current concerns and sequence are stated once in Manual Triage above.
`docs/roadmap.md` carries durable direction; task files own acceptance and
remaining scope. Earlier decomposition, runtime-ownership, acceptance, and
coverage umbrellas are historical foundations, not active blockers.
