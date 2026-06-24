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
- `260619-workboard-sync-script-parser-and-identity-fix` is closed: generated
  board entries preserve full task handles, fallback summaries ignore task
  header metadata, and the sync-script follow-up is complete.
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
  - 260619 workboard sync-script parser and identity fix (closed)
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
- **[T260412-json-callable-lane-parser-and-policy]** Prompt-library text previously implied JSON action objects as if they were equivalent to current callable extraction, which created operator confusion...
- **[T260412-transcript-lcp-checkpoint-optimization]** Correctness fixes should land first, but full transcript rescans each step are unnecessary once we can recover effective state at a known checkpoint a...
- **[T260418-weak-model-safe-apply-patch-contract]** Current tool ergonomics rely significantly on model priors. We want a tighter contract and response shape that remains reliable when priors are weaker...
- **[T260428-cross-repo-intent-routing]** Cross-repo mission workflows were identified as a follow-on at `456` closure.
- **[T260428-session-identity-orchestration]** `456` established configurable transcript paths; next step is ergonomic multi-buffer identity and selection.
- **[T260509-alternative-operator-frontends]** Vim remains functional, but frontend diversity improves operator fit, reduces single-client coupling risk, and can surface protocol/runtime assumption...
- **[T260509-multi-operator-orchestration]** There is clear interest in reducing single-operator cognitive overhead by introducing structured high-level delegation/orchestration. This should be e...
- **[T260515-apply-patch-windows-crlf-hardening]** `apply_patch` failures on Windows/CRLF content are recurring and difficult to diagnose without better matching instrumentation.
- **[T260524-attention-focused-workboard-layout]** Design and implement an "Attention-Focused" layout for the Workboard that highlights high-impact tasks and suppresses noise.
- **[T260524-auto-inferred-task-dependencies]** Develop a mechanism to automatically infer task dependencies from code changes and commit history, reducing manual overhead and improving accuracy.
- **[T260524-exploratory-work-representation-model]** Define a flexible task schema that supports both "Verified Implementation" tasks and "Exploratory/Research" tasks without forcing one into the other's...
- **[T260524-workboard-as-control-surface]** Transform `WORKBOARD.md` from a passive report into an active control surface that allows the operator to influence system behavior.
- **[T260530-shell-lane-spawn-semantics]** Recent investigation under `571` found a deterministic lane split: Assistant lane shell calls could hang for commands like `rg ...` when no explicit p...
- **[T260602-transport-equivalence-certification]** `669` closed at the right bar for current work: shared runtime semantics are explicit routed daemon/RPC subscribe path no longer blocks parity legacy ...
- **[T260614-architecture-follow-through-coordination]** # Architecture Follow-Through Coordination
- **[T260614-backend-lifecycle-cross-process-identity]** # Backend Lifecycle Cross-Process Identity
- **[T260614-legacy-and-fidelity-adapter-precedence]** # Legacy And Fidelity-Adapter Precedence
- **[T260614-model-backend-failure-handoff]** # Model Invocation To Backend Lifecycle Failure Handoff
- **[T260614-shell-owned-backend-lifecycle]** # Shell-Owned Backend Lifecycle
- **[T260614-vim-test-cost-audit]** The vim tests dominate suite wall-clock time. Before accepting that cost as necessary, we should verify that the test structure isn't paying for setup...
- **[T260615-runtime-package-growth-boundary-audit]** # Runtime Package Growth Boundary Audit
- **[T260621-assistant-callable-plan-coalescing]** # Assistant Callable Plan Coalescing
- **[T260621-compact-search-output]** # Compact Search Output
- **[T260621-eval-command-output-formatting]** # Audit and Standardize Command Output Formats
- **[T260621-windows-shell-launcher-and-path-resolution]** # Windows Shell Launcher And Path Resolution
- **[T260621-yaml-block-indent-salvage]** # YAML Block Indent Salvage
- **[T260622-staged-replay-trailing-edge-newline-healing]** # Staged Replay Trailing-Edge Newline Healing
- **[T260622-tool-write-newline-policy-and-windows-lf-defaults]** # Tool Write Newline Policy And Windows LF Defaults
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
- **New Follow-Up:** `260622-staged-replay-trailing-edge-newline-healing`
  captures the likely CRLF/trailing-newline seam where indent-only mismatches
  may fall back to fuzzy diagnostics instead of staging `/heal`.
- **New Follow-Up:** `260622-tool-write-newline-policy-and-windows-lf-defaults`
  captures Windows tool-written CRLF defaults creating mixed endings in
  otherwise LF-oriented repos.

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
- **[T260621-staged-replay-healing-indent-only-mismatches]** # Staged Replay Healing For Indent-Only Mismatches
- **[T260621-search-block-first-line-indent-diff-fidelity]** # Search Block First-Line Indent Diff Fidelity
- **[T260621-read-file-optional-line-numbering]** # Read File Optional Line Numbering
- **[T260621-enable-shell-globbing]** # Enable Shell Globbing
- **[T260620-retire-host-session-path-env-coupling]** # Retire Host Session Path Env Coupling
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
