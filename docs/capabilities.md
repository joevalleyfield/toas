# TOAS Capabilities

## Purpose

This document describes what TOAS can do now from an operator perspective.

It focuses on current behavior and constraints, not implementation chronology.

## Core Operating Model

TOAS is built around:
- a configured transcript working file (`session.md` default via `session.transcript_path`)
- `.toas/events.jsonl` as default append-only durable canonical state (legacy root `events.jsonl` fallback when present)
- `toas step` as one-layer consequence resolution

Key model properties:
- no hidden autonomous loop
- branching by explicit parentage and lineage selection
- durable separation between message events and non-message records

## Durable Record Surfaces

Message-event surface:
- `id`, `parent`, `role`, `content`, `metadata`
- optional provenance for source classification (`user_authored`, `llm_generated`, `user_correction`, `adopted`)

Non-message durable surfaces:
- control records (`jump`, `head`, `anchor`)
- tool records (`tool_request`, `tool_result`)
- model-call records (`llm_call`)
- operator command records (`command_request`, `command_result`)
- config override records (`config_override`)
- execution queue records (`execution_queue`) for replayed multi-op continuation state

## Step And Frontier Resolution

`toas step` resolves one frontier layer at a time.

Observed resolution behavior:
- non-callable user tail: eligible for model generation
- callable tail (user or assistant): eligible for execution
- execution and generation are intentionally separate consequences

Projection behavior:
- stdout emits newly produced consequences only
- result-style outputs project as `## RESULT` blocks
- historical content is not re-echoed during ordinary step output

## Command And Transcript Surfaces

Primary CLI surfaces include:
- stepping: `toas step`, `toas step --async`, `toas watch`, `toas cancel`
- replay harness: `toas replay-script <script_path> [--output <path>] [--dry-run]`
- lineage/inspection: `toas heads`, `toas head`, `toas jump`, `toas transcript`, `toas llm-input`, `toas history`, `toas ancestry`, `toas diff`, `toas index rebuild`
- intent inspection: `toas intents`
- prompt surfaces: `toas prompt`, `toas prompts`
- daemon/runtime: `toas daemon start|stop|status`
- backend lifecycle: `toas backend start|stop|restart|status`

Session command surfaces include:
- `/help`
- `/prompt` (canonical selector)
- `/prompts` (compat alias)
- `/model`, `/backend`
- `/env set|unset`
- `/config` (`show`, `set`, `unset`, `restore`, `load`, `save`, backend subcommands)
- `/intent` (`list`, `current`, `set`, `status`, `note`)
- `/extract [--verbose] [index]`
- `/replay [--dry-run] [--index <n>] [--force]`
- `/replay --resume|--approve|--skip|--cancel <queue_id>` for queued multi-op continuation

Callable action schema supports canonical and compatibility forms:
- canonical fields: `operation`, `params`, optional `intent`
- compatibility aliases: `tool_name`, `args`/`arguments`, `intention`
- shell payload guard: reject mixed `argv` + `command`/`cmd` in one call

## Tooling And Execution Capabilities

Built-in tool layer includes bounded model-addressable capabilities such as:
- shell execution (bounded policy lane)
- file and search/edit helpers (for example `read_file`, `search`, `replace_block`, `write_file`, `replace_range`)
- structure and echo helpers (`get_structure`, `echo_block`)
- capability introspection (`capability_help`) for compact topic/tool detail during active runs
- procedure invocation (`procedure`) for reusable named multi-step repo workflows

User-intent shell execution is distinct:
- explicit tail `$ ...` shorthand executes as user intent
- user-intent shell lane is recorded durably (`tool_request` / `tool_result` shape) but not constrained by bounded model shell policy
- multiline user execution is supported via tail-armed structured command forms

## Runtime Modes And Transport

`TOAS_RPC_MODE` controls local vs daemon-routed behavior:
- `off`: CLI-local execution path
- `auto` (default): prefer daemon endpoint when present, fallback local on RPC errors
- `on`: force RPC attempt first for routed commands, with explicit fallback paths

Transport/runtime surfaces:
- daemon-backed async run/watch/cancel
- Unix socket and Windows transport support
- Vim persistent channel integration as transport optimization

## Prompt And Generation Surfaces

Prompt system capabilities:
- file-backed prompt library with versioned assets
- first-class composed template assets (for example under `session-start/templates/*`) rendered through the same `toas prompt`/`/prompt` surface
- prompt browsing and explicit rendering
- dynamic capability-advertisement prompts
- profile-based capability advertisement controls via config (`capability_advertisement.profile`, `capability_advertisement.hidden_tools`)

Generation/runtime capabilities:
- OpenAI-compatible backend integration
- config-backed generation policy controls (including thinking mode)
- bounded retry behavior with transient/permanent error classification
- per-attempt `llm_call` durability and metadata
  - optional stream-projection lanes under runtime policy:
  - thinking stream projection (`runtime.thinking_stream_mode`)
  - prompt-processing progress projection (`runtime.prompt_progress_mode`)

Context assembly lens workflow:
- durable lens management: `/lens list|set|remove|reset`
- packet quality triage: `/lens packet`, `/lens doctor`
- folded packet inspection:
  - baseline folded view: `/lens packet --folded`
  - explicit expansion by source handles: `/lens packet --folded --expand n42,n43`
  - compare folded vs expanded budget counters in output (`text_budget_chars`, `depth_counts`, `hidden_refs`) before deciding whether to refine lens artifacts

## Inspection, Provenance, And Scale Aids

Current introspection and durability aids include:
- provenance markers on message events and correction linkage
- seekable binary index companion for fast event lookup
- lineage and divergence inspection (`heads`, `ancestry`, `diff`)
- transcript rebuild and llm-input projection for auditability

## Constraints And Invariants

Operational boundaries:
- prior history is append-only and not mutated
- message-event numbering/lineage is distinct from non-message records
- transcript edits that diverge from prior aligned content branch rather than rewrite history
- direct user intent remains distinct from model-addressable capability

## Related Docs

- `docs/vision.md`
- `docs/roadmap.md`
- `docs/protocol-notes.md`
- `docs/storage-notes.md`
- `docs/llm-notes.md`
- `README.md`
