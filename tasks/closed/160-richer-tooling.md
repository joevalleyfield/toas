## Goal

Expand the tool layer from a proof-of-shape into a genuinely useful capability surface.

## Scope

- Add more than one practical built-in tool
- Strengthen execution policy and safety boundaries
- Enrich tool result payloads beyond flat text
- Keep transcript-visible results derived from durable structured facts

## Why

The runtime mechanics are now coherent, but the tool surface is still too small to justify the architecture. Richer tooling is the shortest path from “interesting operator” to “actually useful system.”

## Planned Tasks

- `161`: bounded shell tool
- `162`: repo read/search tools
- `163`: structured tool result records
- `164`: canonical result projection from structured tool outputs

## Non-Goals

- No giant kitchen-sink library
- No hidden prompt-defined tools
- No unsafe unrestricted command execution surface

## Done When

- The tool layer includes a small set of genuinely useful built-in tools
- Tool execution has explicit safety boundaries
- Durable tool records carry richer structured results
- Transcript-visible `RESULT` blocks remain projections of those durable facts
