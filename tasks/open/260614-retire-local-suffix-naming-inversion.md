## Goal
Filed as: 260614-retire-local-suffix-naming-inversion
FKA:
AKA: _local suffix; naming inversion; run_step_local; local_request_ops; cli_local_commands
Legacy index:

keywords: naming, refactor, cli, local, daemon, smell, conventions

## Problem

The `_local` suffix was introduced when the daemon was the primary execution path and local execution was the fallback. It marked the fallback variant.

Since the local-first flip (T534/T540), local execution is the default and the daemon is optional. The naming now encodes the old mental model: the primary implementation carries an apologetic suffix while the thin RPC-routing wrapper has the clean name.

The suffix has also spread into module names (`cli_local_commands`, `local_request_ops`) where it means "not-daemon-facing" rather than "fallback," creating two different semantics for the same qualifier.

## Desired Reality

The qualifier belongs on the variant, not the default. Primary implementations should have clean names. RPC-augmented wrappers, if they survive at all, should carry a suffix or be inlined.

## Scope

- Audit all uses of `_local` as a suffix or module name component
- Distinguish: does it mean "fallback," "direct," "not-RPC," or "not-daemon-facing"?
- Rename primary implementations to drop the suffix
- Rename or inline the RPC-routing wrappers
- Update module names where the suffix has leaked (`cli_local_commands`, `local_request_ops`)
- Update all callers and tests

## Dependencies

Should follow T400 decomposition work — wait until module boundaries are stable before renaming across them.

## Done When

No production symbol uses `_local` to mean "primary implementation" or "default path."
