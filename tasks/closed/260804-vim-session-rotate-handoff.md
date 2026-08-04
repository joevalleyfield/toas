Filed as: 260804-vim-session-rotate-handoff
FKA:
AKA: rotate step step; post-compact successor; vim transcript rotation
Legacy index:

keywords: runtime, implementation, historical, usability, session, transcript, projection, vim, naming

Parent: `260803-session-rotation-lifecycle`
Depends on: `260803-llm-native-compaction-projection`; `260803-first-failure-plan-recovery`; `260803-seed-prompt-operator-stance`
Related: `260509-alternative-operator-frontends`; `260509-vim-first-operator-surface`

# Rotate A Compacted Handoff Into A Vim Successor Session

## Status

Completed on 2026-08-04.

## Objective

Add one ordinary Vim action that turns the selected post-`/compact` handoff
into a named successor transcript containing the configured seed, semantic
handoff, and a staged restoration plan. The resulting interaction should be:

```text
/compact
<leader>s     generate handoff
<leader>r     rotate into suggested successor transcript
<leader>s     execute staged restoration plan
<leader>s     continue conversation
```

This is transcript hygiene for the same logical line of work. It must not
create a sibling operator, parallel session, implicit branch, or special step
semantics.

## Interaction Contract

- Expose `:ToasRotate` and a default `<leader>r` mapping.
- Refuse rotation while a generation, tool plan, cancellation, watcher, or
  unresolved/indeterminate execution is active.
- Ask the runtime for a rotation transition; keep the Vim plugin responsible
  only for invoking it, offering the suggested name for editing, and opening
  the returned successor path.
- Suggest a collision-safe transcript name from the handoff's current
  objective. Present it as an editable default rather than silently choosing.
- After rotation, leave restoration staged but unexecuted. The next ordinary
  `ToasStep` executes it; the following ordinary step continues model work.
- Failure at any point leaves the predecessor buffer, active transcript path,
  and selected projection unchanged.

## Successor Transcript Composition

Compose the successor explicitly from:

1. the configured seed prompt and its resolved prompt reference/version;
2. the selected LLM compaction handoff;
3. a directly manipulable restoration plan derived from the handoff's
   `Files to Restore` and `Commands to Run` sections.

Restoration translation rules:

- `$ cat AGENTS.md` is restored first whenever it governs the workspace;
- `$ cat <path>` entries become ordinary `read_file` calls;
- remaining `$ <command>` entries become ordinary shell calls;
- preserve source order within each section;
- render the result through the existing callable plan lane, not a new
  rotation-only execution protocol;
- do not execute any restoration operation during rotation.

Because restoration is an ordinary multi-tool plan, existing first-failure
recovery owns partial completion: completed restoration becomes results, the
failed operation becomes the editable standalone retry, and remaining calls
stay staged as the forward plan.

## Runtime And Durable Contract

- Runtime/operator semantics own safe-boundary validation, name suggestion,
  successor composition, file creation, active-path selection, and the
  append-only lifecycle record.
- Record predecessor path, successor path, selected compaction projection,
  seed prompt reference, successor boundary message IDs, and timestamp or
  equivalent ordering evidence.
- Continue the existing message lineage. Rotation must not create another
  head, merge fact, operator identity, or concurrency surface.
- Bind subsequent working/model context at the successor boundary while
  retaining complete recovery through durable event history.
- Reopening either predecessor or successor must remain comprehensible through
  ordinary session, transcript, history, and LLM-input inspection surfaces.

## Naming Contract

- Derive the suggested slug from `## Current Objective`, using a deterministic
  normalization and a bounded readable length.
- Include enough date or sequence information to avoid accidental reuse.
- Resolve collisions without overwriting an existing transcript.
- Keep the accepted path workspace-relative and within the configured session
  transcript area unless the existing explicit path policy authorizes more.
- Persist the accepted name/path, not merely the original suggestion.

## Acceptance Criteria

