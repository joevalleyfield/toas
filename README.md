# TOAS

TOAS is a transcript-oriented operator over durable history.

It exists in part to make a locally available but behaviorally awkward model usable through stronger operator semantics, durable state, and better control over prompting, tool use, and replay.

The system is built around three things:
- `session.md`: the user-controlled working transcript
- `events.jsonl`: append-only durable state
- `toas step`: a one-step operator that accepts transcript state and resolves one layer of consequence

It is not a hidden conversation loop. It is a small operator runtime over a message graph plus related operator records.

## Current Features

- graph-native message history with branching
- durable `jump`, `head`, and `anchor` control records
- lineage-aware `step`
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
- `toas step --async`
  Start one step asynchronously over daemon RPC and return a `run_id`.
- `toas watch <run_id> [--offset <n>] [--follow]`
  Read incremental output for an async run.
- `toas cancel <run_id>`
  Request cancellation for an async run.
- `toas jump <bind_index>`
  Set manual transcript binding in message-view space.
- `toas head <head_id>`
  Select the current lineage head.
- `toas heads`
  List known lineage heads.
- `toas transcript [head_id]`
  Print a lineage-backed transcript projection.
- `toas llm-input [head_id]`
  Print model-facing projected messages as transcript-style blocks.
- `toas prompt <ref> [--mode <direct|mimic>] [--constraint <name> ...]`
  Print a named prompt asset so it can be inserted explicitly into the transcript.
- `toas prompts [prefix]`
  Browse prompt assets (including composed template assets) and one-line descriptions by library prefix.
- `toas history [limit]`
  Print selected head, bind state, heads, and recent event summaries.
- `toas rebuild [head_id]`
  Rewrite `session.md` from projected history and emit a useful anchor.
- `toas daemon [start|stop|status]`
  Manage the local `toasd` process used for RPC-backed stepping.

`toas` commands can be routed through daemon RPC using `TOAS_RPC_MODE`:

- `TOAS_RPC_MODE=auto` (default): prefer RPC when daemon endpoint exists, fallback to local
- `TOAS_RPC_MODE=on`: require RPC path, fallback only on RPC error
- `TOAS_RPC_MODE=off`: always run local path

`step --async`, `watch`, and `cancel` are currently daemon-RPC surfaces.

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

### 3. Persistent Vim channel mode

Use this for lowest per-step latency in editor workflows.

```vim
:ToasStep
```

`ToasStep` uses a persistent RPC channel to `toasd` and falls back to `:read !toas step` if needed.

## Shell Policy

- A frontier line of the form `$ ...` is treated as explicit user shell intent.
- That user-shell path is not restricted by TOAS command allowlists or workspace fences.
- The registry `shell` tool remains bounded because it is model-addressable capability rather than direct user intent.
- Assistant loose `command:` proposals project as:
  - single-line: `$ ...`
  - multiline: preserved multiline command text (not flattened to one line)
- Multiline user execution uses tail-armed structured command shape (for example tail YAML `command:` / `cmd:` blocks), not `$` plus trailing prose.

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

Use `/config` for in-session overrides and `toas.toml` for project defaults.

In session:

```text
/config show
/config show --sources
/config set generation.thinking_mode disabled
/config set generation.max_retries 2
/config set generation.retry_delay_s 0.25
/config unset generation.max_retries
/config restore
/config load ./toas.toml
/config save ./toas.toml
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

Project defaults (`toas.toml`):

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
- project config (`toas.toml`)
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

- [docs/vision.md](/Users/tim/Documents/Projects/toas/docs/vision.md)
- [docs/roadmap.md](/Users/tim/Documents/Projects/toas/docs/roadmap.md)
- [docs/llm-notes.md](/Users/tim/Documents/Projects/toas/docs/llm-notes.md)
- [docs/protocol-notes.md](/Users/tim/Documents/Projects/toas/docs/protocol-notes.md)
- [AGENTS.md](/Users/tim/Documents/Projects/toas/AGENTS.md)
