# 554 Vim Transport Annotation Implementation Follow-on

## Goal
Apply targeted code/doc rationale annotations identified by Task `553` Step 5 annotation-gap audit.

## Why
Task `553` is scoped to triage/cleanup and explicitly avoids code-file edits. Annotation implementation must be tracked separately to preserve clean planning-to-implementation boundaries.

## Scope
In scope:
- add minimal, high-value rationale comments/doc notes at approved hotspots from `553` Step 5
- keep edits narrowly scoped to intent-preserving annotations only

Out of scope:
- functional behavior changes
- broad style/comment rewrites

## Inputs
- annotation-gap findings and file/line targets produced by `553` Step 5

## Done When
- all approved annotation targets from `553` Step 5 are implemented
- no functional behavior changes are introduced
- task/docs references are stitched and validated

## Related
- `553`
- `541`
- `542`

## Progress
- 2026-05-24: implemented all Step 5 audit targets as annotation-only updates:
  - `vim/plugin/toas.vim`: default transport rationale, fail-safe normalization rationale, routing contract comment, compatibility-helper note, and explicit watch fallback rationale.
  - `src/toas/runtime/session_host_process.py`: streaming-vs-list compatibility boundary note plus subscribe lifecycle rationale (`push_ack` timing, immediate reject semantics, `push_complete.reason` contract note).
  - `docs/protocols/vim-host-stdio.md`: added normative `stream_subscribe` lifecycle + immediate-forwarding/flush requirements.
- 2026-05-24: verified no functional behavior changes were introduced in this task slice.
