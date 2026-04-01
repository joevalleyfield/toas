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

## Next Horizons

The next useful work is extension, not completion.

### 1. Richer Tooling

Potential focus:
- more built-in tools than `echo`
- better argument schemas
- stronger execution policy and safety boundaries
- richer result payloads than canonical text alone

This is now the clearest next build direction because the runtime mechanics are no longer toy-sized, but the capability surface still is.

### 2. Prompted Extraction And Repair

Potential focus:
- use extraction prompt assets in a real workflow
- use repair prompt assets when callable structure is malformed
- move beyond “last YAML block parses” as the only structural path

### 3. Better Model Runtime

Potential focus:
- bounded retries with clearer error classes
- optional streaming
- richer metadata in `llm_call` records
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

The highest-leverage next step is richer tooling.

Recommended order:

1. add a bounded `shell` tool with explicit policy and structured output
2. add repo-native `read_file` and `search` tools
3. enrich `tool_result` records beyond flat canonical text
4. derive transcript-visible `RESULT` blocks from those richer payloads

That expands practical capability without reopening the architectural decisions that are now settled.

## Next Task Set

The next concrete task set is:

- `160`: richer tooling umbrella
- `161`: bounded shell tool
- `162`: repo read/search tools
- `163`: structured tool result records
- `164`: canonical result projection from structured tool outputs

After that, the next likely track is prompted extraction and repair.

## Boundaries To Preserve

Future work should still preserve these constraints:

- no hidden mutable state outside durable history unless clearly justified
- no conflation of message events with control, tool, or model-call records
- no system-side rewriting of user transcript content during ordinary operation
- no storage decisions that make lineage or replay ambiguous

If future work weakens one of those constraints, it should be explicit.
