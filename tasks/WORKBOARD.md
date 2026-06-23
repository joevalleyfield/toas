# TOAS Workboard

> **Status:** Active Development
> **Last Sync:** 2026-06-22

## 0. Manual Triage
*Hand-curated operator triage, not automated extraction.*

- `260614-architecture-follow-through-coordination` is the active coordination
  object for top-down architecture follow-through. It ties subtasks to
  `docs/architecture-masterplan.md`, `docs/runtime-direction.md`, and
  `docs/runtime-ownership.md` without replacing those documents.
- First split children `260614-effective-policy-authority-resolver` and
  `260614-backend-lifecycle-identity-stale-config` are closed.
- `260614-backend-lifecycle-cross-process-identity` now parks the unresolved
  cross-process identity gap (backend process management is aspirational).
- `260614-shell-owned-backend-lifecycle` now parks the resolved design shape
  for shell-owned backend processes and parent session-host watchdogs.
- `260619-workboard-sync-script-parser-and-identity-fix` tracks the sync-script
  follow-up for task-identity preservation and metadata-safe summaries.
- `260615-legacy-surface-retirement-inventory` is closed: the first inventory
  slice now distinguishes transitional compatibility surfaces from
  fidelity-lowering adapters.
- `260619-session-md-compatibility-retirement` is closed: the CLI/runtime
  fallback to `session.md` has been retired.
- `260620-retire-host-session-path-env-coupling` is closed: host default
  session targeting now uses explicit host-owned state and `host_session_path`
  payload threading instead of ambient `TOAS_HOST_SESSION_PATH`.
- `260620-host-stdio-reasoning-terminality-ux` is closed: host-stdio
  substantive recovery now respects reasoning-stream visibility, command-only
  tails no longer fabricate assistant answers, and failed runs append a compact
  visible cause line instead of depending on log-file spelunking.
- `260619-daemon-package-facade-shrinkage` is closed: the remaining daemon
  package root is now a bounded compatibility/execution-entry facade with
  direct package-boundary coverage, including `toas.daemon.__main__`.
- Inception-only children now park the remaining known architecture pressures
  until they are ready for focused investigation.
- Task lists may stay linear where that reflects reality; active coordination
  work should preserve tree/graph relationships with explicit task links.
- Closed umbrellas `400`, `525`, `374`, and `379` remain historical context,
  not active work parents.
- Parked or exploratory items remain intentionally deferred unless pulled into
  the architecture coordination tree or selected as focused follow-ups: `349`,
  `365`, `415`, `463`, `464`, `488`, `490`, `513`, `557`, `558`, `559`, `560`,
  `660`, and `676`.

### Active Arc Map
*Lexical first-mention tree; repeated tokens use `@` on later appearances.*

- 260614 architecture follow-through coordination
  - architecture doc reconciliation after backend lifecycle landed
  - 260614 effective policy and authority resolver shape
  - 260614 backend lifecycle identity and stale-config contract
  - 260614 backend lifecycle cross-process identity (parked)
  - 260614 shell-owned backend lifecycle (parked)
  - 260614 model backend failure handoff (inception)
  - 260614 activity live/durable boundary (closed discovery)
  - 260614 transcript reconciliation handoff (inception)
  - 260614 legacy and fidelity-adapter precedence (inception)
  - 260615 force-structure alignment survey (inception)
  - 260615 runtime package growth boundary audit (inception)
  - 260619 workboard sync-script parser and identity fix (active)
  - 260619 session.md compatibility retirement (closed)
  - 260620 retire host session path env coupling (closed)
  - 260620 host-stdio reasoning terminality UX (closed)
  - 260619 daemon package facade shrinkage (closed)
  - edge fidelity adapter inventory (marker)
  - 260614 local suffix naming inversion (closed; historical reference)
  - 660 shell lane spawn-semantics follow-up (parked)
  - 676 transport-equivalence certification (parked)

- closed historical context: 400 module decomposition, 525 runtime ownership,
  374 coverage-led refactor pass, 379 coverage noise burndown

## 1. Open Queue
*Generated open-task inventory. Use Manual Triage above for active vs parked sequencing.*

