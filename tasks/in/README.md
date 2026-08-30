# TOAS Task Inbox

This directory (`tasks/in/`) is the intake surface for TOAS work delegated from the workspace level (Documents/Journal).

## Pattern

When workspace coordination identifies work that belongs to TOAS:
1. A note is created in this directory with minimal context
2. TOAS triages at its own cadence
3. TOAS either: claims it as an open task (move to `tasks/open/`), defers it, or rejects it

## Project Decision

- Keep `tasks/in/` version-controlled as the durable workspace-to-project
  intake boundary.
- Keep incoming notes minimal. They describe delegated intent, not a ready
  implementation contract.
- Triage the directory on demand. Promote accepted work by expanding the note
  to the normal TOAS task format and moving it to `tasks/open/`.
- Leave deferred notes in place with a short disposition. Remove rejected
  notes only after recording why they do not belong in TOAS.
- Keep this README when the inbox is empty so the intake boundary remains
  discoverable.

## Current Scope

Notes in this directory are raw workspace-level delegations. No acceptance
criteria or implementation assumptions are required at intake.

TOAS interprets intent and decides next steps.
