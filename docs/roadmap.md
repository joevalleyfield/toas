# TOAS Roadmap

## Status

The initial roadmap is complete, and several post-milestone arcs have also landed.

The repo currently has:
- graph-native message history with branching and lineage-aware `step`
- durable control, tool, model-call, and operator-command records
- head selection, jump binding, transcript projection, rebuild, and history inspection
- local OpenAI-compatible generation with no-thinking policy and trace granularity control
- registry-backed tool execution including bounded `shell`, `read_file`, `search`, and `replace_block`
- versioned prompt assets with metadata-backed browsing and dynamic capability-advertisement prompts
- RPC daemon with Unix socket transport and Vim persistent channel integration
- practical anchor maintenance
- operator config and policy persistence (`OperatorConfig`, `toas.toml`, durable `config_override` records, `/config` command)
- message provenance, correction capture, byte-offset index, ancestry inspection, and divergence summary
- unified help surface: `toas help` and `/help` enumerate CLI commands, slash commands, tools (with shell allowlist), and config keys from live registries

This document is now less about finishing the original plan and more about defining the next horizon.

## What The First Roadmap Achieved

The closed milestone set delivered:

1. Core Runtime Maturity
2. Real LLM Integration
3. Real Tool Library
4. Prompt Assets
5. Ergonomics And Scale

Since then, the following post-milestone arcs have also landed:

6. Richer Tooling — tool layer beyond toy proof-of-shape into genuinely useful built-in capability
7. Endpoint Characterization And Runtime Normalization — thinking-on/off comparisons, endpoint quirk docs, `llm_call` record improvements
8. Backend-Adaptive Operator Protocol — collision probes, file-backed prompt variants, `BackendGenerationPolicy`, protocol notes
9. Transcript Framing Hardening — `## TOAS:<ROLE>` markers, v1 retirement, marker escaping, malformed-marker failure
10. Operator Commands As Durable Records — slash-command substrate, workspace/cwd controls, `replace_block`, `/extract --dry-run`, command record model, projection/adoption semantics
11. Operator Config And Policy Persistence — `OperatorConfig`, `ExtractionPolicy`, `toas.toml`, `config_override` records, `/config` command, extraction dispatch gated on config flags
12. Message Provenance, Correction Capture, And Branch Inspection — inline `provenance` on message events, `llm_call` attribution via `message_id`, correction detection with `corrects` pointer, byte-offset seekable index, enriched `toas heads`, `toas ancestry`, `toas diff`
13. Unified Help And Discoverability — `SLASH_COMMANDS` registry in `step.py`, `render_session_help()` assembling slash commands, tools, shell allowlist, and config keys; `toas help` and `/help` both drive from live data

## Next Horizons

Section numbers below are stable identifiers, not priority ranks. See **Suggested Next Move** for active sequencing.

### 1. Windows Runtime Validation (Close 222, Deferred)

Potential focus:
- validate named-pipe daemon startup/connect/stop behavior on a real Windows machine (CLI RPC path)
- validate Windows Vim persistent-channel transport behavior using the localhost TCP endpoint (`.toas.vim-port`) rather than named pipes
- validate CLI fallback behavior (`TOAS_RPC_MODE=auto|on|off`) under Windows-specific failure modes
- harden any path normalization or endpoint naming quirks found in live runtime

Why later:
- code and mocked tests are already in place
- runtime validation depends on access to a real Windows environment
- this is intentionally parked and not treated as the active next move

### 2. Operator Commands As Durable Records (Landed, Extend)

Current status:
- explicit slash-command entry is in place for command-native prompt browsing and workspace/cwd controls
- command-context controls (`/cd`, `/pwd`, workspace scope controls) are durable and replayable
- callable projection now uses user-bridge output for clearer continuation boundaries
- slash-command execution now writes durable `command_request` and `command_result` records
- first mechanical extraction command is in place as `/extract --dry-run [--index <n>]`

