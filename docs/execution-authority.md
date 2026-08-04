# Assistant Execution Authority

Status: CURRENT

Assistant-addressable shell execution keeps authorization, workspace scope,
cancellation, and execution lifetime as separate concerns. Timeout is not an
authority grant.

## Timeout policy

- `shell` and `shell_script` accept any positive integer `timeout_s` supplied
  on a call. TOAS has no built-in numeric maximum.
- If a call omits `timeout_s`, the runtime injects the effective
  `shell.assistant_timeout_s` value. The in-code default is 5 seconds.
- A per-call timeout overrides the default for that call only.
- Direct user shell intent retains its existing separate timeout semantics and
  does not inherit the assistant default.

The durable session override surface is:

```text
/config set shell.assistant_timeout_s 120
```

The same value can be supplied in project/global TOML:

```toml
[shell]
assistant_timeout_s = 120
```

Inspect the effective value and provenance with:

```text
/config show --sources
```

Remove only the durable session override with:

```text
/config unset shell.assistant_timeout_s
```

`capability_help` topic `shell` reports the effective default, its source, and
the fact that explicit positive timeouts have no numeric ceiling.

## Constraint audit

| Constraint | Current owner/evidence | Safety purpose | Disposition |
| --- | --- | --- | --- |
| Default and maximum timeout | `config.py::ShellPolicy`, `runtime/step_runtime.py`, `tools_cluster/execution.py`, `tools_cluster/shell_ops.py` | Bound omitted calls while allowing intentional long work | Change: configurable omitted-call default; remove numeric maximum |
| Timeout termination and descendant cleanup | `tools_cluster/shell_ops.py`, `tools_cluster/shell_streaming.py` | Ensure the directly owned subprocess reaches a terminal timeout result | Keep direct-child cleanup and terminal result behavior. Arbitrary detached descendants are not promised by this lane |
| Assistant command allowlist and grants | `step.py::resolve_effective_shell_allowed`, `shell_grants.py`, `tools.py::shell_allow_policy` | Prevent timeout from becoming command authority | Keep |
| Workspace/cwd boundaries | `tools.py::workspace_policy`, `tools_cluster/shell_ops.py` | Restrict assistant file/process scope to configured roots | Keep |
| `shell` versus `shell_script` syntax | Tool registry plus `shell_ops.py` validation | Keep argv execution distinct from scripts/operators and validate each shape | Keep |
| Environment mutation/inheritance | `tools_cluster/execution.py`, `shell_ops.py`, runtime env modifiers | Make environment additions explicit while retaining required process environment | Keep |
| Buffered versus streaming execution | `runtime.streaming_mode`, `TOAS_STREAM_STDOUT`, `shell_streaming.py` | Preserve progress/liveness without changing command semantics | Keep; long timeouts do not require a separate authority tier |
| Host/RPC request lifetime versus command lifetime | async start returns a run id; subscribe/watch requests use independent observation timeouts | A carrier/read deadline must not claim that the activity was killed | Keep separation; terminal activity state is authoritative |
| Staging into direct user intent | assistant shell authorization projection in `runtime/step_runtime.py` | Escalate missing command authority, not arbitrary timeout policy | Change: timeout alone never causes staging; authorization staging remains |
| Platform launcher/process behavior | `shell_ops.py`, `shell_streaming.py`, session-host/daemon process lifecycle tests | Preserve Windows/POSIX launch and terminal cleanup behavior | Keep current platform adapters and tests |

## Lifecycle guarantees

- Ordinary tool failure and timeout produce one terminal tool result.
- Timeout results are marked indeterminate by plan recovery because the caller
  must not infer domain-level completion from transport/process timing alone.
- Async cancellation remains owned by activity lifecycle and converges on one
  terminal activity state.
- Async transport subscription deadlines are observational. They do not
  terminate the underlying activity or rewrite its terminal state.
