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
- `toas prompt <kind>/<version>`
  Print a named prompt asset so it can be inserted explicitly into the transcript.
- `toas prompts [prefix]`
  Browse prompt assets and one-line descriptions by library prefix.
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

## Runtime Defaults

The local model client defaults to:

- `TOAS_LLM_BASE_URL=http://localhost:8080/v1`
- `TOAS_LLM_API_KEY=not-needed`
- `TOAS_LLM_MODEL=qwen3.5-35b-a3b`

That matches a local OpenAI-compatible `llama-cpp` style setup.

## Development

Run tests with:

```bash
uv run pytest
```

## Vim Persistent Channel

TOAS includes a minimal Vim plugin at `vim/plugin/toas.vim`.

- `:ToasStep`
  Sends a `step` RPC request over a persistent channel to `toasd` and inserts returned blocks after the cursor.
  If channel setup or RPC fails, it falls back to `:read !toas step`.

Quick setup in Vim:

```vim
set runtimepath^=/path/to/toas
```

Optional socket override:

```vim
let g:toas_socket_path = '/custom/path/.toas.sock'
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
