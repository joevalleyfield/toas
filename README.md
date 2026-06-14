# TOAS

TOAS is a transcript-oriented operator over durable history.

It exists in part to make a locally available but behaviorally awkward model usable through stronger operator semantics, durable state, and better control over prompting, tool use, and replay.

The system is built around three things:
- `session.md` (default): the user-controlled working transcript
  - configurable via `.toas/config.toml` (or `toas.toml` compatibility path) as `[session] transcript_path = ".toas/session1.md"`
- `.toas/events.jsonl` (default): append-only durable state
  - compatibility fallback: root `events.jsonl` is still honored when present
- `toas step`: a one-step operator that accepts transcript state and resolves one layer of consequence

It is not a hidden conversation loop. It is a small operator runtime over a message graph plus related operator records.

## Current Features

- graph-native message history with branching
- durable control records for operator provenance and projection support
- frontier-authoritative `step` with explicit `/replay` for non-frontier callable selection
- local OpenAI-compatible generation
- registry-backed tool execution
- versioned prompt assets
- metadata-backed session-starting prompt family
- dynamic capability-advertisement prompts
- transcript projection, rebuild, and history inspection commands

## CLI

- `toas step`
  Accept transcript edits, append new durable state, and print only newly produced consequences.
  If the frontier message ends with a line of the form `$ some_shell_command`, TOAS executes that command as an explicit user shell action and prints its result as a `RESULT` block.
  Session target can be selected per call with `--session <transcript_path>`.
- `toas step --async`
  Start one step asynchronously and return a `run_id`.
- `toas watch <run_id> [--offset <n>] [--follow]`
  Read incremental output for an async run.
- `toas cancel <run_id>`
  Request cancellation for an async run.
- `toas heads`
  List known lineage heads.
- `toas transcript [head_id]`
  Print a transcript projection; explicit node/head targeting is read-only projection and does not affect subsequent `step` execution.
- `toas llm-input [head_id]`
  Print model-facing projected messages; explicit node/head targeting is read-only projection and does not affect subsequent `step` execution.
- `toas prompt <ref> [--mode <direct|mimic>] [--constraint <name> ...]`
  Print a named prompt asset so it can be inserted explicitly into the transcript.
- `toas prompts [prefix]`
  Browse prompt assets (including composed template assets) and one-line descriptions by library prefix.
- `toas history [limit]`
  Print recent event summaries and head listings for inspection.
- `toas rebuild [head_id]`
  Rewrite the configured transcript working file from projected history and emit a useful anchor.
- `toas daemon [start|stop|status]`
  Manage the local `toasd` process used for RPC-backed stepping.
- `toas host serve [--owner-pid <pid>]`
  Run a session host tied to an owner process lifecycle.
  Optional `--session <transcript_path>` sets the host-default transcript surface.
- `toas host stop [--workdir <path>] [--owner-kind <editor|shell>] [--owner-id <id>]`
  Stop and clear the recorded session host for a workdir. If owner filters are provided
  (or `TOAS_OWNER_KIND` / `TOAS_OWNER_ID` are set), stop is conditional on owner identity match.
- `toas replay-script <script_path> [--output <path>] [--dry-run]`
  Run append-first progressive replay scripts and emit artifact snapshots (`steps`, `events_tail`, `session_tail`).

`toas` commands can be routed through daemon RPC using `TOAS_RPC_MODE`:

- `TOAS_RPC_MODE=auto` (default): prefer RPC when daemon endpoint exists, fallback to local
- `TOAS_RPC_MODE=on`: require RPC path, fallback only on RPC error
- `TOAS_RPC_MODE=off`: always run local path

`step --async`, `watch`, and `cancel` are local-first async lifecycle surfaces.
Explicit compatibility opt-back remains available via `TOAS_ASYNC_BACKEND_MODE=rpc`.

Session/transcript selection precedence for step execution (informative):
1. explicit step request/session override (`--session`, async payload `session_path`/`session`)
2. host default (`toas host serve --session ...`)
3. durable selected surface mapping
4. config transcript path (`session.transcript_path`)
5. fallback `.toas/session.md`