Potential focus:
- broaden command coverage for mechanical extraction, compaction, and repair workflows
- refine projection and affordances where operator ambiguity still appears

Why now:
- operator pressure is increasingly in mechanical workflows (`compaction`, non-tail extraction, topic outlining), not just frontier resolution
- the landed command substrate is ready for targeted second-wave commands

### 2b. Operator Config And Policy Persistence (Landed)

That work:
- added `config.py` with `OperatorConfig` and `ExtractionPolicy` dataclasses
- flat dotted-key presentation (`extraction.yaml_position`) over nested config-shaped storage, with flatten/unflatten at the boundary
- file-backed project defaults via `toas.toml` (3.11+ `tomllib`, graceful skip on 3.10)
- durable `config_override` records in `events.jsonl` for session-level overrides; later records accumulate and win per-key
- `/config [show]` and `/config set <key> <value>` operator commands
- extraction dispatch in `step()` gated on config flags; defaults match pre-config behavior exactly

### 3. Mechanical Extraction And Manual Repair

Potential focus:
- build extraction around structural parsing and deterministic transforms first
- make repair primarily a user-facing/manual workflow at first
- move beyond "last YAML block parses" as the only structural path
- only later allow optional LLM-backed extraction or repair paths where explicitly configured

Why now:
- prompt authority is transparent (190–194 closed), extraction can be added without reintroducing hidden prompt policy
- config foundation (250) is in place to gate and vary extraction behavior explicitly
- the operator-command substrate is ready for second-wave mechanical commands

Current status:
- `/extract` is now frontier-scoped and adoption-first: preview candidates, select one, then execute via normal `step`
- extraction plan resolution supports `yaml_position = tail|first|any` from config
- `/compact` now compacts transcript `## RESULT` blocks with deterministic threshold behavior and explicit dry-run
- `/outline` now provides a mechanical, numbered transcript structure view with callable/command annotations

**Triage needed:** prompt-library planning notes for tasks `200` and `210` (session-starting family, dynamic capability-advertisement prompts) used to live here. Both delivered and annotated inline as "now in place," but this section was never cleaned up afterward. Full original notes are in git history. A future triage pass should either remove them or consolidate into a brief "also landed" summary in the Status section.

### 4. Backend-Adaptive Generation Policy (Landed)

`OperatorConfig` now provides the persistence layer for policy controls, making this work more concrete than when this section was first written.

Potential focus:
- extend `BackendGenerationPolicy` with config-backed controls for prompt selection, thinking mode, and action format
- decide when no-thinking, stricter prompts, or more entraining prompts should apply, and make that decision explicit and overridable
- add explicit fallback strategy when a backend ignores or bends the preferred protocol
- surface policy decisions through `/config` so they are inspectable and session-overridable

Why now:
- `OperatorConfig` is fresh and ready to absorb these controls
- prompt text alone is not the whole control surface — flags, terminology, and conversation setup all affect whether the backend stays inside the TOAS lane
- small arc, likely to land quickly

That work landed as tasks `260`-`262`:
- `generation` policy section in `OperatorConfig` (`thinking_mode`, `avoid_terms`) with `/config` visibility and override support
- policy derivation in `generation_policy_from_config()` consumed by `cli.py` and dynamic capability prompt rendering
- retirement of unwired aspirational backend-policy fields (`preferred_action_formats`, `protocol_prompt_version`, `entrainment_prompt_version`) with explicit seam note in code

### 5. Better Model Runtime

That work landed:
- bounded retries with explicit transient/permanent generation error classes
- config-driven retry controls (`generation.max_retries`, `generation.retry_delay_s`)
- per-attempt `llm_call` durability with attempt metadata
- richer `llm_call` metadata (`duration_ms`, optional `usage`)
- backend-call seam in `llm.py` via normalized `BackendResponse` path

Potential follow-on:
- optional streaming
- additional backend implementations on the existing seam

