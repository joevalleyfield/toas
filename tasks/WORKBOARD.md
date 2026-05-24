# TOAS Workboard

> **Status:** Active Development
> **Last Sync:** 2026-05-26

## 1. Now
*Active open tasks and immediate sequencing.*

<!-- WORKBOARD:NOW:START -->
- **[T349]** Define a separate JSON-callable lane with explicit parser, extraction semantics, and policy behavior, without coupling it to the current fenced-YAML c...
- **[T354]** Diagnose and fix selected-head transcript projection so rewinds reflect the intended lineage boundary and do not unexpectedly retain distant/sibling r...
- **[T365]** Optimize transcript-modifier resolution (`/shell`, `/env`, related command-derived state) using LCP/checkpoint state recovery plus tail replay.
- **[T374]** Run a focused coverage-led refactor pass that improves testability and uses uncovered seams to expose and address code smells we have deferred.
- **[T379]** Reduce future coverage-report noise by driving selected small/medium modules to `100%` so they disappear from the missing-lines output.
- **[T400]** Break up `tools.py`, `step.py`, `cli.py`, and `daemon.py` into smaller modules/directories so coverage reports and maintenance work target coherent un...
- **[T415]** Explore and define a weak-model-safe `apply_patch` tool contract that improves first-pass correctness and guided recovery for lower-prior models.
- **[T463]** Define and implement named/multi-buffer session identity semantics (for example `.toas/session-<name>.md`) while preserving canonical `events.jsonl` a...
- **[T464]** Define scope/routing semantics for intents that span multiple repositories/workspaces without violating local history invariants.
- **[T466]** Clarify and stabilize the `/config` sequencing contract (timing, lane precedence, durability classes) with stronger operator diagnostics and documenta...
- **[T488]** Evaluate higher-level orchestration patterns (including TOAS-in-TOAS or multi-agent collaboration) as a follow-on capability, separate from base singl...
- **[T490]** Evaluate and stage a medium-horizon path for operator frontends beyond Vim, including VS Code, Antigravity, and/or Web surfaces.
- **[T497]** Further decompose `src/toas/tools_cluster/shell_ops.py` so subprocess execution, stream-emission policy, and shell-shape adapters are separated into f...
- **[T510]** Imported file content currently lacks a consistent fenced-block contract with explicit metadata. We need deterministic structure so downstream tooling...
- **[T513]** `apply_patch` failures on Windows/CRLF content are recurring and difficult to diagnose without better matching instrumentation.
- **[T525]** Define and execute the next runtime architecture arc after envelope adoption so primary operator flows are ownership-coupled and user-surface-first, w...
- **[T534]** Move async operator behavior to local-first default for CLI-owned sessions while retaining explicit RPC opt-back and safe cutover controls.
- **[T548]** Adopt Python standard library `logging` as the primary diagnostics surface for runtime/host debug emission.
- **[T549]** Reproduce root-equivalent parenting failures with minimal deterministic fixtures. Prevent root-equivalent messages from being attached as non-root chi...
- **[T550]** Current message taxonomy treats root-parenting as an exceptional branch (`null` parent handling). LCP/divergence logic must branch on root/non-root pa...
<!-- WORKBOARD:NOW:END -->

### Strategic Priorities (Manual)
- **Runtime Ownership:** Prioritize ownership-first seams under `525`.
- **CLI Decomposition:** Execute remaining slices under `400`.

## 2. System Health
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

## 3. Recent Closures
*Key completions driving current momentum.*

<!-- WORKBOARD:CLOSED:START -->
- **[T556]** Reproduce the missing-marker behavior with a deterministic fixture. Reproduce and lock down the Vim plugin streaming completion failure path specifica...
- **[T555]** - a dedicated harness can reproduce healthy and pathological transport cases deterministically
- **[T554]** - all approved annotation targets from `553` Step 5 are implemented
- **[T553]** - architecture-shift narrative is captured in durable task/docs surfaces
- **[T552]** - callback path replaces polling as primary intake in contract plugin
<!-- WORKBOARD:CLOSED:END -->

### Impact Notes (Manual)
- **543:** Stream-first stdio host lifecycle path established.
- **542:** Historical record preserved after local-host default cutover.
- **551:** Vim default transport is now `local_host`.
- **533:** CLI-level local mode lifecycle contract validated.

## 4. Strategic Arcs
*High-level themes and open questions.*

### A. Acceptance-Proven Operator Completion
- **Goal:** Reproducible end-to-end acceptance path from intake to validated commit.
- **Status:** Foundation open under `469`/`470`.

### B. Maintainable Runtime Decomposition
- **Goal:** Thinner facades, focused helper ownership, stable coverage.
- **Status:** Umbrella `400` active.

### C. Weak-Model Protocol Reliability
- **Goal:** Deterministic tool guidance slices without manual coaching.
- **Status:** `471` closed; `415` open for patch safety.

### D. Transcript/Control/Config Contract Clarity
- **Goal:** Explicit precedence semantics and diagnostics.
- **Status:** `465` closed; `466` open.

### H. Primary-Path Runtime Ownership
- **Goal:** `step`/`watch`/`cancel` are ownership-first; cancellation is bounded/terminal.
- **Status:** `525` is the master umbrella.
