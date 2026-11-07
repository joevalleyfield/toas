Filed as: 261107-intra-turn-policy-mutation-staleness
FKA:
AKA: /shell allow in-flight staleness; stale effective grants; chained slash command policy race; intra-step policy propagation
Legacy index:

keywords: policy, runtime, operator, shell, slash-command, in-flight, staleness, active

Related: `261107-branch-isolated-policy-state`; `260920-effective-policy-provenance-inspection`

# Intra-Turn Policy Mutation Staleness and Staged Execution Failure

## Intent

Ensure that operator policy mutations (e.g. `/shell allow <grants>`, `/shell remove`, `/shell reset`) take effect immediately in the runtime execution environment so that:
1. The rendered operator feedback displays accurate post-mutation effective grants rather than pre-mutation state.
2. Subsequent intent candidates chained within the same turn (such as `/shell allow uv jj` followed by `/run p1.o4..`) execute against the updated policy rather than failing with false authorization errors.

## Context & Motivation

Demonstrated in the dogfood transcript `.toas/session-20261106-1823-visible-transcript-turn-ids.md` (turns `oscar`/`papa` and `events.jsonl` records 121–127):

When an assistant tool call fails authorization:
```text
[ERROR] shell: tool shell disallows command: uv (override needed; stage in user context to run unbounded)
```
The operator naturally responds in a single turn by granting permission and retrying the staged operation:
```text
/shell allow uv jj

/run p1.o4..
```

During step execution, two distinct bugs occur:

1. **Immediate Feedback / Projection Staleness**:
   In `src/toas/runtime/operator_command_prompt_workspace.py` (`_shell_runtime_mutation_result`), `effective = _shell_effective_grants(...)` is computed against the pre-mutation context *before* the policy update node is built. As a result, the rendered response:
   ```text
   shell grants updated: add uv jj (scope=session)
   effective: awk, cat, echo, find, head, ls, pwd, rg, sed, tail, wc
   ```
   claims the grants were updated, but the `effective:` line shows the stale pre-grant state omitting `uv` and `jj`.

2. **In-Flight Execution Failure Across Chained Candidates**:
   In `src/toas/runtime/step_runtime.py` (`_handle_user_or_control_frontier`), the loop over intent candidates only applies `config_update` to live state:
   ```python
   for node in consequences[consequence_start:]:
       config_update = node.get("config_update")
       if isinstance(config_update, dict):
           config, live_overrides = _apply_live_config_update(...)
   ```
   It completely ignores `policy_update` / `policy_updates`! The policy override record is only appended to `events.jsonl` at the end of the entire step in `session_step_edges.py: _apply_policy_updates`.
   When candidate 2 (`/run p1.o4..`) executes in `source_reference_operations.py`:
   ```python
   shell_allowed_commands=step_mod.resolve_effective_shell_allowed(context.working, context.config, context.events)
   ```
   `context.events` does not contain the in-flight policy override, so the retry immediately fails with the identical `disallows command: uv` authorization error.

## In Scope

- Fix `_shell_runtime_mutation_result` (and any related policy command handlers) to compute `effective:` grants reflecting the post-mutation state.
- Update `step_runtime.py` to propagate in-flight `policy_update` / `policy_updates` into the active step context and working event set so subsequent intent candidates in the same turn see the mutated policy.
- Ensure durable persistence semantics in `events.jsonl` remain unchanged and replay-safe.
- Add targeted tests verifying:
  - `/shell allow` reports post-mutation effective grants in its text output.
  - Chained `/shell allow <cmd>` + `/run ...` in the same user turn successfully authorizes and runs the target command without requiring an intermediate turn.

## Out of Scope

- Changing policy persistence schemas or event kinds in `events.jsonl`.
- Redesigning the policy hierarchy or scope model.
