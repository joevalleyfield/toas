Filed as: 261109-portable-spill-scratch-paths
FKA:
AKA: portable spill scratch paths; normalize spill paths posix; windows backslash in spill fence; posix scratch rel path
Legacy index:

keywords: active, bugfix, portability, windows, tools, rendering, spill

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

- [ ] Use `.as_posix()` when calculating `scratch_rel_path` in `src/toas/tools_cluster/rendering.py:spill_inert_block` and any companion scratch path formatting helpers.
- [ ] Verify fence info strings, banner text, and footer diagnostic notes use POSIX paths on both POSIX and Windows environments.
- [ ] Add targeted test coverage verifying portable scratch paths on Windows path fixtures while maintaining 100.00% statement coverage.

## Out of Scope

- Changing local filesystem operations (which continue to use standard `Path` objects).

## Acceptance Criteria

1. `scratch_rel_path` in spilled block fences and banners is formatted as `.toas/scratch/<block_id>.txt` across all platforms.
2. Unit and regression tests pass with 100.00% statement coverage on modified modules.
