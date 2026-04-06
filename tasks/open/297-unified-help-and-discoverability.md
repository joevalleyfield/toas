## Goal

Make all session capabilities discoverable from a single location by assembling the existing registries into a unified help output.

## Problem

The system has several independent capability registries with no shared presentation layer:

- CLI subcommands — USAGE string in `cli.py`, flat and static
- Slash commands (`/pwd`, `/cd`, `/workspace`, `/prompts`, `/prompt`, `/outline`, `/compact`, `/extract`, `/config`) — implicit if-chains in `step.py`, not enumerated anywhere
- Tool registry (`echo`, `shell`, `read_file`, `search`, `replace_block`) — only reachable via capability prompt
- Shell allowlist — now surfaced in capability prompt but not directly queryable
- Config keys and valid values — `valid_config_keys()` exists in `config.py` but has no CLI surface; `/config show` shows current values, not the schema

No single answer exists to "what can I do from inside a session?"

## Approach

Unify by assembling — not by merging the registries themselves. Each registry stays where it belongs. A new help surface reads from all of them and presents a coherent picture.

**Option A: enrich `toas help`** — extend the existing `run_help` CLI command to include tools, slash commands, and config keys below the existing USAGE block.

**Option B: add `/help` slash command** — a new in-session slash command that renders the same content as a TOAS result block, visible in the transcript.

Both are worth doing; A is the baseline, B makes it accessible without leaving the session.

## Slash command registry

Before surfacing slash commands, they need to be enumerable. The if-chain in `step.py` is the current dispatch; a small registry (name → usage line + description) should be extracted alongside it so both the help surface and future tooling can iterate over it.

This does not need to be a full schema — a simple list of `(name, usage, description)` tuples is enough for display.

## Scope

1. Extract a slash command registry (name, usage string, one-line description) from the if-chain in `step.py`
2. Enrich `toas help` to show:
   - existing CLI subcommands (as now)
   - available slash commands with usage lines
   - available tools with required args
   - available config keys
3. Add a `/help` slash command that renders the same content as a result block
4. No changes to how any of the registries work — display only

## Non-Goals

- No unified schema over tools and slash commands
- No changes to dispatch logic
- No capability prompt changes (the dynamic prompts already serve the model-facing surface)

## Future Consideration

The slash command registry extracted here is a natural first step toward partial or full unification of CLI and slash-command entry points into a shared capability set, with explicitly chosen exceptions where the inside/outside-session distinction is load-bearing.

## Done When

- `toas help` shows CLI commands, slash commands, tools, and config keys in one output
- `/help` in the transcript produces the same information as a result block
- All sections are driven from live data (registry, `valid_config_keys()`, `REGISTRY`) not hardcoded strings
