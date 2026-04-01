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

## Next Horizons

The next useful work is extension, not completion.

### 1. Endpoint Characterization And Runtime Normalization

Potential focus:
- broaden the live endpoint probe matrix
- record behavioral quirks that matter for agentic use
- decide how TOAS should treat fields like `reasoning_content`
- improve prompt/output robustness for structured responses

Groundwork already exists:
- `toas-llm-harness`
- initial live probes against the local OpenAI-compatible endpoint

### 2. Richer Tooling

This is no longer just prospective work. The `160` series is closed and delivered:
- bounded `shell`
- repo-native `read_file`
- repo-native `search`
- structured tool result records
- canonical `RESULT` projection from structured payloads

Further richer-tooling work is still possible, but it is no longer the immediate missing piece.

### 3. Prompted Extraction And Repair

Potential focus:
- use extraction prompt assets in a real workflow
- use repair prompt assets when callable structure is malformed
- move beyond “last YAML block parses” as the only structural path

### 4. Better Model Runtime

Potential focus:
- bounded retries with clearer error classes
- optional streaming
- richer metadata in `llm_call` records
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

The next immediate move is to characterize the live inference endpoint more deliberately, because richer tooling is now in place and the next practical uncertainty is model behavior under agentic prompting.

Recommended order:

1. expand the harness scenario matrix
2. write down endpoint quirks and candidate mitigations
3. decide normalization policy for model responses
4. then continue into prompted extraction/repair with that knowledge in hand

That avoids building agentic flows on assumptions the live endpoint may not satisfy.

## Next Task Set

The next concrete task set is:

- `170`: endpoint characterization umbrella
- `171`: expand harness scenarios and reporting
- `172`: document observed endpoint quirks
- `173`: runtime normalization policy for model responses
- `174`: structured-output robustness probes

After that, the next likely track is richer tooling plus prompted extraction and repair, informed by what the live endpoint actually does.

## Boundaries To Preserve

Future work should still preserve these constraints:

- no hidden mutable state outside durable history unless clearly justified
- no conflation of message events with control, tool, or model-call records
- no system-side rewriting of user transcript content during ordinary operation
- no storage decisions that make lineage or replay ambiguous

If future work weakens one of those constraints, it should be explicit.