Step execution contract:
- `step` resolves from current transcript frontier only.
- Only current frontier content (`user`/`assistant`/`control`) can select what executes next.
- `/replay` is the explicit mechanism for selecting historical non-frontier callable content.
- There is no hidden selector state that may redirect step away from transcript frontier.

## Operating Modes

### 1. CLI-pure local mode (no daemon)

Use this when you want deterministic local execution with no RPC path.

```bash
TOAS_RPC_MODE=off uv run toas step
```

You can also set it for a shell session:

```bash
export TOAS_RPC_MODE=off
```

### 2. Daemon-backed CLI mode

Use this when you want normal `toas` commands to prefer daemon RPC and keep local fallback behavior.

```bash
uv run toas daemon start
TOAS_RPC_MODE=auto uv run toas step
uv run toas daemon status
```

To bias hard toward RPC while still falling back on explicit RPC errors:

```bash
TOAS_RPC_MODE=on uv run toas step
```

For async lifecycle commands, you can opt back to RPC compatibility mode explicitly:

```bash
TOAS_ASYNC_BACKEND_MODE=rpc uv run toas step --async
```

### 3. Persistent Vim channel mode

Use this for lowest per-step latency in editor workflows.

```vim
:ToasStep
```

`ToasStep` uses a persistent RPC channel to `toasd` and falls back to `:read !toas step` if needed.

Editor ownership behavior:
- Vim exports `TOAS_OWNER_KIND=editor` and a stable `TOAS_OWNER_ID` for the Vim process.
- On `VimLeavePre`, the plugin runs `toas host stop` in the workspace.
- Because owner identity is exported, host stop only tears down the matching editor-owned host.

## Shell Policy

- A frontier line of the form `$ ...` is treated as explicit user shell intent.
- That user-shell path is not restricted by TOAS command allowlists or workspace fences.
- The registry `shell` tool remains bounded because it is model-addressable capability rather than direct user intent.
- Assistant loose `command:` proposals project as:
  - single-line: `$ ...`
  - multiline: preserved multiline command text (not flattened to one line)
- Multiline user execution uses tail-armed structured command shape (for example tail YAML `command:` / `cmd:` blocks), not `$` plus trailing prose.

### Shell Grant Scopes

`/shell` grant mutations are operational-state updates (durable policy), not transcript-text reconstruction.

Usage:

- `/shell list`
- `/shell add <grant> [--scope <scope>]`
- `/shell remove <grant> [--scope <scope>]`
- `/shell unset <grant> [--scope <scope>]`
- `/shell reset [--scope <scope>]`

Default mutation scope is `session`.

Supported scopes:

- `global`
- `user`
- `workspace`
- `head`
- `session`
- `transient`

Scope semantics:

| Scope | Meaning | Persistence |
| --- | --- | --- |
| `global` | Broad baseline policy intended to apply across TOAS usage. | Durable config-backed layer. |
| `user` | User-level baseline policy across repositories. | Durable config-backed layer. |
| `workspace` | Repository/workdir-local baseline policy. | Durable config-backed layer. |
| `head` | Lineage/head-local policy for a selected branch of history. | Durable graph record layer. |
| `session` | Current working session policy (default mutation target). | Durable graph record layer. |
| `transient` | Highest-priority short-lived override lane for immediate control. | Durable graph record layer (intended as temporary override semantics). |

Effective precedence (highest to lowest):

1. `transient`
2. `session`
3. `head`
4. `workspace`
5. `user`
6. `global`
7. defaults

Examples:

```text
/shell add prefix:jj
/shell add prefix:git --scope workspace
/shell remove echo --scope user
/shell reset --scope transient
```

### Callable Schema

Canonical callable shape:

```yaml
- operation: echo
  intent: describe why this call exists
  params:
    text: hello
```

Compatibility aliases are accepted and normalized:
- `operation` or `tool_name`
- `params`, `args`, or `arguments`
- `intent` or `intention`

For `shell` operations, avoid ambiguous mixes:
- use `params.argv` for explicit argv execution
- or use `params.command` / `params.cmd` string sugar
- do not provide `argv` with `command`/`cmd` in the same call

## Tool Notes

