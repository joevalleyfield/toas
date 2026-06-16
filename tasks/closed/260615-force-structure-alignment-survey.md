Filed as: 260615-force-structure-alignment-survey
FKA:
AKA: architecture force survey; alignment survey; least-aligned surface inventory
Legacy index:

keywords: docs, investigation, closed, architecture, alignment, survey, boundaries, maintainability

# Force Structure Alignment Survey

## Current Reality

The architecture work has named the main forces: durable state, transcript
reconciliation, operator semantics, activity lifecycle, session host
supervision, effective policy and authority, model invocation, model backend
lifecycle, transport/protocol, surface adapters, and projection/rendering.

Individual tasks now cover several seams, but there is no broad survey task
that periodically asks which current code, docs, names, adapters, or task
claims are least aligned with that force structure.

Parent: `260614-architecture-follow-through-coordination`

## Desired Reality

TOAS should have an explicit alignment survey pass that inventories the most
force-misaligned current surfaces and converts them into bounded future work.

The survey should rank friction by how much it distorts current understanding
or blocks future alignment, not by how tempting a new feature might be.

## Completed Survey: 2026-06-15

The initial survey of the repository has identified the following misalignments:

### 1. Naming Mismatch

* **Stale `local_` Prefix**: 
  * *Evidence*: Modules like `src/toas/runtime/local_request_handler_edges.py`, `local_request_ops.py`, and `local_request_handler_edges.py` still carry the `local_` prefix. Under the stdio-first and session-rooted host model, these handlers coordinate core *runtime* requests (whether CLI-local or routed through stdio host), making the `local_` prefix a confusing vestige of the legacy daemon-client split.
  * *Distorted Force*: `Transport And Protocol` / `Surface Adapters` / `Operator Semantics`.
  * *Follow-Up*: Combine with the parked `260614-retire-local-suffix-naming-inversion` task once the contours of runtime interfaces are fully stabilized.
* **Dangling Compatibility Shims**:
  * *Evidence*: `src/toas/runtime_edges.py` and `src/toas/step_frontier.py` are 7-line shims that simply export everything from `toas.runtime.rpc_edges` and `toas.runtime.frontier_resolution` respectively. They are completely unused in both `src/` and `tests/`.
  * *Distorted Force*: `Transport And Protocol` / `Operator Semantics` / `Legacy Transition`.
  * *Follow-Up*: Retire these shims completely as part of the legacy surface retirement pass.

### 2. Ownership Mismatch

* **Reconciliation Logic in Legacy Facade**:
  * *Evidence*: `step_runtime.py` (Operator Semantics) imports `_normalize_anchor_index` and `_lcp` from `toas.step` (legacy step facade). Calculating the longest common prefix (LCP) to align edited transcript text to canonical history is a `Transcript Reconciliation` concern, but it currently resides in a legacy facade.
  * *Distorted Force*: `Transcript Reconciliation` vs `Operator Semantics`.
  * *Follow-Up*: Consolidate LCP and anchor index normalization into a dedicated `Transcript Reconciliation` helper module in `runtime/` (or merge into `transcript.py`), then migrate `step_runtime.py` to import from it.
* **Task Capture in Public Facade**:
  * *Evidence*: `toas/tools.py` (legacy tools registry facade) imports `route_and_capture` from `toas/tasks.py`. The capability to capture task threads from model output should be decoupled from the core tools registry interface.
  * *Distorted Force*: `Capabilities` vs `Operator Semantics`.
  * *Follow-Up*: Migrate the import of `tasks.py` out of `tools.py` once tools facade cleanup occurs.

### 3. Adapter / Domain Confusion

* **Mixed Handler Seams**:
  * *Evidence*: `src/toas/runtime/local_request_handler_edges.py` maps request payload dicts to handler functions, but it directly imports adapters (`async_local_start_adapter.py`) and runtime workers (`async_step_runtime_worker.py`), mixing transport adapter dispatch with core runtime step lifecycle.
  * *Distorted Force*: `Transport And Protocol` vs `Activity Lifecycle`.
  * *Follow-Up*: Explicitly separate request dispatching adapters from core async activity lifecycle workers.

### 4. Legacy Transition Debt

* **Completely Unused/Dead Modules**:
  * *Evidence*: `src/toas/reconcile.py` contains 20 lines of code calculating LCP, but it is never imported or used anywhere in `src/` or `tests/`. This is dead code.
  * *Distorted Force*: `Transcript Reconciliation` / `Legacy Debt`.
  * *Follow-Up*: Remove `src/toas/reconcile.py`.
* **Active Imports of Facades**:
  * *Evidence*: The legacy facades `tools.py` and `step.py` are heavily imported by tests and production modules (e.g. `cli.py`, `capability_prompts.py`, `tools_guidance.py`), preventing their sunsetting.
  * *Distorted Force*: `Legacy Transition`.
  * *Follow-Up*: Tracked under `260615-legacy-surface-retirement-inventory`.

### 5. Documentation Fiction

* **LCP Reconciliation Description**:
  * *Evidence*: `docs/execution-model.md` describes transcript reconciliation as a formal conceptual pass via LCP prefix matching, but the module `src/toas/reconcile.py` is dead code, and the actual calculations are done via non-public helpers in the legacy `step.py` facade.
  * *Distorted Force*: `Transcript Reconciliation` / `Documentation`.
  * *Follow-Up*: Document the actual reconciliation entry points in `docs/execution-model.md` and clean up the dead code.

### 6. Package / Module Placement Pressure

* **God-Package Risk in `runtime/`**:
  * *Evidence*: `src/toas/runtime/` has swollen to 54 files, mixing core semantic domains (e.g. backend lifecycle, policy) with transport, rendering, and edge glue.
  * *Distorted Force*: `Runtime Ownership`.
  * *Follow-Up*: Tracked under `260615-runtime-package-growth-boundary-audit`.
* **Root-Level `tasks.py`**:
  * *Evidence*: `src/toas/tasks.py` contains 28KB of task capture/routing logic but lives at the root package level rather than inside a dedicated capability or runtime directory.
  * *Distorted Force*: `Capabilities`.
  * *Follow-Up*: Rehome task thread capture logic to a more specific package boundary.

### 7. Parked Feature Ideas (Should Stay Parked)

* **Cross-Process Backend Identity & Watchdog loops**:
  * *Evidence*: `260614-backend-lifecycle-cross-process-identity` and `260614-shell-owned-backend-lifecycle` are correctly parked; local model serving process supervision is the current limit, and extending this to remote/pre-started instances is parked.
  * *Distorted Force*: `Model Backend Lifecycle`.

## Known Facts

- `260615-runtime-package-growth-boundary-audit` covers the narrower
  `runtime/` module-to-domain map.
- `260614-legacy-and-fidelity-adapter-precedence` covers legacy and
  fidelity-lowering adapter vocabulary.
- Several current tasks were born from finding fiction in architecture wording,
  especially around backend lifecycle and activity replay.

## Unknowns

- Which current surfaces are most misleading relative to the force map.
- Whether the highest-value next work is naming, documentation, module
  placement, or tests.
- How much of the remaining mismatch is historical text versus live code shape.

## Evidence

- `[x]` a first alignment inventory exists
- `[x]` each entry names the distorted force and current evidence
- `[x]` follow-ups are split only where they are bounded alignment work
- `[x]` speculative feature ideas are marked as parked instead of promoted
