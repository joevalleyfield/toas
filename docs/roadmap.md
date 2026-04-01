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

### 1. Prompted Extraction And Repair

Potential focus:
- use extraction prompt assets in a real workflow
- use repair prompt assets when callable structure is malformed
- move beyond “last YAML block parses” as the only structural path

Why now:
- endpoint characterization showed that YAML/tool-call prompting is fragile enough that extraction and repair should be treated as runtime capabilities, not future polish

### 2. Better Model Runtime

Potential focus:
- bounded retries with clearer error classes
- optional streaming
- richer metadata in `llm_call` records where the current shape still feels too thin
- support for more than one compatible backend shape

### 3. Richer Replay And Branch UX

Potential focus:
- head ancestry inspection
- better branch summaries
- more selective rebuild targets
- friendlier divergence debugging

### 4. Scale And Indexing

Potential focus:
- smarter anchor placement
- lightweight indexes for large logs
- snapshots or compaction, if they can preserve current invariants

## Suggested Next Move

The next immediate move is prompted extraction and repair.

Recommended order:

1. use JSON-first extraction prompting on TOAS-relevant structures
2. add repair handling for malformed callable output
3. keep the harness around to compare prompt variants when reliability is unclear
4. only then broaden into retries/streaming or heavier runtime concerns

That uses the characterization work rather than letting it sit as an isolated probe effort.

## Next Task Set

The previous next-task set is now closed:

- `170`: endpoint characterization umbrella
- `171`: expand harness scenarios and reporting
- `172`: document observed endpoint quirks
- `173`: runtime normalization policy for model responses
- `174`: structured-output robustness probes

The next likely track should elaborate prompted extraction and repair into a fresh task series.

## Boundaries To Preserve

Future work should still preserve these constraints:

- no hidden mutable state outside durable history unless clearly justified
- no conflation of message events with control, tool, or model-call records
- no system-side rewriting of user transcript content during ordinary operation
- no storage decisions that make lineage or replay ambiguous

If future work weakens one of those constraints, it should be explicit.
