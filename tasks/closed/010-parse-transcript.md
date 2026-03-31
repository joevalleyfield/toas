## Goal

Parse `session.md` into a sequence of message objects without applying any history-aware interpretation.

## Scope

- Create `transcript.py`
- Implement:
  - `parse_transcript(text: str) -> list[Message]`

## Shape

Message:
- role: str
- content: str

## Rules

- Sections start with `## ROLE`
- Everything until next `##` is content
- Preserve transcript order exactly
- Parsing is pure: no log awareness, no alignment, no advancement
- Ignore malformed sections for now

## Non-Goals

- No tool execution
- No alignment against the log
- No callable detection beyond preserving raw content
- No strict validation

## Done When

- Can turn a simple transcript into structured messages without changing meaning or order
