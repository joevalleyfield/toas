Filed as: 261111-toas-new-edit-sessions
FKA:
AKA: toas new; toas edit; session create/open convenience
Legacy index:

keywords: cli, session, transcript, editor, convenience, operator-ergonomics
Depends on:
Related: `260926-state-step-requirements`; `260803-session-rotation-lifecycle`

# toas new / toas edit: session create and open convenience

Status: OPEN; triage complete, spec locked, awaiting implementation spike

## Objective

Add two thin, file-only CLI commands that remove the friction of starting a
session, without introducing any runtime semantics, seed selection, or state
entry points:

- `toas new [slug] [--edit]` — create a fresh dated session file.
- `toas edit [path]` — open an existing session (or the most recent one) in
  an editor.

The motivation is the operator loop: cd into a project, start a transcript,
add a title, save, step. Today that is `mkdir -p .toas && touch
.toas/session-...md && $EDITOR ...` with the date/slug naming done by hand.
These commands make that one keystroke and keep it portable (works in clean
runners like Codex Cloud, unlike a machine-local shell function).

## Locked Scope

### `toas new [slug] [--edit]`

- `slug` is an OPTIONAL POSITIONAL argument (not a flag).
  - `toas new add-task-toas-new` -> `.toas/session-{yyMMdd-HHmm}-add-task-toas-new.md`
  - `toas new` -> `.toas/session-{yyMMdd-HHmm}.md` (datetime-only)
- Reuses the existing canonical naming + collision logic in
  `src/toas/runtime/session_rotation.py` (`suggested_continuation_name` /
  `_resolve_target_path`): slug normalization, `[A-Za-z0-9._-]` validation,
  ordinal suffix on collision (`-2`, `-3`, ...). This is the one accepted
  runtime coupling (the naming heuristic).
- `mkdir -p .toas`, then create the file EMPTY (no seed, no header). The
  first `toas step` boots the normal message bootstrap default exactly as
  today. Staying seed-agnostic is intentional (see Out of Scope).
- Prints the created path on success.
- `--edit`: after creating, hand off to the editor (same resolver as
  `toas edit`).

### `toas edit [path]`

- No argument -> open the MOST RECENT session:
  - sort `.toas/session-*.md` by the `yyMMdd-HHmm` date prefix parsed from
    the filename (durable, intent-bearing signal = "most recently started");
  - mtime is a secondary tie-break only;
  - if no dated `session-*.md` files exist, fall back to `.toas/session.md`
    (the `toas step` default).
- `toas edit <path>` -> open that explicit path; print a clear error if the
  path does not exist (do not silently create -- that is `toas new`'s job).
- Opens via the editor resolver below.

### Editor resolver (new; no existing config key)

Resolution order, first non-empty wins:
1. `TOAS_EDITOR` environment variable
2. `$EDITOR`
3. `vim` (hardcoded last-resort fallback)

No TOAS config-schema change is introduced; this is env-var driven. Note:
the operator originally considered a "fail if `TOAS_EDITOR` and `EDITOR`
are both unset" strict mode, but allowed `vim` as last resort, so the
resolver degrades to `vim` rather than failing. If strict mode is later
wanted, it is a one-line change to drop the `vim` fallback.

## Out of Scope (named follow-ons, NOT built here)

- **Fluid in/out of the STATE flow** (the operator's real want: move between
  conversation and `## TOAS:STATE/1` turns without hand-editing markers).
  Cross-reference: `260926-state-step-requirements` (ACTIVE state runtime
  family). The separate state runtime is disliked but not fixable yet; this
  task does not touch it.
- **Any seed-selection surface.** Message-seed choice is already handled by
  `/prompt` at step time; the bootstrap default is acceptable as-is. No
  `## TOAS:SEED` marker, no `toas seeds` command.
- **State entry-point generation.** `toas new` writes an empty file; it does
  not emit a `## TOAS:STATE/1` turn. Starting a state transcript remains a
  documented manual step (first turn `## TOAS:STATE/1`) until the fluid
  follow-on lands.

## Triage Findings (evidence)

- Not redundant: `toas session continue` requires a predecessor handoff;
  `toas session-path` only prints a path. Neither creates a fresh session or
  opens the most recent one.
- Message bootstrap fires at `src/toas/runtime/step_runtime.py` in
  `run_step`: `if not handoff.working_for_frontier and
  config.session.bootstrap_prompt_ref: return
  _bootstrap_seed_consequences(...)`. Seed is a single config value
  (`SessionPolicy.bootstrap_prompt_ref`, default
  `session-start/templates/pragmatic-default_v2`) with no per-session
  override.
- State mode routes by transcript content, not config:
  `src/toas/cli_session_commands.py` collects `state_turn_indices` from
  `parse_transcript` and dispatches to `_run_state_step` when present. An
  empty `toas new` file has no such turn, so it cannot reach state mode
  without a hand-typed marker.
- No existing editor config key or `execvp` invocation in the runtime; the
  resolver is entirely new (env-var driven).
- `active_config_overrides(events)` is an architectural violation (deriving
  config from event history) and is ruled out as a sticky-seed mechanism.

## Implementation Seams (to spike before coding)

- Command registration: `src/toas/cli_dispatch.py` (dispatch table) and
  `src/toas/cli_usage.py` (usage/help text + `_SUBCOMMAND_HELP`).
- Naming/collision reuse: `src/toas/runtime/session_rotation.py`
  (`suggested_continuation_name`, `_resolve_target_path`, `_NAME_RE`).
- "Most recent" resolution: new small helper (file-only, no graph/events
  reads) that globs `.toas/session-*.md` and sorts by filename date prefix.
- Editor handoff: `os.execvp` with the resolver above.

## Verification

- `uv run pytest` green; `./scripts/check.sh` green; 100.00% statement
  coverage on the new command module.
- Operator-perspective end-to-end (mandatory, file-only surface):
  - `toas new foo` in a dir without `.toas/` -> creates
    `.toas/session-...-foo.md`, prints path, file is empty.
  - `toas new` -> datetime-only name; second call same second -> ordinal
    suffix.
  - `toas edit` with no dated sessions -> opens `.toas/session.md`; with
    dated sessions -> opens the newest by filename date prefix.
  - `toas edit missing.md` -> clear error, no file created.
  - `TOAS_EDITOR=... toas new foo --edit` -> opens via `TOAS_EDITOR`; unset
    both -> degrades to `vim`.
- Test public seams (`toas new` / `toas edit` CLI entrypoints), not private
  `_` helpers.
