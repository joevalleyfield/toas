# Config Precedence and Sequencing Contract

Status: Normative contract for the ordinary config lane (as of 2026-09-20).

This document defines the precedence model, timing semantics, and operation
classes for the ordinary `OperatorConfig` lane. It does not define one global
precedence ladder for transcript control records, child-process environment, or
TOAS host/bootstrap environment. Those domains are covered by the [Transcript
Control State And Resolution Contract](2026-09-20-transcript-control-state-contract.md).

## Intent

Within this lane, TOAS converges toward a precedence model where the most
immediate, intentional operator action wins over broader defaults. The ladder
is a source order for ordinary config values, not a claim that every runtime
policy resolves in the same order.

## Precedence Ladder

Effective config settings are resolved in the following order of precedence (highest to lowest):

1. **Ephemeral Runtime Secrets** (highest)
   - In-memory only (e.g. `/config secret set llm_api_key <value>`).
   - Does not persist across runs, but takes priority for the active process/daemon lifetime.
2. **Session Durable Overrides**
   - Recorded as `config_override` records in durable history (e.g. via
     `/config set`, `/config load`, `/config unset`, `/config restore`). The
     contract is to resolve them against the selected message lineage. Some
     current reducers still receive the full journal and therefore behave
     history-forward; that implementation gap is tracked in the companion
     control-state contract.
   - These persist in `events.jsonl` and are rebuilt dynamically.
3. **Local Project Config File**
   - Loaded from `./toas.toml` (highest file precedence) or `./.toas/config.toml`.
4. **Global Config File**
   - Loaded from `~/.toas.toml` or `~/.config/toas/config.toml`.
5. **Process Environment Variables**
   - Fallback compatibility variables for keys whose resolver admits them
     (e.g., `TOAS_LLM_BASE_URL`, `TOAS_LLM_MODEL`). This is not a blanket
     endorsement of `TOAS_*` variables as configuration knobs.
6. **In-Code Defaults** (lowest)
   - Hardcoded fallback settings defined within the policies.

For a rewritten transcript branch, the session-override layer is not a
journal-wide bucket. It is the ordered config-delta overlay visible on the
selected branch, evaluated from that branch's message LCP through the selected
operation. The current user/project file result remains the ordinary baseline.
See [LCP policy reevaluation](2026-09-20-transcript-control-state-contract.md#transcript-control-deltas-and-lcp-reevaluation)
for the branch rule, including immutable reconstitution of a prior config-load
result versus an explicit fresh load.

## Operation Classes

Configuration actions belong to one of three distinct classes:

| Class | Command Example | Timing | Durability |
| :--- | :--- | :--- | :--- |
| **Durable Session Override** | `/config set key val`<br>`/config load [path]`<br>`/config unset key`<br>`/config restore` | Evaluated relative to frontier consequence execution. Recorded when the step completes. | Durable in `events.jsonl`; lineage-scoped by contract. |
| **Ephemeral Runtime Secret** | `/config secret set key val` | Applies immediately in-process. | Ephemeral (lost on restart). |
| **Side Effect Export/Save** | `/config save [path]` | Executed immediately as a file write. | Saved to local `.toml` file. |

## Timing Semantics

When a config command (like `/config set`) is executed inside a transcript step:
1. The command is evaluated as a candidate intent during frontier consequence execution.
2. It returns a result node containing a `config_update` payload.
3. During execution of the *same* step's subsequent commands (in the same turn), the running config is updated in-memory so downstream commands see the new setting immediately.
4. When the step completes, the update is committed as a `config_override` record in the event log.
5. In all subsequent steps, this override is resolved from the selected
   lineage. Implementations must not silently use the storage tip when an
   explicit branch or head was requested.

## Scope boundary

This contract covers ordinary config values that can be represented by
`OperatorConfig` and its file/session override lane. It does not settle:

- shell grants, workspace/command context, target or surface selection, and
  other record-specific transcript controls;
- child-process environment profiles, bindings, or transcript `/env` modifiers;
- host/bootstrap, daemon, protocol, test-only, or diagnostic environment
  switches; or
- whether a future full settings checkpoint should project any of the above.

Those controls may be visible in a composite settings view, but such a view
must preserve domain labels, source provenance, and the distinction between a
canonical delta and a derived checkpoint.

## Related

- `466` config sequencing/precedence contract and diagnostics clarity
- `485` shell-lane purpose unification and shared stream-policy handling
- `260920-transcript-control-state-contract` transcript control-state and
  resolution contract
