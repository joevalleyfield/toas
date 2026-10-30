Filed as: 261030-unified-scoped-policy-engine
FKA:
AKA: unified policy lifecycle; scoped policy consolidation; control state lifecycle unification
Legacy index:

keywords: runtime, policy, config, grants, model, scope, lifecycle, unification, transcript, session-rotation

Parent: 260920-branch-projected-policy-program
Depends on: 260920-branch-projected-policy-program
Blocks:
Blocked by:
Related: 260920-transcript-control-state-survey, 260920-effective-policy-provenance-inspection, 261030-post-generation-yaml-canonicalization

# Unified Scoped Policy Engine

Consolidate the fragmented operator policy surfaces (`/shell`, `/model`, `/config`, `/cd`)
and their bespoke event representations (`shell_scope_grant`, `target_selection`,
`config_override`, `command_context`) into a single, symmetrical 5-tier scoped policy engine.

## Current Reality & Status Quo

In September 2026, `260920-transcript-control-state-survey` and `260920-branch-projected-policy-program`
established branch-forward policy evaluation and source-linked records. However, Phase 2
intentionally preserved each domain's bespoke event types and reducers:

1. **`/shell`**: Uses an explicit 6-tier scope hierarchy (`transient > session > head > workspace > user > global > defaults`),
   emits `shell_scope_grant` events, and has bespoke rotation re-serialization in `session_rotation.py`.
2. **`/model`**: Uses `/model select <target>` or `/model select <endpoint> <model>`, emits `target_selection`
   events, and uses a bespoke branch-scanning reducer (`_branch_visible_target_selection`). Active selections
   are currently dropped entirely on session rotation (`/continue`).
3. **`/config`**: Uses `/config set <key> <value>`, emits `config_override` records with raw `deep_merge`,
   and has no explicit scope parameter or rotation re-serialization.
4. **`/cd`**: Emits `command_context` records recording `cwd`, reduced separately from configuration.

### Problems & Costs of the Status Quo

- **Combinatorial Integration Tax**: Every transcript-level operator (session rotation, transcript compaction,
  branch jump/rebuild, salvage, inspection) must write bespoke adapter logic for every distinct event kind.
- **Leaky Rotation**: Session rotation carries forward shell grants, but silently drops active model target
  selections and runtime configuration overrides.
- **Redundant Scopes**: Scope `head` in `/shell` is an artificial VCS concept that adds cognitive load and
  implementation branches without fulfilling an actual operator need (graph parentage already isolates
  branch state).

## Confirmed Direction

1. **Prune Scope `head` to Establish a Clean 5-Tier Hierarchy**:
   ```text
   Runtime / Temporal:
     1. transient  → in-memory; expires after immediate next step
     2. session    → working transcript (session.md); default for interactive commands

   Persistent / File-Backed:
     3. workspace  → .toas/config.toml (project repository)
     4. user       → ~/.config/toas/config.toml (operator machine)
     5. global     → built-in system defaults
   ```
   No bespoke VCS scope (`head`)—graph ancestry (`related_to: message_id`) already provides branch isolation.

2. **Unified Event Representation (`policy_override`)**:
   Collapse bespoke control event kinds (`shell_scope_grant`, `target_selection`, `config_override`)
   into a single durable shape:
   ```json
   {
     "kind": "policy_override",
     "related_to": "msg_...",
     "payload": {
       "key": "llm.target",
       "scope": "session",
       "action": "set",
       "value": "sonnet"
     }
   }
   ```
   - Scalar keys support actions: `set`, `unset`.
   - Set/membership keys (like `shell.allowed`) support actions: `add`, `remove`, `unset`, `reset`.

3. **Preserve High-Frequency Surface Verbs as Syntactic Sugar**:
   Existing frontend verbs remain untouched for ergonomic comfort:
   - `/model select <target>` sugar for `policy_override(key="llm.target", action="set", value=target, scope="session")`
   - `/shell add <cmd>` sugar for `policy_override(key="shell.allowed", action="add", value=cmd, scope="session")`
   - `/config set <key> <val>` sugar for `policy_override(key=key, action="set", value=val, scope="session")`

4. **Zero-Glue Session Rotation**:
   Rotating a transcript (`/continue`) executes a generic delta query:
   *Gather all active policy overrides at scope `session` on the current branch.*
   Serializes them into the successor's opening `## TOAS:CONTROL` preamble:
   ```markdown
   ## TOAS:CONTROL

   /model select sonnet
   /shell add pytest uv
   /config set runtime.streaming enabled
   ```

## Gaps & Further Research

1. **Namespaced Key Taxonomy**:
   Formalize the canonical dot-notation keys for all policy surfaces:
   - `llm.target`
   - `shell.allowed`
   - `workspace.cwd`
   - `runtime.<policy_field>`
2. **Legacy Compatibility & Reading Boundary**:
   Existing `events.jsonl` files contain legacy `target_selection`, `shell_scope_grant`, and `config_override` records.
   The unified reducer should normalize these legacy shapes into the canonical policy state in memory,
   while writing only `policy_override` going forward.
3. **Coordination with `260920-effective-policy-provenance-inspection`**:
   Unifying the policy engine will simplify effective-policy inspection by providing a single query interface
   that explains which scope tier and source event won for any given key.