- `capability_help` is a model-addressable, read-only tool for compact capability detail by topic or tool name (`core`, `shell`, `editing`, `debug`, `all`, or a tool name).
- `procedure` loads and runs named reusable procedure assets (for example `repo_discovery_triage_v1`).
- `write_file` explicitly creates or overwrites a workspace file with full provided content.
- `echo_block` echoes multiline payloads with simple diagnostics (`line_count`, `leading_spaces`) for YAML/debug workflows.
- `replace_block` supports optional indentation controls:
  - `search_indent`
  - `replacement_indent`
  These are applied deterministically before match/replace to reduce YAML block-scalar whitespace mismatch failures.
- `get_structure` maps Python `def`/`class` structure for a file or directory (with line ranges).
- `replace_range` replaces an explicit line range in a workspace file.

Example split workflow:
1. Run `get_structure` on a Python file to find target function `start_line`/`end_line`.
2. Run `replace_range` for that span with two new function definitions in `replacement_block`.
   Optional: pass `indent` to left-prefix each non-empty replacement line (for example Python block indentation).
   Optional: pass `context_start` and/or `context_end` to verify boundary lines before replacement.

## Layer Semantics

- `/config` defines operator baseline capability/default space.
- Transcript commands (for example `/model ...`, `/env ...`) define branchable transcript state.
- Capability validation happens at consumption frontier (for example inference step), not at write-time intent capture.
- When selected capability is unavailable at frontier, TOAS emits explicit continuation guidance; it does not silently fallback.

## Selector Commands

- `/prompt [ref_or_prefix]` is the canonical prompt selector:
  - no arg: list top-level prompt namespaces
  - non-leaf prefix: list children
  - leaf ref: render prompt content (fragment or composed template asset)
- `/prompts [prefix]` remains as a compatibility alias.
- `/model [name]`:
  - no arg: list available models from current capability space (catalog first, fallback/defaults after)
  - with arg: set transcript-scoped model intent (validated at inference frontier)
- `/backend [id]`:
  - no arg: list configured backend aliases
  - with arg: set transcript-scoped backend intent (validated at inference frontier)
- `/env` modifiers are transcript-scoped execution-surface deltas:
  - `/env set <KEY> <VALUE>`
  - `/env unset <KEY>`
- `/extract [--verbose] [index]` previews/adopts callable intent from the latest assistant message.
- `/replay [--dry-run] [--index <n>] [--force]` re-executes historical callable intent.
- queue continuation controls for replayed multi-op plans:
  - `/replay --resume <queue_id>`
  - `/replay --approve <queue_id>`
  - `/replay --skip <queue_id>`
  - `/replay --cancel <queue_id>`

## Runtime Defaults

The local model client defaults to:

- `TOAS_LLM_BASE_URL=http://localhost:8080/v1`
- `TOAS_LLM_API_KEY=not-needed`
- `TOAS_LLM_MODEL=qwen3.5-35b-a3b`

That matches a local OpenAI-compatible `llama-cpp` style setup.

## Config Workflow

Use `/config` for in-session overrides and `.toas/config.toml` for project defaults (`toas.toml` remains a compatibility path).

In session:

```text
/config show
/config show --sources
/config set generation.thinking_mode disabled
/config set generation.max_retries 2
/config set generation.retry_delay_s 0.25
/config unset generation.max_retries
/config restore
/config load ./.toas/config.toml
/config save ./.toas/config.toml
/config set runtime.context_budget_mode strict
/config set runtime.streaming_mode enabled
/config set runtime.async_runs enabled
/config set runtime.cancellation_mode enabled
/config set capability_advertisement.profile core
/config set capability_advertisement.hidden_tools echo_block
/config set backend_startup.thinking_budget_tokens 0
/config backend list
/config backend add local http://localhost:8080/v1
/config backend set local.model qwen3.5-35b-a3b
/config backend capture local
```

Project defaults (`.toas/config.toml` preferred, `toas.toml` compatibility):

