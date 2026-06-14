# TOAS Capabilities

Status: CURRENT
Normative Scope: implemented operator/runtime behavior
Task Link: `516` (doc-truth model guardrails)

## Purpose

This document describes what TOAS can do now from an operator perspective.

It focuses on current behavior and constraints, not implementation chronology.

## Core Operating Model

TOAS is built around:
- a configured transcript working file (`.toas/session.md` default via `session.transcript_path`)
- `.toas/events.jsonl` as default append-only durable canonical state (legacy root `events.jsonl` fallback when present)
- `toas step` as one-layer consequence resolution

Key model properties:
- no hidden autonomous loop
- branching by explicit parentage and lineage selection
- durable separation between message events and non-message records

Terminology guardrails (current usage):
- `cli`: operator command surface (`toas ...`) and argument/dispatch handling.
- `runtime`: semantic execution ownership (frontier resolution, runtime_step consequences, policy application).
- `host`: session-owned stdio transport process (`toas host ...`) used for persistent local interaction lanes.
- `daemon`: compatibility RPC transport/service process (`toas daemon ...`); not the semantic owner of runtime behavior.
- `async`: execution mode/lifecycle shape (`step --async`, `watch`, `cancel`), independent of whether transport is host- or daemon-routed.
- Extended glossary: `docs/terminology.md`.

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
- daemon compatibility transport: `toas daemon start|stop|status`
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

Session/transcript selection precedence for `step` surfaces (normative):
1. explicit request/session override (`--session`, RPC payload `session_path`/`session`)
2. host default session path (`toas host serve --session ...`)
3. durable selected surface mapping (`surface_select` + `surface_bind`)
4. effective config transcript path (`session.transcript_path`, including durable config overrides)
5. fallback default `.toas/session.md`

Transcript lane semantics:
- `TOAS:USER` and `TOAS:ASSISTANT` are message lanes.
- `TOAS:CONTROL` is an operator-command lane for slash-command/frontier control work (for example `/help`, `/config`, `/prompt`) and is durable in history.
- `TOAS:CONTROL` content is excluded from LLM input projection; it is visible for operator mechanics/history but not treated as user/assistant model-turn content.
- inert regions (`[[inert]]...[[/inert]]`, ```inert ... ```) dud command/call extraction in control lane the same way they do in user lane.

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

Imported file-like payloads project as Markdown code fences with language, `path=...`, and quiet `source=...` metadata when the renderer can identify a single source.

User-intent shell execution is distinct:
- explicit tail `$ ...` shorthand executes as user intent
- user-intent shell lane is recorded durably (`tool_request` / `tool_result` shape) but not constrained by bounded model shell policy
- multiline user execution is supported via tail-armed structured command forms

Shell-lane unification boundary:
- live async streaming/watch semantics are shared across user-intent and callable shell execution paths
- policy remains intentionally different:
  - callable `shell`/`shell_script` are bounded by grants/workspace validation
  - user-intent `$ ...` remains unbounded by that callable-policy layer
- `watch` mode semantics stay protocol-first:
  - `poll`: return output/events available now
  - `follow`: wait for progression until timeout/terminal

Shell grant operational-state model:
- `/shell` grant mutations are authoritative operational state updates, not transcript-line parsing.
- mutation default scope is `session`; explicit `--scope` is supported for:
  - `global`, `user`, `workspace`, `head`, `session`, `transient`
- effective precedence order (highest to lowest):
  1. `transient`
  2. `session`
  3. `head`
  4. `workspace`
  5. `user`
  6. `global`
  7. defaults
- practical consequence: transcript compaction/reprojection does not silently alter shell authorization behavior.

## Runtime Modes And Transport

`TOAS_RPC_MODE` controls local vs daemon-routed behavior:
- `off`: CLI-local execution path
- `auto` (default): prefer daemon endpoint when present, fallback local on RPC errors
- `on`: force RPC attempt first for routed commands, with explicit fallback paths

Transport/runtime surfaces:
- daemon-backed async run/watch/cancel
- Unix socket and Windows transport support
- Vim persistent channel integration as transport optimization

Async primary-surface ownership and cutover controls:
- `step` (sync):
  - ownership-first local by default
  - `--stdin` and `--control` always execute locally (never daemon-routed)
- `step --async`, `watch`, `cancel`:
  - local-first lifecycle surfaces in current architecture
  - rationale: ownership-first async path is primary; RPC remains explicit compatibility opt-back
  - ownership migration status: `525` closed after primary runtime/local ownership audit; backend lifecycle ownership is tracked separately by `260614-runtime-owned-backend-lifecycle-architecture`
  - backend mode selector:
    - `TOAS_ASYNC_BACKEND_MODE` (env) overrides config
    - `runtime.async_backend_mode` (config) fallback
    - default `local`
  - diagnostics:
    - async command status lines include `backend=<mode>`
    - when active session-host state is resolved, diagnostics include `host=<host_id>`
  - strict local cutover guard:
    - `TOAS_ASYNC_LOCAL_STRICT_GUARD=1` enforces explicit "local backend not implemented yet" exits when backend mode resolves to `local`
    - default unset/off allows the current local runtime path; explicit RPC opt-back remains available through backend mode selection

## Prompt And Generation Surfaces

Prompt system capabilities:
- file-backed prompt library with versioned assets
- first-class composed template assets (for example under `session-start/templates/*`) rendered through the same `toas prompt`/`/prompt` surface
- prompt browsing and explicit rendering
- dynamic capability-advertisement prompts
- profile-based capability advertisement controls via config (`capability_advertisement.profile`, `capability_advertisement.hidden_tools`)
- config-driven proactive prompt guidance constraints (`prompt.constraints`) applied to `/prompt` renders and bootstrap seed composition

Prompt-guidance starter recipes (operator presets):
- weak-model repo-work starter:
  - `/config set prompt.constraints tools-guidance-core,tools-guidance-repo-work`
  - use for first discovery/edit/test pass with bounded repo-local operations
- edit-heavy pass:
  - `/config set prompt.constraints tools-guidance-full`
  - use when indentation-sensitive replacements or multi-file edit planning is likely
- revert to minimal/no proactive guidance:
  - `/config unset prompt.constraints`

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
