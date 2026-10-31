Filed as: 261030-namespaced-config-policy-coalescence
FKA:
AKA: namespaced policy unification; config policy coalescence; unified config provenance
Legacy index:

keywords: runtime, policy, config, namespaced, provenance, grants, model, unification, operator-ux

Parent: 260920-branch-projected-policy-program
Depends on: 261030-unified-scoped-policy-engine
Blocks: 260920-effective-policy-provenance-inspection
Blocked by:
Related: 260830-exec-grant-policy-matchers; 260920-effective-policy-provenance-inspection

# Coalesce Scoped Policy into Namespaced Configuration Tree

Complete the unification of the scoped policy engine by fully absorbing model target
selection and shell grants into the namespaced configuration tree, retiring parallel
internal policy buckets, and elevating `/config show [topic] [--sources]` to be the
authoritative, provenance-aware policy inspection surface.

## Current Reality & Architectural Tension

1. **Bespoke Internal Buckets**:
   While `261030-unified-scoped-policy-engine` unified durable event logging into
   `policy_override(key, scope, action, value)`, `active_policy_state()` immediately
   diverted execution into three parallel internal buckets:
   - `shell_grants: dict[str, dict[str, set[str]]]`
   - `scalars: dict[str, dict[str, Any]]` (specifically for `llm.target`)
   - `config_overrides: dict` (via `deep_merge`)
   Consumers still call distinct projection helpers (`active_shell_scope_grants`,
   `active_target_selection`, `active_config_overrides`).

2. **Schema & Config Command Blindness**:
   `llm.target` and `shell.allowed` remain outside `OperatorConfig` and
   `valid_config_keys()`. As a result, `/config show` is blind to active model
   targets and shell grants.

3. **Opaque Provenance**:
   `/config show --sources` stamps any session override with a flat, monolithic
   `[source=session_override]`, omitting the winning scope tier and source message ID
   (`n...`), while using an obsolete hardcoded precedence ladder in its footer.

4. **Programmatic Grants on the Horizon**:
   Upcoming programmatic policy programs (e.g. `260830-exec-grant-policy-matchers`)
   need to be referenced by name or module path (`execution.authority.program = "..."`)
   without introducing yet another parallel authority engine.

## Desired Reality

1. **First-Class Namespaced Keys**:
   - `llm.target`: registered as an explicit scalar config key in the schema.
   - `shell.allowed`: registered as a collection config key with set semantics
     (`add`, `remove`, `unset`, `reset`).
   - `/model select` and `/shell add/remove` remain high-frequency ergonomic syntactic
     sugar that emit `policy_override` records for these canonical keys.

2. **Unified Policy Reducer**:
   - `active_policy_state(events)` produces a single cohesive reduction over all keys
     through the 5-tier scope hierarchy (`transient > session > workspace > user > global > defaults`).
   - For every key, the reduction preserves its resolved value, winning scope, and
     source provenance (source message ID `n...`, config load resolution ID, or config file path).
   - Retires the internal branching into bespoke `shell_grants` and `scalars` dictionaries.

3. **Authoritative Provenance Inspection**:
   - `/config show [topic] [--sources]` becomes the single, complete inspection surface.
   - Values show their exact winning scope and contributing message ID or file path:
     ```text
     llm.target = sonnet                  [source=session (n2)]
     shell.allowed = [cat, echo, pytest]   [source=session (n3)]
     shell.assistant_timeout_s = 9         [source=session (n2)]
     generation.max_tokens = 4096         [source=/path/to/toas.toml]
     ```
   - Topic views (`/config show shell`, `/config show models`) naturally display their
     effective scoped state.

4. **Programmatic Policy Readiness**:
   - Storing programmatic authority policies by reference (e.g. `authority.program = "..."`)
     requires no architectural modifications—it is just another namespaced key in the 5-tier tree.

## Acceptance Criteria

- [x] `shell.allowed` and `llm.target` are recognized as first-class keys in the configuration schema and `valid_config_keys()`.
- [x] `active_policy_state()` reduces all keys through the 5-tier scope hierarchy into a unified state structure containing resolved values, winning scopes, and source message provenance.
- [x] Retires the three internal buckets in `active_policy_state()`; consumer modules query unified policy state.
- [ ] `/config show --sources` renders the winning scope and source message ID (or config file / default) for all keys.
- [ ] `/config show [topic]` displays the unified effective policy for that topic (including shell grants and model selections).
- [ ] `./scripts/check.sh` passes at 100.00% statement coverage across all tests.
