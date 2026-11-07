# TOAS Workboard

> **Status:** Active Development
> **Last Sync:** 2026-11-06

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
| Policy, authority, and explicit objectives | 4 | Branch-projected policy program, scoped engine, provenance inspection, and one-shot ingress are complete. Central exec-grant matchers and declared objectives remain open. |
| Execution ingress and source fidelity | 6 | Native/text ingress, language fences, source references, retry adapters, materialization, and extraction boundaries have mixed landed and prospective scope. |
| Platform and patch behavior | 5 | October 20 inventory; October 30 follow-up closes launcher and MSYS verification. Native Windows checks, gVim smoke, and initialized MSYS smoke pass. Patch research remains parked. |
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
   `260830-exec-grant-policy-matchers` (centralizing post-resolution
   executable grant authorization), and `261010-rolling-tool-failure-memory`
   (compact tool failure memory to prevent dead loops). This is a candidate
   list, not three simultaneous implementation commitments.
3. **Handle platform reports through current reproductions.** October 30
   verification closes the old launcher and MSYS evidence questions; gVim smoke
   also passes. MSYS Vim requires its initialized MSYS environment; direct
   native launch is outside scope. Linux parity remains unmeasured here.
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
- `260803-tool-intent-ingress-separation`
- `260803-language-exec-fenced-block-lane`
- `260614-architecture-follow-through-coordination`
- `260627-release-process-and-weekly-release-lane`
<!-- WORKBOARD:RELATIONSHIP_ROOTS:END -->

### Active Arc Map

*Generated first-mention relationship tree; repeated tasks use `@task-id`.*

<!-- WORKBOARD:RELATIONSHIP_TREE:START -->
- 260926-state-step-requirements Develop a reviewable implementation contract for an explicitly state-shaped working surface handled by a state-step operation integrated with TOAS run... (depends on `260926-state-simulation-checkpoint`; related `260926-state-step-contract-spike`, `260926-state-experiment-harness`, `260926-state-experiment-plan-tools`, `260803-session-rotation-lifecycle`, `260927-state-step-history-projections`, `260928-state-user-control-turn-lifecycle`, `261002-state-transcript-branching-and-modification`, `261010-state-inference-response-resilience`, `261010-state-result-history-sideslip`)
  - 261010-rolling-tool-failure-memory Status: OPEN; maintain a compact rolling log of recent tool attempts and failures in observation to prevent repeating dead ends (related `261009-batch-tool-non-fatal-execution-mode`)
- 260803-tool-intent-ingress-separation Separate native provider tool calling, TOAS text-callable alternatives, shared step/runtime semantics, and harness observation so any supported callin... (related `260803-language-exec-fenced-block-lane`, `260412-json-callable-lane-parser-and-policy`, `260803-seed-prompt-composition-study`, `260803-first-failure-plan-recovery`, `260628-gemini-endpoint-discovery`, `171`, `174`)
  - 260831-transcript-source-reference-operations Transcript-Native Assistant Source Reference Operations (related `260803-language-exec-fenced-block-lane`, `260803-first-failure-plan-recovery`, `260831-verbatim-staged-plan-restaging`, `260627-history-affordances-semantic-restaging`, `260830-exec-grant-policy-matchers`)
    - 260901-retry-materialization-adapters Representation-Neutral Retry Materialization (related `260901-source-reference-recovery-integration`, `260803-language-exec-fenced-block-lane`, `260831-language-write-materialization-fences`)