<!-- WORKBOARD:NOW:START -->
- **[T349-json-callable-lane-separate-parser-and-policy-arc]** keywords: exploration, explore, parked, research, json, callable, lane, parser, policy  Define a separate JSON-callable lane with explicit parser, ext...
- **[T365-transcript-lcp-checkpoint-optimization-for-modifier-resolution]** keywords: runtime, investigation, parked, performance, lcp, checkpoint, modifier-resolution, modifier  Optimize transcript-modifier resolution (`/shel...
- **[T415-weak-model-safe-apply-patch-contract-exploration]** keywords: tooling, explore, parked, contract, apply_patch, safety, weak-model, recovery  Explore and define a weak-model-safe `apply_patch` tool contr...
- **[T463-session-identity-orchestration-and-buffer-mapping]** keywords: surface, explore, parked, research, session, identity, buffer-mapping, mapping  Define and implement named/multi-buffer session identity sem...
- **[T464-cross-repo-intent-routing-and-projection-scope]** keywords: surface, explore, parked, research, cross-repo, intent, routing, projection  Define scope/routing semantics for intents that span multiple r...
- **[T488-multi-operator-orchestration-exploration]** Evaluate higher-level orchestration patterns (including TOAS-in-TOAS or multi-agent collaboration) as a follow-on capability, separate from base singl...
- **[T490-alternative-operator-frontends-vscode-zed-antigravity-web]** Evaluate and stage a medium-horizon path for operator frontends beyond Vim, including VS Code, Antigravity, and/or Web surfaces.
- **[T513-apply-patch-windows-crlf-matching-instrumentation-and-hardening]** `apply_patch` failures on Windows/CRLF content are recurring and difficult to diagnose without better matching instrumentation.
- **[T557-exploratory-work-representation-model-and-flexible-task-schema]** The "Workboard" and auto-sync scripts assume a linear, verifiable structure. Exploratory work often yields non-linear insights, dead ends, or open-end...
- **[T558-auto-inferred-task-dependencies-from-code-changes]** Develop a mechanism to automatically infer task dependencies from code changes and commit history, reducing manual overhead and improving accuracy.
- **[T559-workboard-as-control-surface]** Transform `WORKBOARD.md` from a passive report into an active control surface that allows the operator to influence system behavior.
- **[T560-attention-focused-workboard-layout]** Design and implement an "Attention-Focused" layout for the Workboard that highlights high-impact tasks and suppresses noise.
- **[T660-shell-lane-spawn-semantics-unification-follow-up]** Track and defer a focused cleanup to eliminate unintended behavior differences between assistant and user shell execution lanes by centralizing spawn ...
- **[T676-transport-equivalence-certification-and-shared-adapter-followup]** Only if and when it becomes worthwhile, push beyond task `669`'s contract-bounding bar toward stronger transport-equivalence proof and possibly a more...
- **[T260614-architecture-follow-through-coordination]** # Architecture Follow-Through Coordination
- **[T260614-backend-lifecycle-cross-process-identity]** # Backend Lifecycle Cross-Process Identity
- **[T260614-legacy-and-fidelity-adapter-precedence]** # Legacy And Fidelity-Adapter Precedence
- **[T260614-model-backend-failure-handoff]** # Model Invocation To Backend Lifecycle Failure Handoff
- **[T260614-shell-owned-backend-lifecycle]** # Shell-Owned Backend Lifecycle
- **[T260614-transcript-reconciliation-handoff]** # Transcript Reconciliation Handoff Object
- **[T260614-vim-test-cost-audit]** Filed as: 260614-vim-test-cost-audit FKA: AKA: vim tests; test suite cost; stdio contract tests; test performance Legacy index: 688  keywords: vim, te...
- **[T260615-runtime-package-growth-boundary-audit]** # Runtime Package Growth Boundary Audit
<!-- WORKBOARD:NOW:END -->

## 2. Task Inbox
*Captured review items and inbox threads.*

<!-- WORKBOARD:INBOX:START -->

<!-- WORKBOARD:INBOX:END -->

### Strategic Priorities (Manual)
- **Architecture Follow-Through:** Coordinate top-down domain work under
  `260614-architecture-follow-through-coordination`.
- **Focused Implementation:** Open narrow subtasks from concrete architecture,
  failure, or regression evidence rather than reopening closed umbrellas.
- **Immediate Queue Order:** `260621-windows-shell-launcher-and-path-resolution`
  is the next active implementation lane now that user-shell globbing recovery
  is closed.

## 3. System Health
*Recurring maintenance and operational metrics.*

### Coverage & Hygiene
- [ ] **Coverage Ratchet**
  - *Last Run:* 2026-05-16
  - *Next Target:* `src/toas/cli/` and `src/toas/step/`
- [ ] **Docs Truth Governance**
  - *Last Run:* 2026-05-16
  - *Action:* Align `README.md` and `tasks/recurring/` templates with actual surface.

### Operational Sharp Edges
- [ ] **Sharp Edges Log**
  - *Last Run:* 2026-05-16
  - *Active Issues:*
    - [ ] Windows async fixes follow-up (see #369)
    - [ ] Vim transport annotation cleanup (see #554)

## 4. Recent Closures
*Key completions driving current momentum.*

<!-- WORKBOARD:CLOSED:START -->
- **[T260621-enable-shell-globbing]** - user `$ ...` shell shorthand now regains substantive wildcard expansion via real shell routing
- **[T566-search-block-near-match-time-budget-and-heuristics]** - `search_block` near-match fallback is now budget-bounded and heuristic-first instead of exhaustive
- **[T260619-daemon-package-facade-shrinkage]** - daemon package root is now a thin compatibility/execution-entry facade with direct package-boundary coverage
- **[T260620-host-stdio-reasoning-terminality-ux]** - host-stdio recovery is stream-policy-aware and failed runs append a compact visible cause line
- **[T260620-retire-host-session-path-env-coupling]** - host default session targeting is explicit host-owned state, not ambient env
- **[T260620-read-file-line-window-support]** - `read_file` accepts optional `start_line` and `end_line`
- **[T260619-workboard-sync-script-parser-and-identity-fix]** - generated board entries preserve distinct task handles
- **[T260619-session-md-compatibility-retirement]** # Session.md Compatibility Retirement
- **[T260615-retire-dead-modules-and-shims]** # Retire Dead Modules and Compatibility Shims
- **[T260615-relocate-reconciliation-lcp-logic]** # Relocate Transcript Reconciliation LCP Logic
<!-- WORKBOARD:CLOSED:END -->

### Impact Notes (Manual)
- **510:** Imported content projection now emits stable fenced metadata blocks for file reads, search excerpts, and high-confidence shell file output.
- **675:** Runtime/tool ownership guidance now lives in `docs/runtime-ownership.md`; legacy hub files are documented as facades.
- **543:** Stream-first stdio host lifecycle path established.
- **542:** Historical record preserved after local-host default cutover.
- **551:** Vim default transport is now `local_host`.
- **533:** CLI-level local mode lifecycle contract validated.

## 5. Strategic Arcs
*High-level themes and open questions.*

### A. Acceptance-Proven Operator Completion
- **Goal:** Reproducible end-to-end acceptance path from intake to validated commit.
- **Status:** Foundation closed under `469`/`470`; further orchestration exploration is parked under `488`.

### B. Maintainable Runtime Decomposition
- **Goal:** Thinner facades, focused helper ownership, stable coverage.
- **Status:** Umbrellas `400`, `374`, and `379` are closed; future work should
  open focused tasks from concrete domain, failure, or regression evidence.

### C. Weak-Model Protocol Reliability
- **Goal:** Deterministic tool guidance slices without manual coaching.
- **Status:** `471` closed; `415` open for patch safety.

### D. Transcript/Control/Config Contract Clarity
- **Goal:** Explicit precedence semantics and diagnostics.
- **Status:** `465`, `466`, and `354` closed; reopen only on fresh drift evidence.

### H. Primary-Path Runtime Ownership
- **Goal:** `step`/`watch`/`cancel` are ownership-first; cancellation is bounded/terminal.
- **Status:** `525` is closed; future ownership work should route through the
  architecture coordination task or focused follow-ups.
