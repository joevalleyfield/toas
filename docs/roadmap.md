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

## Next Horizons

The next useful work is extension, not completion.

### 1. Backend-Adaptive Operator Protocol

Potential focus:
- identify where provider-native tool semantics collide with TOAS semantics
- test alternative action vocabularies that avoid triggering built-in tool protocols
- compare YAML, JSON, and more neutral "action block" framings
- determine when entrainment and few-shot demonstration are required

Why now:
- the real constraint is not just structured-output quality
- it is protocol collision with hidden server-side prompting and tool behavior

### 2. Prompted Extraction And Repair

Potential focus:
- use extraction prompt assets in a real workflow
- use repair prompt assets when callable structure is malformed
- move beyond “last YAML block parses” as the only structural path
- make extraction/repair part of how TOAS survives backend drift rather than a polish layer

Why now:
- once protocol collision is acknowledged, extraction and repair become core adaptation mechanisms

### 3. Backend-Adaptive Generation Policy

Potential focus:
- select prompts and request flags based on backend behavior
- decide when no-thinking, stricter prompts, or more entraining prompts should apply
- add explicit fallback strategy when a backend ignores or bends the preferred protocol

Why now:
- prompt text alone is not the whole control surface
- flags, terminology, and conversation setup all affect whether the backend stays inside the TOAS lane

### 4. Better Model Runtime

Potential focus:
- bounded retries with clearer error classes
- optional streaming
- richer metadata in `llm_call` records where the current shape still feels too thin
- support for more than one compatible backend shape

### 5. Richer Replay And Branch UX

Potential focus:
- head ancestry inspection
- better branch summaries
- more selective rebuild targets
- friendlier divergence debugging

### 6. Scale And Indexing

Potential focus:
- smarter anchor placement
- lightweight indexes for large logs
- snapshots or compaction, if they can preserve current invariants

## Suggested Next Move

The next immediate move is to treat protocol collision avoidance as a first-class design goal, then build extraction and repair on top of that.

Recommended order:

1. compare action syntaxes and trigger vocabularies that do or do not collide with provider-native tool prompting
2. codify a small set of prompt/flag strategies for hostile or awkward backends
3. build extraction and repair around the most reliable surviving action lane
4. keep the harness around to compare prompt variants when reliability is unclear
5. only then broaden into retries/streaming or heavier runtime concerns

That uses the characterization work to support the real project goal: maintaining a controllable operator protocol even when the backend already has one.

## Next Task Set

The previous next-task set is now closed:

- `170`: endpoint characterization umbrella
- `171`: expand harness scenarios and reporting
- `172`: document observed endpoint quirks
- `173`: runtime normalization policy for model responses
- `174`: structured-output robustness probes

The next concrete task set is:

- `180`: backend-adaptive operator protocol umbrella
- `181`: action syntax and trigger-vocabulary probes
- `182`: entrainment-backed prompt variants
- `183`: backend-adaptive generation policy

After that, prompted extraction and repair should be elaborated on top of the surviving action lane.

## Boundaries To Preserve

Future work should still preserve these constraints:

- no hidden mutable state outside durable history unless clearly justified
- no conflation of message events with control, tool, or model-call records
- no system-side rewriting of user transcript content during ordinary operation
- no storage decisions that make lineage or replay ambiguous

If future work weakens one of those constraints, it should be explicit.
