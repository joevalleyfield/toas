# Config Precedence and Sequencing Contract

Status: Formalized Contract (as of 2026-06-08).

This document defines the authoritative precedence model, timing semantics, and operation classes for the TOAS configuration system.

## Intent

TOAS converges toward a precedence model where the most immediate, intentional operator action wins over broader defaults.

## Precedence Ladder

Effective config settings are resolved in the following order of precedence (highest to lowest):

1. **Ephemeral Runtime Secrets** (highest)
   - In-memory only (e.g. `/config secret set llm_api_key <value>`).
   - Does not persist across runs, but takes priority for the active process/daemon lifetime.
2. **Session Durable Overrides**
   - Recorded as `config_override` records in the durable event graph lineage (e.g. via `/config set`, `/config load`, `/config unset`, `/config restore`).
   - These persist in `events.jsonl` and are rebuilt dynamically.
3. **Local Project Config File**
   - Loaded from `./toas.toml` (highest file precedence) or `./.toas/config.toml`.
4. **Global Config File**
   - Loaded from `~/.toas.toml` or `~/.config/toas/config.toml`.
5. **Process Environment Variables**
   - Fallback variables (e.g., `TOAS_LLM_BASE_URL`, `TOAS_LLM_MODEL`).
6. **In-Code Defaults** (lowest)
   - Hardcoded fallback settings defined within the policies.

## Operation Classes

Configuration actions belong to one of three distinct classes:

| Class | Command Example | Timing | Durability |
| :--- | :--- | :--- | :--- |
| **Durable Session Override** | `/config set key val`<br>`/config load [path]`<br>`/config unset key`<br>`/config restore` | Evaluated relative to frontier consequence execution. Recorded when the step completes. | Durable in `events.jsonl` (lineage-bound). |
| **Ephemeral Runtime Secret** | `/config secret set key val` | Applies immediately in-process. | Ephemeral (lost on restart). |
| **Side Effect Export/Save** | `/config save [path]` | Executed immediately as a file write. | Saved to local `.toml` file. |

## Timing Semantics

When a config command (like `/config set`) is executed inside a transcript step:
1. The command is evaluated as a candidate intent during frontier consequence execution.
2. It returns a result node containing a `config_update` payload.
3. During execution of the *same* step's subsequent commands (in the same turn), the running config is updated in-memory so downstream commands see the new setting immediately.
4. When the step completes, the update is committed as a `config_override` record in the event log.
5. In all subsequent steps, this override is resolved from the lineage.

## Related

- `466` config sequencing/precedence contract and diagnostics clarity
- `485` shell-lane purpose unification and shared stream-policy handling
