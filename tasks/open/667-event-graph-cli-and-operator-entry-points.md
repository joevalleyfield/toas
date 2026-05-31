# Event graph CLI and operator entry points
keywords: surface, implementation, active, usability, graph, cli, projection, operator

## Goal

Add non-Python entry points for the event graph renderer so operators can inspect durable message forests outside Python and from inside a transcript.

## V1 Scope

- Add `toas graph [--projection temporal|consequence]`.
- Add `/graph [--projection temporal|consequence]` as an operator command.
- Default to temporal projection.
- Render the whole message forest from `.toas/events.jsonl`.
- Use deterministic labels shaped as `<id> <role-char> <first-content-line>`, capped at 66 characters.
- Keep projection selection explicit through `--projection`; no short aliases yet.

## Out of Scope

- Event filtering.
- Message summarization or generated tight labels.
- Head selection, subtree selection, or lineage-only views.
- RPC/daemon graph command support unless required by existing CLI fallback seams.
- Model-addressable `event_graph` tool.

## Acceptance Criteria

- `toas graph` renders the temporal whole-forest view from the current workspace event log.
- `toas graph --projection consequence` renders the consequence projection.
- `/graph` and `/graph --projection consequence` return inert result content suitable for transcript projection.
- Invalid projection values produce clear usage-style errors.
- Tests cover CLI dispatch, operator command handling, label truncation, role markers, and mixed message/non-message event logs.

## Related

- `659` roots-on-top event graph visualization renderer foundation.
