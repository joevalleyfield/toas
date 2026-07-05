# Transcript / LLM-Input Surface Contract

Status: DIRECTIONAL
Task Link: `260627-history-surface-user-intent-alignment`
Related: `260628-history-root-to-head-lineage-contract`; `260628-graph-selected-history-topology-framing`; `260703-transcript-llm-input-hot-default`

## Purpose

Capture the narrowed result of the broader history-surface audit:

- keep the read surfaces legible as one family
- make the `transcript` contract explicit
- make the `llm-input` contract explicit
- state the projection delta between them

## Family Story

The main read surfaces should still teach one coherent operator-facing family:

- `history`: one root-to-head lineage
- `heads`: the leaf set / branch-tip view
- `graph`: the topology view
- `transcript`: transcript-shaped reconstruction of a selected lineage
- `llm-input`: model-visible projection of that same selected lineage

The family audit already produced most of the major surface corrections:

- `rebuild` is gone as a peer surface
- `history` is now framed as a bounded root-to-head lineage view
- `heads` and `graph` have explicit sibling framing
- hot/current zero-arg defaults are aligned across the main read surfaces

## `transcript` Contract

`transcript` should take durable event history plus a selected leaf and
re-render the transcript state for that lineage.

The strong intended requirement is:

- previously stepped transcript states are recoverable from durable events
  alone
- saved transcript files are convenience surfaces, not required truth

Current evidence already lines up with that contract:

- `README.md` describes `toas transcript [head_id]` as transcript projection and
  teaches resume-from-lineage through redirect rather than through a separate
  writeback surface
- `src/toas/operator_api.py` routes `transcript_text(...)` to
  `project_transcript(...)` over selected durable events
- `tests/test_graph.py` covers transcript reconstruction from message history,
  explicit head targeting, and ignoring non-message records
- `tests/test_operator_api.py` and `tests/test_history_scale_models.py` cover
  transcript projection through the operator-facing surface, including hot/cold
  history shapes and selected-source anchor behavior

This does not prove perfect symmetry with `step`, but it does prove the more
important operator claim: durable events are sufficient to reconstruct prior
transcript states for selected lineages.

## `llm-input` Contract

`llm-input` should show the human a faithful rendering of what the model is
seeing for that same durable lineage.

This is not only an internal debugging surface. It is also an operator escape
hatch: the rendered input should be usable outside TOAS when step mechanics are
temporarily failing.

Current evidence already lines up with that contract:

- `README.md` describes `toas llm-input [head_id]` as model-facing projected
  messages
- `src/toas/operator_api.py` routes `llm_input_messages(...)` to
  `project_llm_input(...)` for the core message-body projection, and to the
  envelope/context-packet path when `--envelope` is requested
- `tests/test_graph.py` covers the main transforms: adjacent-user
  concatenation, assistant reasoning stripping, reasoning-only message
  elision, and control-lane exclusion
- `tests/test_operator_api.py` and `tests/test_history_scale_models.py` cover
  operator-facing llm-input projection across hot/default and selected-source
  cases

The core export claim is therefore plausible today: TOAS can render the
message-body input the model sees, and it can also show the extra packet/system
shaping that live generation adds through `--envelope`.

## Projection Delta

`transcript` and `llm-input` are sibling projections over the same durable
lineage.

The important difference is:

- `transcript` preserves transcript-shaped conversation rendering for humans
- `llm-input` preserves model-visible message shaping for the LLM interface

Current explicit transforms on the `llm-input` side include:

- coalescing adjacent user messages
- stripping assistant reasoning blocks
- dropping empty reasoning-only assistant messages
- excluding control-lane records

That delta is already well covered in tests, but only partially taught in user
facing help/docs.

## Remaining Gap

The remaining gap is mostly discoverability rather than deep semantics.

What still appears under-taught:

- command-local help does not yet fully teach why `transcript` and `llm-input`
  are different sibling surfaces
- `llm-input`'s outside-TOAS export role is more obvious from operator intent
  than from nearby docs/help text

Those are real but bounded follow-on pressures. They do not require keeping the
broader requirements task open.
