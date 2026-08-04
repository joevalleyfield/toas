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

## Failure Contract

Transport failure, a non-message response, or a handoff missing required
sections yields an explicit `[ERROR] compact: ...` result. No projection record
is selected and `session.md` is left unchanged. Transport-level failed
`llm_call` evidence remains available through the normal model boundary.

The same command path is used for native chat-message and `single_user_blob`
transports; request shaping remains owned by the existing model invocation
contract rather than by compaction.