### 6. Message Provenance, Correction Capture, And Branch Inspection (Landed)

That work landed as tasks `292`-`296`:
- inline `provenance` field on message events at write time; sources: `user_authored`, `llm_generated`, `user_correction` (with `corrects` pointer), `adopted`
- `message_id` on `llm_call` records, written after message events so IDs are known; generation graph is now walkable in both directions
- correction detection in `step.py` at divergence: user node replacing an `llm_generated` node gets `user_correction` + `corrects` pointer; pre-provenance assistant nodes leave provenance absent rather than guessing
- fixed-size 44-byte seekable binary index (`events.idx`) written in sync with `events.jsonl`; `toas index rebuild` repairs it; O(1) seek by position or ID
- enriched `toas heads` with depth, turn count, and provenance breakdown; `toas ancestry <id>` lineage walk with provenance markers; `toas diff <head_a> <head_b>` common-ancestor and first-divergence summary

`291` (historical replay command) remains open — `/extract` explicitly shed that use case, and no replacement has been scoped yet.

### 7. Scale And Indexing

The byte-offset index has been pulled forward into section 6 as a near-term companion to provenance queries. Remaining focus here:

Potential focus:
- smarter anchor placement
- snapshots or chain compaction as a durable transformation (distinct from the current transcript-level `/compact`)

### 8. Quality-Of-Life Iteration Between Seams

Potential focus:
- keep landing targeted ergonomic fixes between major arcs
- prefer small, test-backed improvements that reduce operator friction
- avoid waiting for milestone boundaries when there is a clear local win

Why now:
- this matches the current working rhythm and has already produced high-value incremental improvements
- small QoL passes reduce risk accumulation while larger seams stay in flight

### 9. Real-Environment Backend Adaptation And Prompt-Lane Alignment

Potential focus:
- preserve a known-good minimal shell-command entrainment lane as explicit prompt-library material
- align callable template wording with extractor recognition (canonical key plus compatibility aliases)
- improve config discoverability for runtime knobs operators are actively using (`generation.thinking_mode`)
- add debug-gated backend response diagnostics without changing request semantics
- support single-transaction endpoints that only honor one user-message payload via explicit transport mode

Why now:
- live runtime behavior exposed concrete seams that are not visible in mocked or ideal OpenAI-compatible paths
- current ad-hoc local hacks indicate missing first-class controls, not missing intent
- these fixes are small-to-medium and independently landable, but together remove high-friction failure modes

## Suggested Next Move

Arc 9 is now the active next move: real-environment backend adaptation and prompt-lane alignment.

Primary next tasks:
- `298`: minimal shell-command entrainment baseline (prompt-library + tests)
- `299`: callable-template recognition alignment (`tool_name` / `operation` / `command` compatibility)
- `306`: prompt probing framework with taxonomy-backed expectations and remediation guidance

`222` remains explicitly deferred until Windows runtime validation is intentionally scheduled.

## Next Task Set

The previous next-task set is now closed:

- `170`: endpoint characterization umbrella
- `171`: expand harness scenarios and reporting
- `172`: document observed endpoint quirks
- `173`: runtime normalization policy for model responses
- `174`: structured-output robustness probes

The previous next-task set is now closed:

- `180`: backend-adaptive operator protocol umbrella
- `181`: action syntax and trigger-vocabulary probes
- `182`: entrainment-backed prompt variants
- `183`: backend-adaptive generation policy (initial scope)

The prompt surface transparency arc is also now closed:

- `190`: prompt surface transparency umbrella
- `191`: remove implicit generation prompt injection
- `192`: recast prompt assets as library material
- `193`: model-input prompt transparency
- `194`: separate prompt content from backend policy

The first session-starting prompt family is also now closed:

- `200`: session-starting prompt family

The dynamic capability-advertisement prompt task is also now closed:

- `210`: dynamic capability-advertisement prompts

The daemon/channel task set is now mostly closed:

