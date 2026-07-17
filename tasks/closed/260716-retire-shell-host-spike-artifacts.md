Filed as: 260716-retire-shell-host-spike-artifacts
FKA:
AKA: remove shell-host spike; preserve stdio spike breadcrumb
Legacy index:

keywords: tooling, implementation, historical, maintainability, runtime, shell, stdio, cleanup

# Retire Shell-Host Spike Artifacts

Parent: `260614-architecture-follow-through-coordination`
Related: `260614-shell-owned-backend-lifecycle`; `260614-backend-lifecycle-cross-process-identity`

## Goal

Remove the unsupported zsh shell-host spike and its real-process integration
test from the current tree while preserving an obvious VCS breadcrumb for
future retrieval.

## Why

The spike has served its purpose and its findings are recorded durably. Keeping
the executable specimen in-tree would create avoidable maintenance and test
cost around a deliberately non-product `coproc` approach with known signal,
stderr-inheritance, and singleton-slot limitations.

## Scope

- Record the specimen commit and a direct `jj restore` recipe in the closed
  shell-host task.
- Update adjacent evidence wording so it does not imply the specimen remains
  in the current tree.
- Remove `spikes/shell_host_stdio/`.
- Remove `tests/test_spike_shell_host_stdio.py`.
- Leave runtime code and supported CLI surfaces unchanged.

## Evidence

- [x] Closed task identifies specimen commit `508549c5` and retrieval command.
- [x] Unsupported spike and integration test are absent from the current tree.
- [x] Task inventory and ordinary test suite remain green.
- [x] Roadmap and manual workboard were skimmed and intentionally left
      strategically unchanged.

## Resolution: 2026-07-16

- Removed `spikes/shell_host_stdio/` and
  `tests/test_spike_shell_host_stdio.py` from the current tree.
- Added the exact specimen commit and `jj restore` recipe to
  `260614-shell-owned-backend-lifecycle`.
- Updated the adjacent cross-process disposition so it points to the durable
  task evidence and specimen commit instead of an in-tree spike path.
- Verified commit `508549c5` contains all four removed files with
  `jj file list`.
- Verified `tests/test_tasks_capture.py`: 33 passed.
- Verified the ordinary suite: 2716 passed, 9 deselected, 100% coverage.
