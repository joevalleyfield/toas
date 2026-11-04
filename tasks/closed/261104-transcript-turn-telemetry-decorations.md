Filed as: 261104-transcript-turn-telemetry-decorations
FKA:
AKA: turn telemetry decorations; transcript status decorations; turn header metadata; turn duration and model target; execution telemetry projection
Legacy index:

keywords: transcript, projection, telemetry, metadata, decorations, timing, duration, model-target, status

Parent: `260825-visible-transcript-turn-ids`
Related: `260929-transcript-turn-decorations`; `docs/notes/2026-10-04-transcript-decorators.md`; `260813-transcript-highlighting-design`; `260926-state-step-requirements`

# Transcript Turn Telemetry And Execution Status Decorations

## Intent

Project runtime execution facts and status telemetry directly into or below
transcript turn headings (`## TOAS:ASSISTANT`, `## TOAS:RESULT`, `## TOAS:STATE`),
providing operators with immediate in-buffer visibility into:
- **Timestamps**: when a turn was generated or executed;
- **Model Target**: which LLM target drafted the response (e.g., `anthropic/claude-3-7-sonnet`, `gemini-2.5-flash`, `local/qwen2.5-coder-7b`);
- **Execution Duration**: how long LLM generation or tool calls took to execute (`duration_ms` or humanized elapsed time);
- **Status / Outcome**: execution status matching live streaming/status line items (`status=OK`, `status=ERROR`, exit codes).

## Motivation

During interactive execution (via the Vim persistent channel or CLI streaming),
operators see live status items reporting the active model target, elapsed
seconds, and tool execution status. However, once a turn lands in `session.md`,
that telemetry evaporates from the working surface unless the operator manually
inspects `events.jsonl` or runs diagnostic CLI commands.

Capturing these facts in turn decorations makes the working transcript
self-describing, diagnostic-friendly, and informative without requiring a
secondary inspection window.

## Proposed Presentation Surfaces

### 1. Inline Header Decorations

Trailing within the turn header line:

````markdown
## TOAS:ASSISTANT [target=claude-3-7-sonnet t=11:28:45 duration=1.2s]
I will check the configuration file for you.

## TOAS:RESULT [status=OK duration=42ms]
[OK] read_file: config.json
````

*Pros*: Compact, preserves single-line turn headers, already permitted by the
canonical regex in `src/toas/transcript.py` (`_TRANSCRIPT_ROLE_MARKER_RE`).

### 2. Sub-Heading Metadata Line / Comment Block

Immediately following the turn header:

````markdown
## TOAS:ASSISTANT
<!-- toas: target=claude-3-7-sonnet timestamp=2026-11-04T16:28:45Z duration=1240ms -->
I will check the configuration file for you.

## TOAS:RESULT
<!-- toas: tool=read_file status=OK duration=42ms -->
[OK] read_file: config.json
````

*Pros*: Keeps the role header line clean, allows richer metadata dictionaries,
and can be cleanly folded or concealed using editor syntax definitions (e.g. Vim
`syntax match` / `conceal`).

### 3. Configurable Projection Density

Configurable via `toas.toml` (e.g., `transcript.telemetry_decorations = "off" | "inline" | "comment"`)
or CLI flags (`toas transcript --decorate=full`):
- `off` / `clean`: bare role markers (`## TOAS:ASSISTANT`);
- `inline`: compact inline bracketed summary (`[target=... duration=...]`);
- `comment`: structured HTML/Markdown comment line below the heading.

## Invariants & Design Principles

1. **LCP Invariance**:
   Decorations must never distort longest common prefix (LCP) calculation
   between working transcripts or between a working transcript and durable
   history. `_eq` and `_lcp` in `src/toas/transcript.py` must treat identical
   semantic roles as equivalent regardless of telemetry decorations.
2. **Model Projection Sanitization**:
   Telemetry decorations are presentation artifacts intended for the human
   operator and tooling. When shaping `llm-input` packets for inference, all
   telemetry decorations must be stripped to prevent prompt inflation and
   KV-cache prefix invalidation.
3. **Truthful Derivation from Canonical Records**:
   All projected telemetry must derive directly from durable event facts:
   - `llm_call` records for model target, endpoint, tokens, and duration;
   - `tool_request` / `tool_result` records for tool duration and outcome status;
   - Event timestamps for absolute timestamps.
   Values must never be synthetic or estimated.
4. **Round-Trip Preservation**:
   Existing authored decorations in `session.md` must be preserved across turn
   steps without being overwritten or mangled if the operator edits surrounding
   content.

## Acceptance Criteria

- Define configuration schema for selecting transcript telemetry decoration
  placement (`inline`, `comment`, or `off`).
- Implement transcript projection formatting that renders model target,
  timestamp, duration, and status from historical records into turn markers or
  sub-heading lines.
- Ensure `src/toas/transcript.py` parse/render functions round-trip telemetry
  decorations faithfully while maintaining 100% LCP equivalence.
- Ensure `llm-input` and prompt assembly completely strip telemetry decorations
  from model packets.
- Update syntax highlighting (`syntax/toas.vim` / textmate) to recognize and
  optionally conceal sub-heading telemetry comments.
- Achieve 100.00% statement coverage across all modified and new files.

## Resolution

- Defined `session.telemetry_decorations` configuration option (`"off"`, `"inline"`, `"comment"`) in `src/toas/config.py` and `src/toas/config_parsing.py`.
- Implemented `src/toas/runtime/turn_telemetry.py` providing duration humanization, ISO/local timestamp formatting, telemetry string assembly, telemetry comment parsing, sub-heading extraction, and result node decoration.
- Updated `src/toas/transcript.py`:
  - `parse_transcript` extracts leading sub-heading comments (`<!-- toas: ... -->`) into `message["telemetry_comment"]` and strips them from `message["content"]`.
  - `render_transcript` preserves and emits `telemetry_comment` immediately below turn markers for both spaced and unspaced rendering.
  - Verified LCP invariance (`_eq` and `_lcp`) across transcripts with and without telemetry decorations.
  - Verified `project_llm_input_from_messages` completely isolates model-input prompts from any presentation telemetry.
- Updated `src/toas/runtime/rendering_edges.py`:
  - `render_transcript_blocks` emits custom turn markers, result markers, and sub-heading telemetry comments for message and result nodes.
- Updated `src/toas/runtime/step_generation_runtime.py`:
  - `build_artifacts` decorates assistant turns with active model target, elapsed duration, and timestamp when `session.telemetry_decorations` is `"inline"` or `"comment"`.
- Updated Vim syntax highlighting in `vim/syntax/toas_transcript.vim` to recognize decorated result headings and link `toasTelemetryComment` to `Comment`; verified with Vader test suite in `tests/vim/transcript_syntax_probe.vader`.
- Verified 100.00% statement coverage across all 161 files in `./scripts/check.sh`.