- 260803-language-exec-fenced-block-lane Define executable Markdown fence lanes with `<language> exec` as the clear canonical surface while preserving structurally activated and configurable ... (related `260412-json-callable-lane-parser-and-policy`, `260803-first-failure-plan-recovery`, `260803-seed-prompt-composition-study`, `260803-tool-intent-ingress-separation`, `299`)
  - 261104-fence-io-channels Fence I/O Channels And Artifact Redirection (related `260831-language-write-materialization-fences`, `261010-direct-tool-artifact-capture`, `260926-state-step-requirements`, `260831-transcript-source-reference-operations`)
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
- **[T260412-transcript-lcp-checkpoint-optimization]** Optimize transcript-modifier resolution (`/shell`, `/env`, related command-derived state) using LCP/checkpoint state recovery plus tail replay.
- **[T260418-weak-model-safe-apply-patch-contract]** Explore and define a weak-model-safe `apply_patch` tool contract that improves first-pass correctness and guided recovery for lower-prior models.
- **[T260428-cross-repo-intent-routing]** Define scope/routing semantics for intents that span multiple repositories/workspaces without violating local history invariants.
- **[T260509-alternative-operator-frontends]** Evaluate and stage a medium-horizon path for operator frontends beyond Vim, including VS Code, Antigravity, and/or Web surfaces.
- **[T260509-multi-operator-orchestration]** Evaluate how TOAS can support an operator/driver relationship in which a human or Codex holds the larger intent and trajectory, while TOAS and its con...
- **[T260515-apply-patch-windows-crlf-hardening]** Investigate and harden `apply_patch` behavior on Windows/CRLF files with explicit diagnostics around newline/context matching.
- **[T260524-attention-focused-workboard-layout]** Design and implement an "Attention-Focused" layout for the Workboard that highlights high-impact tasks and suppresses noise.
- **[T260524-auto-inferred-task-dependencies]** Develop a mechanism to automatically infer task dependencies from code changes and commit history, reducing manual overhead and improving accuracy.
- **[T260524-exploratory-work-representation-model]** Define a flexible task schema that supports both "Verified Implementation" tasks and "Exploratory/Research" tasks without forcing one into the other's...
- **[T260524-workboard-as-control-surface]** Transform `WORKBOARD.md` from a passive report into an active control surface that allows the operator to influence system behavior.
- **[T260530-shell-lane-spawn-semantics]** Track and defer a focused cleanup to eliminate unintended behavior differences between assistant and user shell execution lanes by centralizing spawn ...
- **[T260602-transport-equivalence-certification]** Only if and when it becomes worthwhile, push beyond task `669`'s contract-bounding bar toward stronger transport-equivalence proof and possibly a more...
- **[T260614-architecture-follow-through-coordination]** Architecture Follow-Through Coordination
- **[T260614-legacy-and-fidelity-adapter-precedence]** Legacy And Fidelity-Adapter Precedence
- **[T260626-events-jsonl-multiplicity-and-merge-provenance]** Events.jsonl Multiplicity And Merge Provenance
- **[T260626-transcript-parallelism-design-pressures]** Transcript Parallelism Design Pressures
- **[T260627-history-affordances-semantic-restaging]** History Affordances And Semantic Restaging
- **[T260627-release-helper-tooling]** Release Helper Tooling
- **[T260627-release-process-and-weekly-release-lane]** Release Process And Weekly Release Lane
- **[T260803-language-exec-fenced-block-lane]** Define executable Markdown fence lanes with `<language> exec` as the clear canonical surface while preserving structurally activated and configurable ...
- **[T260803-tool-intent-ingress-separation]** Separate native provider tool calling, TOAS text-callable alternatives, shared step/runtime semantics, and harness observation so any supported callin...
- **[T260806-assistance-provenance-trailers]** Capture a durable, truthful commit-provenance convention that distinguishes a Codex task UUID from TOAS's source-qualified event and familiar transcri...
- **[T260811-activity-health-telemetry]** Define and implement a low-volume activity-health signal that makes runtime and transport stalls diagnosable without using always-on wire logs as the ...
- **[T260813-transcript-highlighting-design]** Explore a role-aware syntax-highlighting model for TOAS transcripts in Vim. The transcript remains an ordinary Markdown document, but its role heading...
- **[T260823-conversation-map-projection]** Explore an inspectable conversation-map projection that reifies intent-tracking events, focus changes, and related provenance without adding cognitive...
- **[T260823-intent-tail-focus-trace]** Explore how TOAS can derive a durable or inspectable trace of changing focus from intent-tracking tails and surrounding transcript evidence.
- **[T260823-projection-discoverability]** Develop the discoverability and progressive-disclosure model for TOAS-owned prompt and projection surfaces as the family grows beyond `concept-graph` ...
- **[T260825-visible-transcript-turn-ids]** Define transcript-facing human names and explicit references backed by canonical identity, so users and editor or CLI surfaces can select a turn witho...
- **[T260829-declared-objective-lane]** Replace the dormant `/intent` affordance with a clearly named declared- objective surface for explicit operator-maintained task context.
- **[T260831-transcript-source-reference-operations]** Transcript-Native Assistant Source Reference Operations
- **[T260901-retry-materialization-adapters]** Representation-Neutral Retry Materialization
- **[T260907-extraction-execution-boundary]** Trace one representative mixed-intent recovery/execution path from candidate extraction through the adjacent preview, adoption, authorization, and exe...
- **[T260926-state-step-requirements]** Develop a reviewable implementation contract for an explicitly state-shaped working surface handled by a state-step operation integrated with TOAS run...
- **[T261010-rolling-tool-failure-memory]** Status: OPEN; maintain a compact rolling log of recent tool attempts and failures in observation to prevent repeating dead ends
- **[T261010-state-result-history-sideslip]** Status: INCEPTION; retain observed state-mode history behavior for future consideration
- **[T261011-streaming-mode-env-leak-parent]** The environment leak is fixed. Retain the design rationale and the prospective question of preserving distinct stdout/stderr in streamed tool results....
- **[T261104-fence-io-channels]** Fence I/O Channels And Artifact Redirection
- **[T261105-apply-patch-indent-leniency-and-diff-diagnostics]** apply_patch Indentation Leniency and Unified Diff Diagnostics
- **[T261106-bounded-step-quiescence]** Bounded Multi-Turn Stepping with Quiescence Termination
- **[T261106-fence-aware-transcript-markers]** Fence-Aware Transcript Marker Parsing
- **[T261106-microkernel-skill-runtime-boundary]** Microkernel Runtime Boundary and Fast-Path Code-Only Skills
- **[T261106-skill-specialization-and-script-distillation]** Skill Specialization and Script Distillation Pipeline
- **[T261106-standard-agent-skills-integration]** Standard Agent Skills Support and Extensible Task Recording
- **[T261106-target-coupled-generation-settings]** Target- and Endpoint-Coupled Generation Settings and Client-Side Throttling
<!-- WORKBOARD:NOW:END -->

