# Compaction Projections

TOAS treats compaction as a selectable working projection over durable message
history. It does not delete or rewrite source messages.

## Commands

`/compact` invokes the selected LLM through the normal generation boundary. It
asks for the versioned `compaction/handoff_v1` handoff schema, validates the
required sections, appends the accepted handoff as a projection message, writes
a `compaction_projection` record, and replaces `session.md` with the compact
working view.

`/abridge [--dry-run] [--threshold <n>]` is the former mechanical `/compact`.
It deterministically replaces large projected `RESULT` bodies with character
count placeholders. Existing uses of `/compact --threshold ...` must migrate to
`/abridge --threshold ...`.

## Adoption and History

An accepted assisted projection produces three durable facts:

- a user-facing projection message tagged with `provenance.source =
  "llm_compaction"`;
- its ordinary `llm_call` evidence, associated with that message;
- a `compaction_projection` record naming the selected projection message,
  source message IDs, source head, and prompt reference.

The active transcript binds at the selected projection message. Subsequent
generation therefore sees the handoff and later messages, while `events.jsonl`,
`toas history`, and `toas transcript` retain the uncompacted lineage. Config,
grants, queues, command context, workspace policy, and other non-message records
remain effective because the bind changes only conversational projection.

Re-running `/compact` projects the currently active working context. The prior
projection and its source chain remain inspectable.

## Handoff and Rehydration

The handoff includes the active objective, working state, plans, observations,
actions, change history, durable procedure updates, open questions, and one
immediately executable next step. Its final verbatim section includes:

- `### Files to Restore`, rendered as editable `$ cat <filename>` commands;
- `### Commands to Run`, rendered as editable `$ <command>` entries.

When `AGENTS.md` governs the workspace, the prompt requires `$ cat AGENTS.md`
even if it would otherwise be omitted. TOAS records this recipe but does not
execute it implicitly; restoration remains direct, visible operator-controlled
manipulation.

## Explicit Vim Successor Rotation

After a successful `/compact`, `:ToasRotate` (default `<leader>r`) prepares a
small successor transcript for the same logical line of work. The action asks
the runtime for a deterministic date-and-objective name, offers that name for
editing, and does nothing when the edited value is empty. On acceptance it
opens the collision-safe successor path in Vim.

The successor contains three ordinary user messages: the configured resolved
seed prompt, the exact selected handoff, and one callable YAML restoration
plan. `$ cat` entries become `read_file` operations, governing `AGENTS.md` is
first, and the remaining commands become `shell_script` operations. Rotation
does not execute the plan. The next ordinary step executes it; existing
first-failure recovery separates the failed retry from the still-staged
remainder, and no rotation-specific executor or step mode is involved.

The transition appends the successor messages, active transcript-path
override, any selected-surface rebind, and one `session_rotation` record as a
single durable journal transition. That record names the predecessor and
successor paths, selected
projection message, resolved seed reference, and successor boundary message
IDs. The graph keeps one lineage and one head; only the working bind and the
small Vim buffer move forward. A later `/compact` followed by another explicit
rotation repeats the same lifecycle. TOAS never rotates the visible transcript
because of size or time pressure.

Rotation safety is conservative:

| State | Result |
| --- | --- |
| selected compaction projection is the lineage tail | rotation may proceed |
| generation/run is active or cancelling | refuse without mutation |
| execution queue is pending, running, blocked, or awaiting approval | refuse without mutation |
| predecessor is missing, outside the workspace, or lacks the selected handoff | refuse without mutation |
| name prompt is cleared | cancel without creating or selecting a successor |
| successor filename already exists | choose the next numeric suffix; never overwrite |
| durable journal transition fails | remove the prepared successor and retain the predecessor selection |

This transcript lifecycle is separate from automatic `events.jsonl` segment
rollover. Journal rollover is storage hygiene; `:ToasRotate` is an explicit
operator projection transition.

## Failure Contract

Transport failure, a non-message response, or a handoff missing required
sections yields an explicit `[ERROR] compact: ...` result. No projection record
is selected and `session.md` is left unchanged. Transport-level failed
`llm_call` evidence remains available through the normal model boundary.

The same command path is used for native chat-message and `single_user_blob`
transports; request shaping remains owned by the existing model invocation
contract rather than by compaction.
