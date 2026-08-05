Filed as: 260804-successor-continuation-remediation
FKA:
AKA: post-compact continuation; successor transcript remediation; append-only handoff continuation
Legacy index:

keywords: runtime, implementation, historical, correctness, transcript, projection, graph, vim, naming, boundaries

Parent: `260803-session-rotation-lifecycle`
Depends on: `260803-llm-native-compaction-projection`; `260803-seed-prompt-operator-stance`
Related: `260804-vim-session-rotate-handoff`; `260804-automatic-hot-journal-rollover`

# Untangle Successor Continuation From Journal Rotation

## Objective

Remediate the first post-`/compact` successor implementation so explicit
working-transcript continuation is a projection/lifecycle operation over one
append-only durable lineage, not a rewrite of `.toas/events.jsonl`. Preserve
the useful edit-step-step Vim interaction while giving the predecessor and
successor transcripts the intended conversational roles and keeping literal
user restoration commands intact.

This task supersedes the implementation contract recorded by the completed
`260804-vim-session-rotate-handoff` task where that contract conflicts with
the clarified model below. The completed task remains historical evidence of
what landed and why this remediation exists.

## Terminology And Separation

- `/compact` produces a semantic handoff projection. It does not replace the
  working transcript and does not itself create a successor transcript.
- An explicit **continuation** or **successor** action creates the next bounded
  user-visible working transcript for the same logical lineage.
- **Rotation** is reserved for the automatic physical rollover of the hot
  `.toas/events.jsonl` journal, tracked by
  `260804-automatic-hot-journal-rollover`.
- Native tool calling, alternate callable lanes, transcript lifecycle, and
  durable graph storage remain orthogonal concerns.

User-facing command, request-operation, module, and help names should converge
on `continue`/`successor` language. Any temporary compatibility alias for
`:ToasRotate`, `session_rotate`, or `run_session_rotate` must be deliberate,
documented, and tested rather than silently preserving the conceptual mix-up.

## Required Transcript Shapes

After `/compact`, the finalizing transcript projects the handoff as assistant
context:

```markdown
## TOAS:USER
/compact

## TOAS:ASSISTANT
# Handoff Summary
...
```

The successor transcript is composed from parsed messages, not concatenated
transcript strings:

```markdown
## TOAS:USER
<seed exactly once>

## TOAS:ASSISTANT
# Handoff Summary
...

## TOAS:USER
$ cat AGENTS.md
$ cat path/to/file
$ command-to-resume
```

The final user message remains literal user-command-shaped text. Multiple
`$ ...` commands already execute sequentially when stepped; this task must not
translate them into YAML `read_file`/`shell_script` operations or execute them
during successor creation. First-failure recovery for that command sequence is
deferred.

Successor rendering must also preserve the working surface's text conventions
instead of deriving them from the host OS. Infer the newline convention from
the predecessor session/transcript when it is available; in particular, an
LF-shaped session edited by MSYS2/Git-for-Windows Vim must produce an LF-shaped
successor. Projection-facing paths in the restoration commands use forward
slashes on every platform, including Windows, rather than leaking native
backslashes into `$ cat ...` lines. If the predecessor has no usable newline
signal or has mixed endings, settle and document a deterministic fallback
without making Windows imply CRLF.

## Durable Fact Model

Keep independent facts independent:

- A predecessor transcript is eligible when its last user turn ends in
  `/compact` and the following/final turn is a handoff-shaped assistant turn.
  This transcript-local evidence is authoritative; a selected surface or
  selected `compaction_projection` is not an eligibility prerequisite.
- Append the compact handoff through the ordinary assistant-message path.
- Keep the `compaction_projection` record as separate projection evidence.
- Keep active surface/path selection separate. Continuation does not emit a
  `surface_bind` or `config_override`; the explicit predecessor/successor path
  and Vim's active-buffer step resolution identify the working transcript.
- If durable predecessor/successor identity is necessary, add only a small
  append-only relationship or boundary record.
- Create the successor filesystem surface outside `graph.py`.

Remove `write_session_rotation_transition`. Do not rename it into another
composite writer. In particular, continuation must not copy and atomically
replace the event journal, call `fchmod`, truncate history, or pre-materialize
the seed, handoff, and restoration plan as a batch of durable user messages.
Normal transcript synchronization should append the newly introduced messages
when the successor is stepped, with only the minimal lifecycle/binding evidence
written earlier when that evidence is actually required.

## Acceptance Criteria

- [x] `write_session_rotation_transition` and its tempfile-copy,
  `os.replace`, and `fchmod` journal manipulation are removed.
- [x] Creating a successor leaves the existing event-log bytes as an unchanged
  prefix and adds facts only through ordinary append-only graph writers.
- [x] The compact handoff is an assistant-role durable message and is
  projected under `## TOAS:ASSISTANT` in both the finalizing and successor
  transcripts.
- [x] The successor seed is rendered exactly once, without a doubled
  `## TOAS:USER` marker.