## 2. Task Inbox

<!-- WORKBOARD:INBOX:START -->

<!-- WORKBOARD:INBOX:END -->

## 2a. Pain-Point Log

*Raw current operator friction; resolve or link entries when evidence changes.*

- **Windows editor evidence:** MSYS Vim works in operator use. Windows gVim
  failed historically; its real-host startup/render/exit smoke passes on
  2026-10-30. The native-launched MSYS harness fails, but a login MSYS Bash
  facsimile with MSYS fixture paths passes host/render/exit checks both with
  clean and normal Vim configuration. Closed under `261017-msys-vim-native-host`;
  MSYS Bash → MSYS Vim → native TOAS/Python is a primary supported workflow;
  launching MSYS Vim outside its initialized environment is unsupported and
  requires no detection or repair feature.
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
- **Windows:** Full `scripts/check.sh` on 2026-10-30 at `85a7b4ce` with explicit
  native Vim: 3,612 passed, eight skipped, 17 deselected; 100.00% coverage;
  all 17 acceptance scenarios, Ruff, and mypy pass. Separate gVim real-host
  smoke passes. MSYS login-environment facsimile passes; see editor evidence
  for the failing native-launched harness and its environment/path mismatch.
- **Linux:** No current run recorded in this review.
- **Check policy:** `docs/checks.md` owns the gated local spine. Ruff and mypy
  are gates, not advisory. Hosted cross-platform CI is implemented; see
  `docs/checks.md` for its contract.
- **Maintenance:** Generated stale markers measure age; they do not establish
  bugs, urgency, or unfinished implementation. Recurring templates remain
  available under `tasks/recurring/`; this review is not a full docs audit.

## 4. Recent Closures

*Generated recent-task sample, not a complete completion ledger.*

<!-- WORKBOARD:CLOSED:START -->
- **[T261106-vim-step-count-prefix]** Support Count Prefix for Vim Step Mapping (`[N]\s` -> `toas step [N]`)
- **[T261106-token-count-decorations]** Cumulative Token-Count Turn Telemetry Decorations
- **[T261106-content-spillage-refinement]** Content Spillage Refinement: Dynamic Thresholds, Bookends, Error Focus, and Elision
- **[T261106-bounded-step-quiescence]** Bounded Multi-Turn Stepping with Quiescence Termination
- **[T261106-assistant-turn-handle-progression]** Assistant Turn Handle Progression And History Plumbing
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
