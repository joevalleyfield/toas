Filed as: 261105-user-turn-and-result-telemetry-decorations
FKA:
AKA: user turn telemetry decorations; result telemetry decorations; result provenance id; human turn dwell duration; result outline status
Legacy index:

keywords: transcript, telemetry, result-decorations, user-turn-decorations, dwell-time, provenance, outline-navigation

Parent: `260825-visible-transcript-turn-ids`
Related: `261104-visible-turn-ids-and-compact-headers`; `261104-transcript-turn-telemetry-decorations`; `261104-vim-telemetry-decorations-streaming-reconciliation`

# User Turn And Result Telemetry Decorations

## Status

Closed on 2026-11-05. Result blocks now receive hierarchical provenance IDs
(`parent_handle.p#.o#`), tool target, execution duration, timestamp, and status
(`OK` / `ERROR`) in their heading lines. Structural `## TOAS:USER` turns enclosing
results remain bare, and human-authored `## TOAS:USER` turns receive deterministic
turn handles, invocation timestamps, and dwell duration heuristics (omitted on the
first turn of fresh sessions).

## Intent

Extend transcript telemetry decorations to `## RESULT` blocks and human `## TOAS:USER`
turns:
1. **`## RESULT` Blocks**: Stamp execution telemetry and hierarchical parent provenance
   IDs (`parent-turn-label.p#.o#` or `parent-turn-label.o#`), including `OK` or `ERROR`
   in the heading line (e.g. `## RESULT [bravo.p1.o1 OK shell 08:14:02 45ms]`) so outcomes
   are immediately visible in buffer text and markdown TOC / outline views.
2. **Structural `## TOAS:USER` Turns**: Keep bare (no stamp, no unique handle) when they
   exist purely as frontier boundaries enclosing tool results without user-authored prose.
3. **Human `## TOAS:USER` Turns**: Stamp human user turns with turn handle, invocation
   timestamp, and dwell/working duration heuristic ($\Delta T_{\text{human}} = T_{\text{step}} - T_{\text{prev\_turn\_end}}$),
   e.g. `## TOAS:USER [delta 08:14:15 4m12s]`, cleanly omitting duration on the first turn
   of a fresh session (`## TOAS:USER [alpha 08:14:00]`).

## Acceptance Criteria

1. `## RESULT` blocks rendered under telemetry decoration settings (`compact`, `inline`, etc.)
   feature hierarchical provenance IDs resolved from parent message turn handles:
   `parent_handle.p{plan}.o{op}` (or `parent_handle.o{op}` when 1 plan), along with tool
   name, duration, status (`OK` / `ERROR`), and timestamp.
2. Markdown heading outlines reflect tool execution outcomes (`OK` / `ERROR`) directly
   in `## RESULT` lines.
3. Pure structural `## TOAS:USER` blocks generated to enclose results remain bare.
4. Human-authored `## TOAS:USER` turns receive telemetry stamps with handle, timestamp,
   and dwell duration when preceding events exist in session history.
5. 100.00% statement coverage preserved across the codebase under `./scripts/check.sh`.

## Verification

1. Unit tests:
   - `tests/test_runtime_turn_telemetry.py`: added tests covering `format_result_hierarchical_id`,
     `compute_human_dwell_ms`, `is_human_user_turn`, `decorate_user_turn_node`, compound durations in `humanize_duration`,
     and regex matching.
   - `tests/test_runtime_step_runtime.py`: added end-to-end telemetry tests for `_decorate_step_telemetry`,
     fresh session user turn (duration omitted), second human turn with dwell duration, and result hierarchical provenance.
   - `tests/test_graph.py`: added tests verifying message event persistence preserves marker, duration_ms, and turn_id.
2. End-to-end artifact inspection:
   - Concrete `run_step` and `render_transcript_blocks` execution verified:
     - Turn 1: `Role: user, Turn ID: alpha, Marker: ## TOAS:USER [alpha 19:43:55]`
     - Turn 1 Result: `## TOAS:USER\n\n## RESULT [alpha.p1.o1 OK shell]\n\n[OK] shell: exit=0...`
     - Turn 2: `Turn ID: charlie, Marker: ## TOAS:USER [charlie 19:43:55 4m10s]`
3. Suite & coverage verification:
   - `./scripts/check.sh` passed with 3,768 passed, 0 failures, and 100.00% statement coverage across all 161 source files (24,633 statements).