- [x] Successor composition uses structured/parsed messages rather than raw
  transcript concatenation.
- [x] Restoration commands remain one ordered literal user `$ ...` sequence;
  no YAML tool lane is synthesized and no restoration command runs eagerly.
- [x] The successor inherits the predecessor transcript's detected newline
  convention; an LF MSYS2/Git-for-Windows Vim fixture remains LF, and newline
  choice is not inferred merely from the operating system.
- [x] Paths projected into user restoration commands are normalized to forward
  slashes on Windows as well as Unix-like hosts.
- [x] Successor creation does not eagerly append seed, handoff, and restoration
  plan as three durable user messages.
- [x] The predecessor remains recoverable and the successor continues the same
  logical lineage without creating a sibling operator or head by default.
- [x] Surface selection, compaction evidence, and the successor relationship remain
  recorded separately rather than hidden in a monolithic graph transaction.
- [x] The user-facing Vim/host/CLI surface uses continuation/successor language,
  with any retained rotation alias explicitly marked as compatibility-only.
- [x] Safe-boundary refusal, editable deterministic naming, collision refusal,
  and preservation of the current transcript on failure remain covered.
- [x] Focused tests include a cross-platform path that proves no POSIX-only
  permission operation is required, followed by the full suite.

## Non-Goals

- Automatic rollover or segmentation of `.toas/events.jsonl`.
- Automatic compaction or continuation based on transcript size.
- First-failure/continue recovery inside a multi-command user `$` sequence.
- Converting restoration commands to a YAML, JSON, fenced-exec, or native-tool
  calling lane.
- Parallel sessions, sibling operators, merge semantics, or new heads.
- Reopening the semantic handoff format itself beyond role-correct projection.

## Allowed Write Surfaces

- `src/toas/runtime/session_rotation.py`, including rename/split into a
  continuation-oriented module;
- `src/toas/runtime/session_step_edges.py` and projection synchronization seams
  needed for assistant-role handoff append;
- `src/toas/graph.py` only to remove the composite writer and, if justified,
  add a minimal append-only successor fact;
- CLI, host request-contract/dispatch, daemon, and Vim plugin surfaces needed
  to rename or compatibility-wrap the explicit continuation action;
- transcript/prompt composition helpers needed to compose parsed messages;
- focused graph, runtime, CLI/host, daemon, transcript, and Vim tests;
- lifecycle/operator documentation, this task, its parent task, and generated
  `tasks/WORKBOARD.md` sections.

## Required Completion Evidence

- before/after predecessor and successor transcript fixtures showing exact
  roles, one seed marker, and literal restoration commands;
- LF and CRLF predecessor fixtures plus an MSYS2/Git-for-Windows-oriented case
  proving inherited line endings and forward-slash restoration paths;
- event-log prefix/append proof across successful and failed continuation;
- inventory showing removal of the composite graph writer and POSIX-only mode
  manipulation;
- durable-record example demonstrating separate message, projection, binding,
  and optional successor facts;
- focused runtime/graph/Vim test results and the full-suite result;
- final naming and compatibility disposition for the old rotate surfaces.

## Completion Evidence

Completed 2026-08-04.

- Successful `/compact` retains command request/result evidence while both the
  durable message and transcript projection use assistant role. The original
  transcript is appended through the ordinary projection path and is not
  replaced.
- Continuation eligibility is discovered from the explicit predecessor
  transcript: the last user block ends in `/compact`, followed by a final
  `# Handoff Summary` assistant block. Missing, stale, or unrelated
  `compaction_projection` and surface records do not gate the action.
- `write_session_rotation_transition`, journal tempfile copying,
  `_replace_session_rotation_log`, and `fchmod` were removed. Successful
  creation appends one `session_successor` record; tests prove the preexisting
  event bytes remain an unchanged prefix and no messages, config override, or
  surface bind are appended eagerly.
- Successor rendering composes parsed messages in user/assistant/user order,
  preserves literal ordered `$ ...` commands, places `AGENTS.md` first when
  applicable, normalizes restored file paths to forward slashes, and renders
  the seed exactly once.
- LF, CRLF, mixed-ending fallback, and Windows-backslash fixtures prove that
  newline choice comes from predecessor content (mixed defaults to LF) rather
  than host OS behavior.
- A matching `session_successor` record binds step reconciliation immediately
  after its continuation parent. The first ordinary successor step therefore
  synchronizes the seed, handoff, and restoration messages; repeated
  continuations remain on one head.
- `session_continue`, `run_session_continue`, and `:ToasContinue` are canonical.
  `session_rotate`, `run_session_rotate`, and `:ToasRotate` remain tested
  compatibility aliases; `<leader>r` now invokes `:ToasContinue`.
- Focused continuation coverage: 30 passed, 100% for
  `toas.runtime.session_rotation`.
- Focused transport/host coverage: 77 passed. Focused Vim action: 5/5 cases,
  14/14 assertions.
- Full suite: 2,799 passed, 9 deselected, 100% coverage.
