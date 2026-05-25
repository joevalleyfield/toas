# Frontier Middle-Seam State Space (Interaction Layer)

## Scope

This note externalizes state-space evaluation for the interaction seam between:

1. `run_step_local` transcript/context assembly
2. runtime kwargs handoff into `step(...)`
3. `_build_new_transcript_nodes` boundary reconciliation (`bind_index`, `anchor_index`, `lcp_index`, divergence parent)

This is the layer where end-to-end drift has been observed even when isolated reconciliation seam replay appears correct.

## Variables (Per Step)

- `head_id`: selected head id from control lane (`active_head_id`)
- `lineage_len`: message lineage length for selected head
- `bind_index`: active jump bind index (or `None`)
- `bind_parent`: parent id chosen from selected lineage/bind view
- `storage_tip_parent`: tip id of selected message lineage
- `anchor_index`: anchor hint index from `alignment_anchor_index`
- `parsed_nodes_len`: parsed transcript node count
- `bound_log_len`: effective bounded log length (`len(log[bind_index:])` semantics)
- `lcp_index` (`i`): transcript-vs-bound-log boundary index after anchor offset
- `divergence_parent`: first rewritten node parent boundary (if rewrite occurs)
- `first_new_parent`: parent on `new_from_transcript[0]` when non-empty
- `frontier_role/frontier_id`: resulting frontier in working set

## Core State Families

### F1: Selected-Lineage Context

- `F1.A`: single-head selected lineage, no explicit head control records
- `F1.B`: selected head from explicit head record
- `F1.C`: selected head unchanged but non-message records appended between steps

Invariant intent:
- non-message records must not alter message lineage index mapping for selected head.

### F2: Bind/Anchor Control

- `F2.A`: `bind_index=None`, `anchor_index=0`
- `F2.B`: `bind_index=None`, `anchor_index>0`
- `F2.C`: `bind_index` explicit suffix scope

Invariant intent:
- anchor is a hint only; no stale anchor may force boundary older than true shared prefix.

### F3: Transcript Evolution

- `F3.A`: exact match
- `F3.B`: append-only
- `F3.C`: tail rewrite after shared prefix
- `F3.D`: control insertion (`TOAS:CONTROL`) plus tail rewrite
- `F3.E`: user-turn inline `## RESULT` content edit

Invariant intent:
- `## RESULT` is inline user content, not a structural transcript boundary marker.

### F4: Boundary Outcome

- `F4.A`: `lcp_index == bound_log_len` (no rewrite)
- `F4.B`: `0 < lcp_index < bound_log_len` (shared-prefix rewrite)
- `F4.C`: `lcp_index == 0` (root divergence)

Invariant intent:
- `F4.B` first rewritten parent must equal latest shared-prefix node id.

## Forbidden Transition Signatures

These are considered regression signatures in this seam:

1. `bind_parent` advances between steps while `divergence_parent` regresses by unrelated extra turns under tail rewrite.
2. `lcp_index` collapses toward root (`... -> 1/0`) without corresponding root-level transcript rewrite.
3. `TOAS:CONTROL` insertion causes boundary regression beyond transcript-shared-prefix semantics.
4. Non-message record growth changes effective shared-prefix parent selection for unchanged transcript prefix.

## Assertions (Machine-Checkable Targets)

- `M1_selected_lineage_stability`
  - If selected head unchanged and only non-message records append, lineage message id order remains identical.

- `M2_boundary_from_shared_prefix`
  - Under `F3.C/F3.D/F3.E`, with shared prefix length `k > 0`, `lcp_index == k`.

- `M3_first_new_parent_equals_prefix_boundary`
  - Under `F4.B`, `first_new_parent == selected_lineage[k-1].id`.

- `M4_control_is_non-structural_for_message_boundary`
  - `TOAS:CONTROL` turn insertion does not reduce `k` for unchanged prior message prefix.

- `M5_result_inline_edit_is_user-content-edit`
  - Editing inline `## RESULT` text in a user turn produces user-content rewrite semantics, not special boundary class.

- `M6_non_message_records_not_in_message_identity_space`
  - Message id-space (`n#`) and message lineage indexing are unaffected by non-message record append order.

## Interaction Test Matrix (Planned)

1. Baseline exact-match step then tail rewrite (`F2.A + F3.C -> F4.B`) => assert `M2/M3`.
2. Add control insertion before same tail rewrite (`F2.A + F3.D -> F4.B`) => assert `M2/M3/M4`.
3. Repeat with inline `## RESULT` mutation (`F3.E`) => assert `M2/M3/M5`.
4. Replay with intermediate non-message record append only (`F1.C`) => assert `M1/M6`.

## Notes

- Isolated `_build_new_transcript_nodes` replay from captured red-case payload can pass while end-to-end interaction still fails.
- Therefore, interaction tests must observe transitions across full `run_step_local` cycles, not only single-seam replay.
