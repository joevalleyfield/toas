Filed as: 261109-portable-spill-scratch-paths
FKA:
AKA: portable spill scratch paths; normalize spill paths posix; windows backslash in spill fence; posix scratch rel path
Legacy index:

keywords: historical, bugfix, portability, windows, tools, rendering, spill

Related: `261106-content-spillage-refinement`; `261015-windows-compatibility-restoration`; `261109-runtime-spill-policy-binding`

# Portable POSIX Scratch Paths in Spill Fences and Banners

## Intent

Ensure relative scratch paths emitted in spilled inert block banners, fences, and footers consistently use portable POSIX forward slashes (`.toas/scratch/...`) across all platforms, including Windows.

## Context & Motivation

In `src/toas/tools_cluster/rendering.py`, `spill_inert_block()` computes:

```python
scratch_rel_path = str(target_dir.resolve().relative_to(Path.cwd().resolve()) / f"{effective_block_id}.txt")
```

On Windows, native `Path.__str__` uses backslashes, resulting in banners and fence attributes like:

```text
path=".toas\scratch\ib_6495caa99f96e253.txt"
```

and:

```text
[20 lines remaining. ... path=".toas\scratch\ib_6495caa99f96e253.txt"]
```

This leaks platform-specific backslash path separators into transcript history, fence annotations, and model prompts. All inert fence path metadata and reference notations in TOAS are specified to be portable POSIX paths.

## In Scope

- [x] Use `.as_posix()` when calculating `scratch_rel_path` in `src/toas/tools_cluster/rendering.py:spill_inert_block` and any companion scratch path formatting helpers.
- [x] Verify fence info strings, banner text, and footer diagnostic notes use POSIX paths on both POSIX and Windows environments.
- [x] Add targeted test coverage verifying portable scratch paths on Windows path fixtures while maintaining 100.00% statement coverage.

## Out of Scope

- Changing local filesystem operations (which continue to use standard `Path` objects).

## Acceptance Criteria

1. `scratch_rel_path` in spilled block fences and banners is formatted as `.toas/scratch/<block_id>.txt` across all platforms.
2. Unit and regression tests pass with 100.00% statement coverage on modified modules.


## Completion evidence

Spill projection converts the workspace-relative scratch path to POSIX form
at the rendering boundary. The banner, fence attributes, footer, and preview
diagnostics share that rendered path. The scratch file is still written via
the native filesystem path.

The public renderer regression exercises both native and Windows-style
relative paths while verifying the scratch file contents. The focused
rendering, spill, and skill suites passed 103 tests with 100% statement
coverage of the renderer. A local `toas step` reading a 70-line file showed
the same `.toas/scratch/<block_id>.txt` in the banner, fence, and footer,
and the referenced file contained the complete result.

The full project suite passed 4,069 tests with nine skips and 100% statement
coverage. All 17 acceptance tests, Ruff, and mypy passed.
