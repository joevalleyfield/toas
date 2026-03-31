
## Goal

Parse `session.md` into a sequence of message objects.

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
- Ignore malformed sections for now

## Non-Goals

- No tool execution
- No YAML parsing yet
- No strict validation

## Done When

- Can round-trip a simple session into structured messages
