# TOAS Roadmap

## Status

The initial roadmap is complete.

All milestone umbrellas and their elaborated tasks are now closed under [tasks/closed](/Users/tim/Documents/Projects/toas/tasks/closed).

The repo currently has:
- graph-native message history
- durable control, tool, and model-call records
- lineage-aware `step`
- head selection, jump binding, transcript projection, rebuild, and history inspection
- local OpenAI-compatible generation
- registry-backed tool execution
- richer non-trivial built-in tools (`echo`, bounded `shell`, `read_file`, `search`)
- versioned prompt assets
- practical anchor maintenance

This document is now less about finishing the original plan and more about defining the next horizon.

## What The First Roadmap Achieved

The closed milestone set delivered:

1. Core Runtime Maturity
2. Real LLM Integration
3. Real Tool Library
4. Prompt Assets
5. Ergonomics And Scale

That means the original roadmap did what it was supposed to do: it turned the design from a promising core into a coherent small runtime.

Since then, the first post-milestone extension has also landed:

6. Richer Tooling

That work moved the tool layer beyond a toy proof-of-shape and into a genuinely useful built-in capability surface.

The next post-milestone characterization pass has also landed:

7. Endpoint Characterization And Runtime Normalization

That work:
- expanded the local harness into thinking-on vs thinking-off comparisons
- documented concrete endpoint quirks in [docs/llm-notes.md](/Users/tim/Documents/Projects/toas/docs/llm-notes.md)
- made TOAS generation use the known no-thinking request knob
- updated `llm_call` records to distinguish requested model, returned model, visible content, and hidden reasoning content

The next protocol-framing pass has also landed:

8. Backend-Adaptive Operator Protocol

That work:
- added protocol-collision probes under a hostile-system simulation
- added file-backed terse and entrainment prompt variants
- codified a current awkward-backend policy in [backend_policy.py](/Users/tim/Documents/Projects/toas/src/toas/backend_policy.py)
- documented concrete collision findings in [docs/protocol-notes.md](/Users/tim/Documents/Projects/toas/docs/protocol-notes.md)

The transcript-framing hardening pass has also landed:

9. Transcript Framing Hardening

That work:
- migrated transcript role framing to strict `## TOAS:<ROLE>` markers
- retired transcript v1 marker support (`## USER` / `## ASSISTANT`)
- added explicit line-start marker escaping/unescaping for transcript content collision handling
- tightened malformed marker failure behavior so parse errors are visible

## Next Horizons

The next useful work is extension, not completion.

The prior near-term seams (daemon/channel performance path and prompt-surface transparency) are now implemented. The remaining transport seam is runtime validation of the Windows named-pipe adapter.

### 1. Windows Runtime Validation (Close 222)

Potential focus:
- validate named-pipe daemon startup/connect/stop behavior on a real Windows machine
- validate CLI fallback behavior (`TOAS_RPC_MODE=auto|on|off`) under Windows-specific failure modes
- harden any path normalization or endpoint naming quirks found in live runtime

Why now:
- code and mocked tests are already in place
- this is the last open task from the daemon/channel arc

### 2. Operator Commands As Durable Records

Potential focus:
- introduce explicit `/commands` (or equivalent CLI entrypoints) for non-`step` operator work
- persist command requests/results as durable non-message records
- keep command records linked to message-space targets without inserting them into message parentage
- project command outcomes as result-style output that users may adopt into conversation turns explicitly

Why now:
- operator pressure is increasingly in mechanical workflows (`compaction`, non-tail extraction, topic outlining), not just frontier resolution
- durable command records keep those workflows replayable and inspectable without blurring conversation lineage

### 3. Mechanical Extraction And Manual Repair

Potential focus:
- build extraction around structural parsing and deterministic transforms first
- make repair primarily a user-facing/manual workflow at first
- move beyond “last YAML block parses” as the only structural path
- only later allow optional LLM-backed extraction or repair paths where explicitly configured

Why now:
- once prompt authority is made transparent, extraction and repair can be added without quietly reintroducing hidden prompt policy

Current prompt-library refinement:
- the next prompt-library work should start with a moderately rich family of session-starting assets
- organize that family by user intent at session start:
  - `start-here`
  - `role-framing`
  - `protocol-entrainment`
  - `backend-deconfliction`
- target roughly 3–6 assets per category
- require uniform per-asset metadata with at least `name`, `description`, and `category`
- include basic browsing/listing support so users can discover assets through the index
- optimize primarily for lowering human startup friction; protocol-oriented prompts may be provisional hypotheses at first

This first session-starting prompt family is now in place as explicit library material with metadata-backed browsing.

The next prompt-library extension should add dynamic capability-advertisement prompts:
- user-selectable prompts that introspect live runtime capabilities before rendering
- grounded in actual available tools and relevant operator surfaces
- truthful, compact, and explicit about limits as well as powers
- intended for user-facing discovery and model-facing capability advertisement at the same time

This dynamic capability-advertisement prompt layer is now in place as an explicit prompt-library extension over live runtime introspection.

### 4. Backend-Adaptive Generation Policy (Next Extension)

Potential focus:
- extend the current awkward-backend policy beyond the local model
- decide when no-thinking, stricter prompts, or more entraining prompts should apply
- add explicit fallback strategy when a backend ignores or bends the preferred protocol

Why now:
- prompt text alone is not the whole control surface
- flags, terminology, and conversation setup all affect whether the backend stays inside the TOAS lane

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

The next immediate move is to close `222` with real Windows runtime validation, then define and land the operator-command record arc before extending extraction/repair and backend/runtime hardening.

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

## Boundaries To Preserve

Future work should still preserve these constraints:

- no hidden mutable state outside durable history unless clearly justified
- no conflation of message events with control, tool, or model-call records
- no system-side rewriting of user transcript content during ordinary operation
- no storage decisions that make lineage or replay ambiguous

If future work weakens one of those constraints, it should be explicit.
