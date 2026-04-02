# TOAS

TOAS is a transcript-oriented operator over durable history.

It exists in part to make a locally available but behaviorally awkward model usable through stronger operator semantics, durable state, and better control over prompting, tool use, and replay.

The system is built around three things:
- `session.md`: the user-controlled working transcript
- `events.jsonl`: append-only durable state
- `toas step`: a one-step operator that accepts transcript state and resolves one layer of consequence

It is not a hidden conversation loop. It is a small operator runtime over a message graph plus related operator records.

## Current Features

- graph-native message history with branching
- durable `jump`, `head`, and `anchor` control records
- lineage-aware `step`
- local OpenAI-compatible generation
- registry-backed tool execution
- versioned prompt assets
- metadata-backed session-starting prompt family
- dynamic capability-advertisement prompts
- transcript projection, rebuild, and history inspection commands

## CLI

- `toas step`
  Accept transcript edits, append new durable state, and print only newly produced consequences.
  If the frontier message ends with a line of the form `$ some_shell_command`, TOAS executes that command as an explicit user shell action and prints its result as a `RESULT` block.
- `toas jump <bind_index>`
  Set manual transcript binding in message-view space.
- `toas head <head_id>`
  Select the current lineage head.
- `toas heads`
  List known lineage heads.
- `toas transcript [head_id]`
  Print a lineage-backed transcript projection.
- `toas llm-input [head_id]`
  Print model-facing projected messages as transcript-style blocks.
- `toas prompt <kind>/<version>`
  Print a named prompt asset so it can be inserted explicitly into the transcript.
- `toas prompts [prefix]`
  Browse prompt assets and one-line descriptions by library prefix.
- `toas history [limit]`
  Print selected head, bind state, heads, and recent event summaries.
- `toas rebuild [head_id]`
  Rewrite `session.md` from projected history and emit a useful anchor.

## Shell Policy

- A frontier line of the form `$ ...` is treated as explicit user shell intent.
- That user-shell path is not restricted by TOAS command allowlists or workspace fences.
- The registry `shell` tool remains bounded because it is model-addressable capability rather than direct user intent.

## Runtime Defaults

The local model client defaults to:

- `TOAS_LLM_BASE_URL=http://localhost:8080/v1`
- `TOAS_LLM_API_KEY=not-needed`
- `TOAS_LLM_MODEL=qwen3.5-35b-a3b`

That matches a local OpenAI-compatible `llama-cpp` style setup.

## Development

Run tests with:

```bash
uv run pytest
```

## Key Docs

- [docs/vision.md](/Users/tim/Documents/Projects/toas/docs/vision.md)
- [docs/roadmap.md](/Users/tim/Documents/Projects/toas/docs/roadmap.md)
- [docs/llm-notes.md](/Users/tim/Documents/Projects/toas/docs/llm-notes.md)
- [docs/protocol-notes.md](/Users/tim/Documents/Projects/toas/docs/protocol-notes.md)
- [AGENTS.md](/Users/tim/Documents/Projects/toas/AGENTS.md)
