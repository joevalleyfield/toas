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

## Next Horizons

Section numbers below are stable identifiers, not priority ranks. See **Suggested Next Move** for active sequencing.

### 1. Windows Runtime Validation (Close 222, Deferred)

Potential focus:
- validate named-pipe daemon startup/connect/stop behavior on a real Windows machine
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

Potential focus:
- bounded retries with clearer error classes
- optional streaming
- richer metadata in `llm_call` records where the current shape still feels too thin
- support for more than one compatible backend shape

### 6. Richer Replay And Branch UX

Potential focus:
- head ancestry inspection
- better branch summaries
- more selective rebuild targets
- friendlier divergence debugging

### 7. Scale And Indexing

Potential focus:
- smarter anchor placement
- lightweight indexes for large logs
- snapshots or compaction, if they can preserve current invariants

### 8. Quality-Of-Life Iteration Between Seams

Potential focus:
- keep landing targeted ergonomic fixes between major arcs
- prefer small, test-backed improvements that reduce operator friction
- avoid waiting for milestone boundaries when there is a clear local win

Why now:
- this matches the current working rhythm and has already produced high-value incremental improvements
- small QoL passes reduce risk accumulation while larger seams stay in flight

## Suggested Next Move

Route through mechanical extraction and repair (section 3) next. The operator-command substrate and config/policy foundations are now in place, so this is the highest-leverage seam.

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

- `222`: Windows named-pipe adapter (implementation can proceed here, but runtime validation requires a Windows environment)

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

Mechanical extraction and repair arc (open):

- `270`: umbrella
- `271`: `/extract` live execution
- `272`: non-tail extraction policy (`yaml_position = any/first`)
- `273`: `/compact` command
- `274`: `/outline` command

Better model runtime arc (open):

- `280`: umbrella
- `281`: bounded retries and explicit error classes
- `282`: richer `llm_call` records and multi-backend seam

Richer replay and branch UX arc (open, sub-tasks not yet elaborated):

- `290`: umbrella

## Boundaries To Preserve

Future work should still preserve these constraints:

- no hidden mutable state outside durable history unless clearly justified
- no conflation of message events with control, tool, or model-call records
- no system-side rewriting of user transcript content during ordinary operation
- no storage decisions that make lineage or replay ambiguous

If future work weakens one of those constraints, it should be explicit.