- [x] `:ToasRotate` and `<leader>r` implement the rotate-step-step interaction
  without introducing a special step command.
- [x] The runtime rejects unsafe boundaries with a precise diagnostic and no
  file, config, projection, or lifecycle mutation.
- [x] A valid selected compaction projection produces a successor containing
  the resolved seed, exact handoff, and staged restoration plan.
- [x] `AGENTS.md`, file restoration order, command order, quoting, and paths are
  preserved in representative fixtures.
- [x] The first ordinary step executes the staged plan and inherits existing
  first-failure split/retry/remaining behavior; the next ordinary step invokes
  normal generation.
- [x] Suggested names are readable, editable, deterministic for a fixture, and
  collision-safe; cancellation at the name prompt is a no-op.
- [x] Rotation appends durable predecessor/successor/projection/seed evidence
  and continues the same graph lineage without creating a sibling head.
- [x] The predecessor remains recoverable and the successor is selected and
  opened in Vim after success.
- [x] CLI/runtime coverage proves the lifecycle semantics independently of Vim;
  Vim tests prove only the thin action, name prompt, buffer switch, and errors.
- [x] Multiple compact/rotate cycles keep each active transcript bounded while
  full history remains inspectable.

## Non-Goals

- Automatically running restoration during rotation.
- Adding a rotation-specific tool executor or replay-by-reference mechanism.
- Solving automatic size-pressure rotation policy in this slice.
- Implementing parallel sessions, multiple operators, merges, or storage
  segment rotation.
- Asking a second LLM solely to name the successor transcript.

## Allowed Write Surfaces

- session lifecycle/operator semantics under `src/toas/runtime/`;
- `src/toas/graph.py` for the append-only rotation boundary record;
- session command/request adapters needed to expose the runtime transition;
- `vim/plugin/toas.vim` for the thin action, editable name prompt, and buffer
  switch;
- focused runtime, graph, CLI, and Vim tests under `tests/`;
- session lifecycle/projection documentation;
- this task, its requirements parent, and generated `tasks/WORKBOARD.md`
  sections.

## Required Completion Evidence

- settled rotation record and successor composition examples;
- safe-boundary state matrix with refusal proofs;
- before/after predecessor, successor, history, transcript, and LLM-input
  fixtures;
- deterministic naming and collision fixtures;
- Vim interaction proof for success, edited name, cancellation, and failure;
- first-failure restoration proof using the existing plan recovery lifecycle;
- repeated-rotation bounded-working-set fixture;
- focused and full-suite results.

## Completion Evidence

- `toas.runtime.session_rotation` now owns a two-phase transition: a
  mutation-free suggestion request followed by an accepted-name commit. It
  validates the selected projection tail, active runs and queues, predecessor
  containment/content, restoration recipe, and collision-safe target before
  changing selection.
- The successor is three ordinary user messages: the resolved configured seed,
  exact semantic handoff, and callable YAML restoration plan. Fixtures prove
  governing `AGENTS.md` first, quoted paths, deduplication, file order, command
  order, and `read_file` / `shell_script` translation.
- The journal transition atomically appends the three successor messages, the
  active transcript-path override, any selected-surface rebind, and a
  `session_rotation` record containing
  predecessor, successor, projection, seed reference, and boundary IDs. A
  forced replace failure leaves the old journal byte-identical and removes the
  prepared successor.
- Runtime fixtures prove one graph head, successor-bound context, preservation
  of the predecessor file and complete message lineage, ordinary first-failure
  retry/remainder behavior, and two explicit compact/rotate cycles with a
  bounded second transcript.
- `:ToasRotate` and `<leader>r` use the existing request transport, offer the
  runtime suggestion as an editable default, treat an empty edit as cancel,
  refuse a Vim-known active run, and open the returned successor. Vader proof:
  4 cases, 12 assertions.
- Focused runtime/request coverage: 68 passed. Changed-file Ruff checks passed.
  Full suite: 2,786 passed, 9 deselected, 100% coverage.
