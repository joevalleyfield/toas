Filed as: 260804-successor-continuation-remediation
FKA:
AKA: post-compact continuation; successor transcript remediation; append-only handoff continuation
Legacy index:

keywords: runtime, implementation, active, correctness, transcript, projection, graph, vim, naming, boundaries

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

## Durable Fact Model

Keep independent facts independent:

- Append the selected handoff through the ordinary assistant-message path.
- Keep the `compaction_projection` record as separate projection evidence.
- Keep the active surface/path binding as a separate concern.
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

- [ ] `write_session_rotation_transition` and its tempfile-copy,
  `os.replace`, and `fchmod` journal manipulation are removed.
- [ ] Creating a successor leaves the existing event-log bytes as an unchanged
  prefix and adds facts only through ordinary append-only graph writers.
- [ ] The selected compact handoff is an assistant-role durable message and is
  projected under `## TOAS:ASSISTANT` in both the finalizing and successor
  transcripts.
- [ ] The successor seed is rendered exactly once, without a doubled
  `## TOAS:USER` marker.
- [ ] Successor composition uses structured/parsed messages rather than raw
  transcript concatenation.
- [ ] Restoration commands remain one ordered literal user `$ ...` sequence;
  no YAML tool lane is synthesized and no restoration command runs eagerly.
- [ ] Successor creation does not eagerly append seed, handoff, and restoration
  plan as three durable user messages.
- [ ] The predecessor remains recoverable and the successor continues the same
  logical lineage without creating a sibling operator or head by default.
- [ ] Surface binding, handoff selection, and any successor relationship are
  recorded separately rather than hidden in a monolithic graph transaction.
- [ ] The user-facing Vim/host/CLI surface uses continuation/successor language,
  with any retained rotation alias explicitly marked as compatibility-only.
- [ ] Safe-boundary refusal, editable deterministic naming, collision refusal,
  and preservation of the current transcript on failure remain covered.
- [ ] Focused tests include a cross-platform path that proves no POSIX-only
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
- event-log prefix/append proof across successful and failed continuation;
- inventory showing removal of the composite graph writer and POSIX-only mode
  manipulation;
- durable-record example demonstrating separate message, projection, binding,
  and optional successor facts;
- focused runtime/graph/Vim test results and the full-suite result;
- final naming and compatibility disposition for the old rotate surfaces.

