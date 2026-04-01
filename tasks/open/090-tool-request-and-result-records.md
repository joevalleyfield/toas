## Goal

Represent tool requests and tool execution results as durable event-log records related to message history.

## Scope

- Define durable record shapes for extracted tool requests and tool results
- Extract a tool-request record from a callable accepted message event
- Record tool execution outcomes as result records
- Serialize canonical `RESULT` blocks from result records for stdout

## Behavior

- A callable transcript tail is first accepted as a message event
- Operator extracts the callable structure into a tool-request record
- Execution appends a tool-result record
- `stdout` serializes canonical result text from those records
- The user may keep, rewrite, absorb, or discard that visible result text in the transcript buffer

## Rules

- Tool request/result records are not message events
- Tool request/result records do not directly reproject into prior transcript content
- Result serialization is for forward append convenience, not transcript authority
- The relationship between message events and tool records must remain explicit

## Non-Goals

- No broad tool registry yet
- No sandbox/policy framework beyond the minimal path needed to record request/result facts

## Done When

- Tool requests leave durable non-message records in history
- Tool results leave durable non-message records in history
- `RESULT` blocks are produced from those records without treating them as ordinary assistant dialogue
