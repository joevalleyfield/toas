Filed as: 260920-one-shot-control-ingress-disposition
FKA:
AKA: --control disposition; injected control; ephemeral control ingress
Legacy index:

keywords: design, active, transcript, control, policy, lineage, cli, compatibility

Parent: `260920-branch-projected-policy-program`
Related: `260920-lcp-direct-policy-deltas`; `260920-lcp-policy-reevaluation-contract`; `260920-transcript-control-state-contract`

# Decide the Fate of One-Shot Control Ingress

Determine whether `toas step --control` remains a useful operator-facing
convenience, becomes transcript-materializing, is restricted to transient
queries, or is retired so no non-functional transcript-control vestige remains.

## Current Reality

`toas step --control <slash-command>` and
`operator_api.step_once(control=...)` append a `TOAS:CONTROL` turn only to the
in-memory input for one step. The command is materialized as a durable control
message, but its text is not written to `session.md`. This is an external
CLI/API surface, not merely an acceptance-test harness helper.

Consequently, a subsequent transcript/LCP reconstruction cannot see the
control source. Existing endpoint/config workflows relied on its
history-forward durable side effects; the Phase-1 policy slice preserves that
compatibility behavior for this ingress.

## Desired Reality

Every lasting policy-changing control has an intelligible source and replay
story. A branch-forward transcript policy reducer must not rely on a control
that is absent from the reconstructed transcript. If a one-shot ingress stays,
its semantics and utility must be explicit rather than an accidental exception.

## Questions and candidate dispositions

1. Materialize the supplied control into the selected working transcript before
   stepping. It then behaves like ordinary authored `TOAS:CONTROL` content and
   receives normal LCP/branch semantics.
2. Retain it only for explicitly transient read-only/query operations. It
   cannot write policy-changing durable state.
3. Retire `--control` and direct callers to edit the transcript or use a
   purpose-built query command.
4. Establish a distinct, durable non-transcript command lane only if it has a
   demonstrated operator need and its history/policy semantics can be made
   truthful. This is not a default direction.

## Risks

- Keeping current behavior leaves policy-changing history with a source that
  cannot be replayed from the user-controlled transcript.
- Automatically writing every one-shot command into `session.md` may surprise
  callers who expected an inspection action without transcript mutation.
- Removing the surface without surveying callers could break editor, daemon,
  or automation workflows.

## Evidence needed

- Inventory direct CLI/API/editor/daemon callers and classify their commands
  as query, transient action, or lasting policy mutation.
- Exercise each candidate disposition against endpoint/target authoring and
  direct assistant restep after an inserted policy control.
- Select and document one ingress rule in the transcript control-state
  contract; follow with a narrowly scoped implementation task if needed.

## Next Action

Perform the caller inventory before choosing a disposition. Until then,
preserve the compatibility path but do not extend it to new control domains.
