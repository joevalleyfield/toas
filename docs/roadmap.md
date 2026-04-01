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

## Next Horizons

The next useful work is extension, not completion.

### 1. Prompted Extraction And Repair

Potential focus:
- use extraction prompt assets in a real workflow
- use repair prompt assets when callable structure is malformed
- move beyond “last YAML block parses” as the only structural path
- make extraction/repair part of how TOAS survives backend drift rather than a polish layer

Why now:
- once protocol collision is characterized, extraction and repair become the next core adaptation mechanisms

### 2. Backend-Adaptive Generation Policy

Potential focus:
- extend the current awkward-backend policy beyond the local model
- decide when no-thinking, stricter prompts, or more entraining prompts should apply
- add explicit fallback strategy when a backend ignores or bends the preferred protocol

Why now:
- prompt text alone is not the whole control surface
- flags, terminology, and conversation setup all affect whether the backend stays inside the TOAS lane

### 3. Better Model Runtime

Potential focus:
- bounded retries with clearer error classes
- optional streaming
- richer metadata in `llm_call` records where the current shape still feels too thin
- support for more than one compatible backend shape

### 4. Richer Replay And Branch UX

Potential focus:
- head ancestry inspection
- better branch summaries
- more selective rebuild targets
- friendlier divergence debugging

### 5. Scale And Indexing

Potential focus:
- smarter anchor placement
- lightweight indexes for large logs
- snapshots or compaction, if they can preserve current invariants

## Suggested Next Move

The next immediate move is to build extraction and repair on top of the now-characterized awkward-backend action lane.

Recommended order:

1. build extraction around the most reliable surviving action lane
2. add repair handling when the backend drifts into provider-native protocol anyway
3. keep the harness around to compare prompt variants when reliability is unclear
4. only then broaden into retries/streaming or heavier runtime concerns

That uses the characterization and protocol work to support the real project goal: maintaining a controllable operator protocol even when the backend already has one.

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
- `183`: backend-adaptive generation policy

The next likely track should elaborate prompted extraction and repair on top of the surviving action lane.

## Boundaries To Preserve

Future work should still preserve these constraints:

- no hidden mutable state outside durable history unless clearly justified
- no conflation of message events with control, tool, or model-call records
- no system-side rewriting of user transcript content during ordinary operation
- no storage decisions that make lineage or replay ambiguous

If future work weakens one of those constraints, it should be explicit.
