Filed as: 260628-llm-input-envelope-visibility
FKA:
AKA: llm-input exact request mode; packet-inclusive llm input; model request visibility
Legacy index:

keywords: surface, investigation, follow-on, auditability, llm-input, projection, packet, usability

Parent: `260627-history-surface-user-intent-alignment`
Related: `260614-architecture-follow-through-coordination`; `260627-history-affordances-semantic-restaging`

# LLM-Input Envelope Visibility

## Current Reality

`toas llm-input` currently reflects the shared core message-body projection used
before generation:

- control content is dropped
- assistant reasoning blocks are stripped
- adjacent user messages are coalesced

That is valuable and mostly honest, but live generation may still add
deterministic packet/envelope/system material around that projected body before
the provider request is made.

For auditability, the unresolved question is whether the current surface is
complete enough as "show me what the model sees," or whether TOAS should offer
a stronger "show me the exact request shape" mode.

## Desired Reality

TOAS should keep the shared core message projection explicit while deciding
whether to expose an optional stronger envelope-inclusive view.

The likely contract shape is:

- default `llm-input`: projected conversation body
- optional stronger mode: include packet/system shaping that live generation
  adds above that shared body

## Focus

- decide whether the existing message-body view is sufficient for current
  operator diagnosis
- if not, define the smallest useful envelope-inclusive extension
- keep the distinction between "core message projection" and "full request
  packet" explicit in help/output wording
- avoid creating a misleading diagnostic surface that silently mixes the two
  without explanation

## Questions

- Should the first stronger mode show only the final message list, or also
  packet-quality/lens metadata provenance?
- Should the stronger view live under `toas llm-input --envelope`, another
  flag name, or a sibling diagnostic surface?
- What parts of packet shaping are stable enough to surface as operator-facing
  contract versus implementation detail?

## Disposition (2026-06-28)

Decision: **envelope-inclusive visibility is needed now, and is bounded enough
to implement immediately.**

Grounding from code:

- `toas llm-input` returns `project_llm_input(...)` — the shared core projection
  (`operator_api.llm_input_messages`).
- Live generation runs that *same* projection, then applies exactly one
  message-content transform above it: `shape_messages_for_packet(packet)`
  (`runtime/step_generation_runtime.py` `prepare_request`,
  `runtime/context_assembly.py`).
  - No durable lens artifacts → `shape_messages_for_packet` is identity, so the
    real request equals `llm-input`.
  - Lens artifacts present → it prepends exactly one synthetic
    `{"role": "system", ...}` "Context Assembly Packet" message (goal cue,
    folded outline, lens distillations, evidence refs, constraints, limits).
- A *second* transform exists at the wire: `single_user_blob` transport mode
  (`llm.py` `call_backend`) collapses the message list into one user blob. Per
  CLAUDE.md this channel is "a transport optimization, not a semantic fork," so
  it is **out of scope** for a message-content envelope view. It is noted in
  help wording rather than rendered.

Contract chosen (answers the three open Questions):

- Surface: `toas llm-input [head_id] --envelope` — a flag on the existing
  command, not a sibling command. Default output is unchanged.
- Content: the final message list as shaped for the packet (core projection plus
  the packet system message when durable artifacts exist). First slice shows the
  **final message list only**, not packet-quality/lens-provenance metadata — that
  provenance already has its own surface (`render_folded_packet_outline`).
- Stable contract vs implementation detail: the *presence and ordering* of the
  packet system message above the projected body is the operator-facing
  contract; the internal packet text layout stays implementation detail and is
  not promised stable.
- Wording: default labels itself "core message projection"; `--envelope` labels
  the added block as packet/system shaping and notes that transport modes (e.g.
  `single_user_blob`) may further re-render at the wire without changing message
  semantics.

## Exit Evidence

- explicit disposition on whether envelope-inclusive visibility is needed now
  — done above: yes.
- if yes, one bounded contract for exposing it — done above:
  `toas llm-input --envelope`.
- help/docs language that makes the difference between core message projection
  and full request shaping obvious — done: `cli.py` usage now labels the default
  as "core message-body projection" and `--envelope` as "packet/system shaping…
  above that core projection," noting transport re-rendering is not reflected.
- focused implementation slice or explicit deferral note justified by operator
  diagnostic value — done: `toas llm-input --envelope` implemented.

## Implementation (2026-06-28)

- `graph.lineage_messages` extracted so `project_llm_input` and the envelope path
  share one lineage source.
- `operator_api.llm_input_messages(..., envelope=False)`: when set, builds the
  context packet from durable lineage + events and returns
  `shape_messages_for_packet(packet)` (core projection plus the packet system
  message when durable lens artifacts exist; identical to core otherwise).
- Flag threaded through `cli_dispatch` (`--envelope` parse) →
  `cli.run_llm_input` (RPC payload + local) → `cli_commands` →
  `cli_surface_commands` → `runtime/request_ops` RPC op.
- Tests: `test_operator_api` (envelope prepends packet system message; matches
  core without artifacts), `test_cli_dispatch` (flag parse, default `False`),
  `test_cli_surface_commands` / `test_cli` / `test_daemon_ops` (threading).
  Full suite green at 100% coverage.

Status: **closed** — bounded contract delivered. Remaining open question
(packet-quality/lens-provenance in the envelope view) is intentionally deferred;
provenance already has `render_folded_packet_outline`.