- `220`: RPC protocol and transport interface
- `221`: Unix socket adapter
- `223`: daemon + CLI RPC step path
- `224`: Vim persistent channel integration
- `225`: RPC op parity and recovery
- `226`: latency and behavior validation

Remaining open from that arc:

- `222`: Windows runtime transport validation (named-pipe CLI RPC + Vim TCP persistent channel parity on real Windows)

Operator-command arc note:

- command-native prompt browsing (`235`), workspace/cwd controls (`236`), contextual block replacement (`237`), canonical spacing (`240`), and callable result bridge behavior (`241`) are implemented and closed.
- command-record model (`231`) and command entry/execution path (`232`) are implemented and closed.
- projection/adoption semantics (`233`), first mechanical command set (`234`), and umbrella closure (`230`) are implemented and closed.

Model-runtime policy note:

- `llm_call` trace granularity policy (`238`) and reasoning observability without roundtrip (`239`) are implemented and closed.
- default runtime now uses minimal trace durability, with explicit full-trace opt-in.

Operator config arc:

- `250`: operator config and policy persistence (implemented and closed)

Backend-adaptive generation policy arc:

- `260`: umbrella (implemented and closed)
- `261`: `GenerationPolicy` section in `OperatorConfig`; wire live fields; update consumers (implemented and closed)
- `262`: audit and retire aspirational `BackendGenerationPolicy` fields (implemented and closed)

Mechanical extraction and repair arc (closed):

- `270`: umbrella (implemented and closed)
- `271`: `/extract` live execution (superseded by `275`/`276` — see task file)
- `272`: non-tail extraction policy (`yaml_position = any/first`) (implemented and closed)
- `275`: frontier `/extract` adoption pivot (implemented and closed)
- `276`: `/extract` preview/select adoption UX (implemented and closed)
- `273`: `/compact` command (implemented and closed)
- `274`: `/outline` command (implemented and closed)

Better model runtime arc (closed):

- `280`: umbrella (implemented and closed)
- `281`: bounded retries and explicit error classes (implemented and closed)
- `282`: richer `llm_call` records and multi-backend seam (implemented and closed)

Message provenance, correction capture, and branch inspection arc:

- `290`: umbrella (implemented and closed)
- `291`: historical replay command (implemented and closed)
- `292`: provenance model foundation (implemented and closed)
- `293`: correction capture (implemented and closed)
- `294`: byte-offset index (implemented and closed)
- `295`: ancestry inspection (implemented and closed)
- `296`: divergence summary (implemented and closed)

Unified help and discoverability:

- `297`: unified help surface (implemented and closed)

Real-environment backend adaptation and prompt-lane alignment arc (open):

- `298`: minimal shell-command entrainment baseline (open)
- `299`: callable-template recognition alignment (open)
- `300`: generation config discoverability and guidance (implemented and closed)
- `301`: debug-gated backend diagnostics (implemented and closed)
- `302`: single-user-blob transport mode (implemented and closed)
- `303`: session/stdout line-ending parity for projected transcript writes (implemented and closed)
- `304`: LLM runtime endpoint/model config surface (implemented and closed)
- `305`: secret-safe API key override lane (implemented and closed)
- `306`: prompt probing framework and narrative taxonomy (open)
- `308`: multiline loose-command projection without shape loss (implemented and closed)

History note (2026-04-07):

- commits `66484dd5` (`vok`) and `19e8eee9` (`ooz`) were shipped with `tasks:` prefixes
- intended classification was `feat:` because both commits primarily delivered product behavior
- no history rewrite was performed after push; status/docs were corrected in follow-up commits instead

## Boundaries To Preserve

Future work should still preserve these constraints:

- no hidden mutable state outside durable history unless clearly justified
- no conflation of message events with control, tool, or model-call records
- no system-side rewriting of user transcript content during ordinary operation
- no storage decisions that make lineage or replay ambiguous

If future work weakens one of those constraints, it should be explicit.
