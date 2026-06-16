Filed as: 260614-retire-local-suffix-naming-inversion
FKA:
AKA: _local suffix; naming inversion; run_step_local; local_request_ops; cli_local_commands
Legacy index:

keywords: runtime, refactor, active, naming, cli, local, daemon, smell, conventions

# Retire Local Suffix Naming Inversion

## Problem

The `_local` suffix was introduced when the daemon was the primary execution path and local execution was the fallback. It marked the fallback variant.

Since the local-first flip (T534/T540), local execution is the default and the daemon is optional. The naming now encodes the old mental model: the primary implementation carries an apologetic suffix while the thin RPC-routing wrapper has the clean name.

The suffix has also spread into module names (`cli_local_commands`, `local_request_ops`) where it means "not-daemon-facing" rather than "fallback," creating two different semantics for the same qualifier.

## Desired Reality

The qualifier belongs on the variant, not the default. Primary implementations should have clean names. RPC-augmented wrappers, if they survive at all, should carry a suffix or be inlined.

## Scope

- `[x]` Audit and classify all uses of `_local` as a suffix or module name component
- `[x]` Rename/refactor primary implementations to drop the suffix completely
- `[x]` Update module names where the suffix has leaked
- `[x]` Update all callers and tests
- `[x]` Verify build, test suite, and 100% statement coverage

## Completion Summary

All qualifiers representing the default/primary execution path (both `_local` and `_direct`) have been completely retired. Modules, variables, helper functions, and tests have been renamed to their clean, qualifier-free forms, and the entire test suite is green with 100% statement coverage.

## Status

Closed.
