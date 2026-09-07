Filed as: 260907-known-to-target-promotion
FKA:
AKA: promote known model; derived target names; bulk target materialization
Legacy index:

Parent: `260907-endpoint-target-acceptance`
Depends on: `260907-endpoint-target-acceptance`
Blocks: `260907-endpoint-bootstrap-workflow`
Blocked by:
Related: `docs/notes/2026-09-06-endpoints-models-and-targets.md`

keywords: config, runtime, surface, implementation, active, usability, contract

# Promote Known Models Into Named Targets

Make the transition from endpoint-associated known model IDs to durable named
targets convenient without implying live availability or changing selection.

## Contract

- `/config target add ENDPOINT MODEL` derives a deterministic target ID.
- `/config target add NAME ENDPOINT MODEL` remains the explicit alias form.
- Existing target IDs are never overwritten by derived or bulk promotion.
- `/config target add --all-known ENDPOINT` promotes the durable known catalog.
- `--preview` reports planned additions without mutation.
- Bulk promotion is one atomic config update and never probes the network.
- Empty catalogs explain how to refresh the endpoint first.

## Allowed Write Surfaces

- `src/toas/runtime/operator_command_config_help.py`
- `src/toas/config_overrides.py` only if merge semantics require it
- focused operator/config tests
- acceptance coverage for known-to-target promotion

## Progress Evidence

Closed: implemented derived target naming and bulk promotion from the durable
known-model catalog. The explicit named form remains available; derived names
are deterministic, collisions are rejected, `--preview` is read-only, and
bulk writes are emitted as one atomic config update without network access.

Verification: focused operator/config tests passed (229); acceptance coverage
passed (4); full suite passed (3,205 passed, 13 deselected, 100% coverage);
Ruff reported no findings.
