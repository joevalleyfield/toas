# TOAS Workboard

> **Status:** Active Development
> **Last Sync:** 2026-06-14

## 0. Manual Triage
*Hand-curated operator triage, not automated extraction.*

- `671` was the roadmap/workboard sync item; this pass keeps the same contracted split and removes follow-on drift from later closures.
- Active implementation arcs are `525`, `400`, `374`, and `379`.
- Parked or exploratory items remain intentionally deferred: `349`, `365`, `415`, `463`, `464`, `488`, `490`, `513`, `548`, `557`, `558`, `559`, `560`, `566`, `660`, and `676`.

### Active Arc Map
*Lexical first-mention tree; repeated tokens use `@` on later appearances.*

- 525 runtime ownership / de-daemonization
  - 660 shell lane spawn-semantics follow-up (parked)
  - 676 transport-equivalence certification (parked)

- 400 module decomposition umbrella
  - 374 coverage-led refactor pass
  - 379 coverage noise burndown

## 1. Open Queue
*Generated open-task inventory. Use Manual Triage above for active vs parked sequencing.*

<!-- WORKBOARD:NOW:START -->
- **[T349]** keywords: exploration, explore, parked, research, json, callable, lane, parser, policy  Define a separate JSON-callable lane with explicit parser, ext...
- **[T365]** keywords: runtime, investigation, parked, performance, lcp, checkpoint, modifier-resolution, modifier  Optimize transcript-modifier resolution (`/shel...
- **[T374]** keywords: runtime, decomp, active, maintainability, coverage, refactor, tests, smells  Run a focused coverage-led refactor pass that improves testabil...
- **[T379]** keywords: runtime, decomp, active, maintainability, coverage, burndown, reporting, missing-lines  Reduce future coverage-report noise by driving selec...
- **[T400]** keywords: runtime, decomp, active, maintainability, decomposition, coverage, cli, tools, step  Break up `tools.py`, `step.py`, `cli.py`, and `daemon.p...
- **[T415]** keywords: tooling, explore, parked, contract, apply_patch, safety, weak-model, recovery  Explore and define a weak-model-safe `apply_patch` tool contr...
- **[T463]** keywords: surface, explore, parked, research, session, identity, buffer-mapping, mapping  Define and implement named/multi-buffer session identity sem...
- **[T464]** keywords: surface, explore, parked, research, cross-repo, intent, routing, projection  Define scope/routing semantics for intents that span multiple r...
- **[T488]** Evaluate higher-level orchestration patterns (including TOAS-in-TOAS or multi-agent collaboration) as a follow-on capability, separate from base singl...
- **[T490]** Evaluate and stage a medium-horizon path for operator frontends beyond Vim, including VS Code, Antigravity, and/or Web surfaces.
- **[T513]** `apply_patch` failures on Windows/CRLF content are recurring and difficult to diagnose without better matching instrumentation.
- **[T525]** Define and execute the next runtime architecture arc after envelope adoption so primary operator flows are ownership-coupled and user-surface-first, w...
- **[T548]** Adopt Python standard library `logging` as the primary diagnostics surface for runtime/host debug emission.
- **[T557]** The "Workboard" and auto-sync scripts assume a linear, verifiable structure. Exploratory work often yields non-linear insights, dead ends, or open-end...
- **[T558]** Develop a mechanism to automatically infer task dependencies from code changes and commit history, reducing manual overhead and improving accuracy.
- **[T559]** Transform `WORKBOARD.md` from a passive report into an active control surface that allows the operator to influence system behavior.
- **[T560]** Design and implement an "Attention-Focused" layout for the Workboard that highlights high-impact tasks and suppresses noise.
- **[T566]** Bound near-match fallback to a strict interactive time budget (target: 1–2 seconds wall-clock) and replace exhaustive exploration with higher-signal h...
- **[T660]** Track and defer a focused cleanup to eliminate unintended behavior differences between assistant and user shell execution lanes by centralizing spawn ...
- **[T676]** Only if and when it becomes worthwhile, push beyond task `669`'s contract-bounding bar toward stronger transport-equivalence proof and possibly a more...
<!-- WORKBOARD:NOW:END -->

## 2. Task Inbox
*Captured review items and inbox threads.*

<!-- WORKBOARD:INBOX:START -->

<!-- WORKBOARD:INBOX:END -->

### Strategic Priorities (Manual)
- **Runtime Ownership:** Prioritize ownership-first seams under `525`.
- **CLI Decomposition:** Execute remaining slices under `400`.

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
- **[T260608]** Current projection safety is split across result rendering, inert wrapping, import-shape ideas, Vim streaming formatting, and command/help special cas...
- **[T260608]** - sequencing and precedence model is explicit in docs/help and reflected in diagnostics
- **[T260608]** - reproducible minimal case is captured in tests
- **[T687]** - [x] each cluster has been evaluated: either remediated or documented as genuinely requiring the sl
- **[T686]** ## Current Reality
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
- **Status:** Umbrella `400` active.

### C. Weak-Model Protocol Reliability
- **Goal:** Deterministic tool guidance slices without manual coaching.
- **Status:** `471` closed; `415` open for patch safety.

### D. Transcript/Control/Config Contract Clarity
- **Goal:** Explicit precedence semantics and diagnostics.
- **Status:** `465`, `466`, and `354` closed; reopen only on fresh drift evidence.

### H. Primary-Path Runtime Ownership
- **Goal:** `step`/`watch`/`cancel` are ownership-first; cancellation is bounded/terminal.
- **Status:** `525` is the master umbrella.
