## Goal

Freeze behavior boundaries and add compatibility seam locks so later module movement under `400` stays parity-safe.

## Why Now

Decomposition without explicit boundary locks risks silent drift across CLI/runtime/transcript contracts.

## Scope

- document externally visible entry points that must remain stable across extraction:
  - CLI command surfaces
  - runtime step semantics
  - daemon RPC op contracts
  - tool registry callable contracts
- add/extend contract tests for high-risk flows before movement
- add lightweight compatibility import shims where extraction is expected to move symbols
- define rollback checks for each moved cluster (imports + behavior tests)

## Boundary Inventory (Phase-0 Freeze)

- CLI command surface (must remain stable during decomposition):
  - `toas step [--async]`
  - `toas watch <run_id> [--offset <n>] [--follow]`
  - `toas cancel <run_id>`
  - `toas backend [status|start|stop|restart]`
  - `toas jump <index>`
  - `toas head <node_id>`
  - `toas heads`
  - `toas transcript [head_id]`
  - `toas llm-input [head_id]`
  - `toas prompt <ref> [--mode <direct|mimic>] [--constraint <name> ...]`
  - `toas prompts [prefix]`
  - `toas history [limit]`
  - `toas rebuild [head_id]`
  - `toas ancestry <message_id> [--depth <n>] [--full]`
  - `toas diff <head_a> <head_b> [--full]`
  - `toas index rebuild`
  - `toas daemon [start|stop|status]`
- Daemon RPC op contracts:
  - `status`, `step`, `step_async`, `step_async_warm`, `step_async_cold`, `watch`, `cancel`
  - `backend_status`, `backend_start`, `backend_stop`, `backend_restart`
  - `heads`, `history`, `transcript`, `llm_input`, `rebuild`, `jump`, `head`, `diff`, `ancestry`, `index_rebuild`
- Tool callable contracts:
  - `REGISTRY` keys and required argument shapes remain stable for current call lanes
  - `validate_call` / `execute_call` preserve current error contracts for unknown tool / missing args

## Intended Behavior

- later extraction slices can move code without changing user-visible semantics
- failures from movement show up as deterministic contract-test failures

## Constraints

- no large structural movement in this task
- focus on behavior locks and compatibility scaffolding only
- keep history/transcript invariants unchanged

## Done When

- boundary inventory is captured in task notes and reflected in tests
- compatibility seams exist for first planned extraction clusters
- parity checks pass with full test suite

## Progress

- added phase-0 boundary inventory above as decomposition freeze target
- added contract-lock tests for daemon op-handler/payload-validator maps and core tool callable contracts