```toml
[generation]
thinking_mode = "enabled"
max_retries = 2
retry_delay_s = 0.25

[llm]
base_url = "http://localhost:8080/v1"
model = "qwen3.5-35b-a3b"
api_key_source = "env"
api_key_ref = "TOAS_LLM_API_KEY"

[[llm.models]]
id = "qwen3.5-35b-a3b"
label = "Qwen Local"
tags = ["local", "fast"]
notes = "default local loop"

[[llm.models]]
id = "gemma3-27b-it"
label = "Gemma 3 27B"
tags = ["local", "strict-shape"]

[runtime]
context_budget_mode = "balanced"   # runtime-adjustable by TOAS
streaming_mode = "enabled"         # runtime-adjustable by TOAS
async_runs = "enabled"             # runtime-adjustable by TOAS
cancellation_mode = "enabled"      # runtime-adjustable by TOAS
thinking_stream_mode = "disabled"  # runtime-adjustable by TOAS; optional thinking stream projection
prompt_progress_mode = "disabled"  # runtime-adjustable by TOAS; optional prompt-processing progress projection

[capability_advertisement]
profile = "core"                   # core|full|debug
hidden_tools = ["echo_block"]

[backend]
mode = "external"                  # external|managed-local

[backend.managed_local]
command = ["python", "-m", "llama_cpp.server", "--model", "/path/model.gguf"]
cwd = "."
health_url = "http://127.0.0.1:8080/health"
health_timeout_s = 15.0

[backend.managed_local.env]
CUDA_VISIBLE_DEVICES = "0"

[backend_startup]
thinking_budget_tokens = 0         # startup-only constraint; requires backend restart/apply
```

Managed lifecycle commands (daemon RPC mode):

```text
toas backend status
toas backend start
toas backend stop
toas backend restart
```

Precedence is:
- session override (`/config set`)
- config files (global + project layered; highest precedence is project `toas.toml` compatibility when present)
- environment defaults/runtime defaults

## Development

Run tests with:

```bash
uv run pytest
```

Run lint and type checks with:

```bash
uv run ruff check src tests
uv run mypy
```

Test runs include coverage checks by default (`--cov=toas --cov-fail-under=79`).

## Vim Persistent Channel

TOAS includes a minimal Vim plugin at `vim/plugin/toas.vim`.

- `:ToasStep`
  Prefers async run/watch flow over persistent RPC (`step_async` + `watch`) and inserts returned blocks after the cursor.
  Falls back to synchronous `step` RPC, then CLI fallback if RPC is unavailable.
  In non-blocking mode it inserts a per-run sentinel region and streams updates in place.
- `:ToasStepAsync`
  Starts async step execution and stores `g:toas_active_run_id`.
- `:ToasWatch [run_id] [--follow]`
  Polls watch events for the active run (or explicit `run_id`) and appends streamed output.
- `:ToasCancel [run_id]`
  Requests cancellation for the active run (or explicit `run_id`).

Quick setup in Vim:

```vim
set runtimepath^=/path/to/toas
```

Optional socket override:

```vim
let g:toas_socket_path = '/custom/path/.toas.sock'
```

Optional non-blocking toggle (default enabled):

```vim
let g:toas_step_nonblocking = 0
```

## Daemon Recovery Notes

- stale socket files are cleaned before daemon start if the endpoint healthcheck fails
- `toas step` and other RPC-routed commands fall back to local execution on RPC errors
- `toas daemon stop` uses SIGTERM with SIGKILL fallback if termination does not complete
- on Windows, named pipes are implemented in transport code but still require real Windows runtime verification in your target environment

## Latency Benchmark

Run local benchmark comparisons with:

```bash
uv run toas-bench --iterations 20 --json
```

Current local sample (8 iterations):

- `spawn_local_cli_step` p50: ~200ms
- `cli_over_rpc_step` p50: ~198ms
- `persistent_rpc_step` p50: ~2.7ms

Interpretation:

- CLI spawn dominates latency even when RPC is used under the hood
- direct persistent channel path (the Vim integration target) is materially faster

## Key Docs

- [docs/vision.md](docs/vision.md)
- [docs/roadmap.md](docs/roadmap.md)
- [docs/runtime-ownership.md](docs/runtime-ownership.md)
- [docs/runtime-direction.md](docs/runtime-direction.md)
- [docs/execution-model.md](docs/execution-model.md)
- [docs/capabilities.md](docs/capabilities.md)
- [docs/llm-notes.md](docs/llm-notes.md)
- [docs/protocol-notes.md](docs/protocol-notes.md)
- [AGENTS.md](AGENTS.md)
