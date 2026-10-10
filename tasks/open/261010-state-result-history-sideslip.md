# Consider State Result History Side-Slip

Filed as: 261010-state-result-history-sideslip
FKA:
AKA: state result import branch; duplicated state after projected results
Legacy index:

keywords: runtime, investigation, inception, provenance, state, history, projection

Related: `260926-state-step-requirements`; `261002-state-transcript-branching-and-modification`

Status: INCEPTION; retain observed state-mode history behavior for future consideration

## Evidence

Dogfood `.toas/session-20261010-1247-preview-request-pretty-inspection.md`
and `.toas/events.jsonl`, inspected 2026-10-10:

- Event-log line 478: `n95` is the user turn containing two shell commands,
  `cat AGENTS.md` and `cat tasks/open/261010-preview-request-pretty-inspection.md`.
- Line 490: generated `STATE/2` message `n96` follows `n95`.
- Lines 493-495: projected RESULT blocks become durable user messages `n97`
  (parent `n95`) and `n98` (parent `n97`); state `n99` follows `n98`.
- `n96` and `n99` have identical content and metadata. Ordinary stepping has
  produced a second lineage containing the imported result turns.
- Adjacent audit mismatch: line 479 records only the second `cat` in the
  `tool_request`, while lines 480-481 record both tool results.

Line numbers describe the inspected append-only file; message IDs and content
are the durable evidence handles.

## Disposition

The operator considers the side-slip a likely known state-mode issue/quirk,
with lower priority than inference resilience. This task preserves evidence
for future review; it does not declare a new repair urgent or assume existing
state-mode reconciliation should be redesigned. Keep the adjacent request/result
audit mismatch distinct if it eventually receives its own investigation.

## Future Questions

- Is result re-import and state re-materialization intentional compatibility
  behavior, or should projected results reconcile without becoming user events?
- What should state identity and provenance mean across an unchanged projected
  transcript, and which existing tasks already own that contract?
- Does multi-command user-shell audit capture need an independent follow-on?
