# Runtime Ownership And Module Boundaries

Status: CURRENT
Normative Scope: contribution guidance for where runtime, tool, CLI, and transport semantics should live
Task Link: `675`
Related: `400`, `525`, `572`, `674`

## Purpose

This note describes the current ownership map while TOAS continues the `400`
decomposition arc.

Several historical files remain as public import surfaces or compatibility
facades. New behavior should follow the ownership boundaries below rather than
the older habit of placing broad logic in `step.py`, `tools.py`, `cli.py`, or
`daemon.py`.

## Ownership Principles

- Keep durable storage and graph append/query concerns in `graph.py` and
  focused `graph_*_edges.py` / `graph_*_writers.py` helpers.
- Keep transcript parsing and transcript-shape mechanics in `transcript.py` and
  transcript/frontier-specific helpers.
- Keep semantic execution ownership in `src/toas/runtime/`.
- Keep tool capability behavior in `src/toas/tools_cluster/`.
- Keep CLI modules thin: argument parsing, local orchestration calls, rendering,
  and compatibility wrapping.
- Keep daemon modules transport-adapter oriented. Daemon/RPC can carry runtime
  requests, but should not define semantic behavior.
- Keep model transport in `llm.py` and prompt library behavior in `prompts.py`
  plus file-backed prompt assets.
- Prefer focused helpers over new compatibility shims. Add or keep facade
  symbols only when they preserve an existing public/import contract.

## Current Module Map

### Semantic Runtime

`src/toas/runtime/` owns frontier and consequence semantics:

- `step_runtime.py`, `frontier_resolution.py`, and `step_*_runtime.py` own the
  step/consequence path.
- `operator_commands.py` and `operator_command_*` modules own slash-command
  runtime behavior.
- `result_nodes.py`, `rendering_edges.py`, and `presentation_edges.py` own
  runtime/projection result-node boundaries.
- `async_activity_store*`, `stream_subscribe_runtime.py`,
  `session_host_process.py`, and transport contract modules own runtime-host and
  async lifecycle semantics.
- `session_step_edges.py`, `session_file_edges.py`, and related edge modules own
  cross-surface runtime glue that is semantic rather than CLI-specific.

### Tool Capabilities

`src/toas/tools_cluster/` owns model-addressable tool behavior:

- `registry.py` owns validation/dispatch mechanics.
- `execution.py` owns plan execution orchestration.
- `basic_ops.py`, `file_ops.py`, `apply_patch_ops.py`, `shell_ops.py`, and
  `shell_streaming.py` own concrete capabilities.
- `rendering.py` owns tool-result projection shaping.
- `capability_help_ops.py` and `survey_ops.py` own introspection helpers.

`src/toas/tools.py` remains the registry-facing public facade and compatibility
surface. New tool behavior should normally land in `tools_cluster/` and be
wired through `tools.py` only as needed for the established public registry.

### CLI And Operator API

CLI ownership is split across focused modules:

- `cli.py` is a compatibility-facing entry surface and should stay thin.
- `cli_dispatch.py` and `cli_dispatch_ops.py` own top-level argument routing.
- `cli_session_commands.py`, `cli_async_commands.py`, `cli_host_commands.py`,
  `cli_runtime_commands.py`, `cli_session_views.py`, `cli_analysis_commands.py`,
  and `cli_streaming.py` own command-family wrappers and rendering.
- `operator_api.py` is the in-process API seam for local operator workflows.

New semantic behavior should usually move below these wrappers into
`runtime/`, `tools_cluster/`, `graph*`, or config/prompt modules.

### Daemon, Host, And Transport

`src/toas/daemon/` owns daemon transport/server compatibility:

- request parsing, dispatch adapters, process lifecycle, backend lifecycle, and
  run-store transport state live here.
- Runtime semantics consumed by daemon paths should come from `runtime/` or
  `operator_api.py`.

The session host direction is runtime-owned and stdio-first. See
`docs/runtime-direction.md` for the broader target architecture.

### Historical Facades

These files are important but should not attract unrelated new logic:

- `step.py`: legacy/session-help facade plus compatibility exports around
  runtime-owned step and operator-command behavior.
- `tools.py`: public registry facade around `tools_cluster/`.
- `cli.py`: top-level compatibility surface around focused CLI modules.
- `daemon/__init__.py`: package facade around daemon adapter modules.

When editing these files, prefer delegation, compatibility preservation, and
small wrapper cleanup over adding new ownership.

## Routing Questions

Use these defaults when choosing where to edit:

- Does it change what a transcript frontier means or what consequence is
  produced? Use `runtime/`.
- Does it change durable record storage/query behavior? Use `graph.py` or a
  focused `graph_*` helper.
- Does it change a model-addressable tool? Use `tools_cluster/`, then wire the
  registry facade.
- Does it change user CLI parsing or stdout presentation only? Use focused
  `cli_*` modules.
- Does it change daemon/RPC carrying behavior without changing semantics? Use
  `daemon/` or protocol/transport modules.
- Does it change backend HTTP/model-call transport? Use `llm.py` or related
  generation runtime seams.
- Does it change prompt asset discovery/rendering? Use `prompts.py` or prompt
  assets.

When a change crosses these boundaries, keep the semantic change in the owning
layer and let outer surfaces call into it.
