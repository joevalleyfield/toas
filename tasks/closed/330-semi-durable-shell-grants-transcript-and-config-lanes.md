## Goal

Add semi-durable shell grant management that can live in transcript scope (regional/branch-aware) and config scope (durable/global-ish).

## Status

Closed (2026-04-14)

## Why Now

Operators need low-friction approvals that can persist appropriately without collapsing all policy into one global mutable lane.

## Scope

- define grant model and merge precedence between transcript lane and config lane
- support expressive match forms:
  - prefix
  - wildcard/glob
  - segmented shell pipeline composition rules
- add compact grant-management command surface (list/add/remove/unset/reset as appropriate)
- provide source visibility for effective grants

## Intended Behavior

- transcript grants follow lineage/branch behavior naturally
- config grants provide stable baseline defaults
- effective policy is inspectable and explainable

## Constraints

- no opaque hidden state changes
- policy resolution must be deterministic and testable

## Done When

- grant records can be added/removed in both lanes
- effective policy view shows origin/source information
- tests cover merge precedence, wildcard/prefix matching, and segmented pipeline matching

## Completed

- added normalized shell grant model with explicit forms:
  - exact command (`rg`)
  - prefix (`prefix:jj`)
  - glob (`glob:python*`)
- transcript lane supports:
  - `/shell add|remove|unset|reset`
  - compat aliases: `/shell allow|deny`
- config lane supports:
  - `/shell config list|add|remove|reset`
  - emits `config_update` records for durable baseline updates
- `/shell list` now shows:
  - effective grants with source attribution (`config`, `transcript`)
  - baseline grants
  - active transcript lane delta (added/removed)
- assistant-bounded shell checks now use grant matcher (exact/prefix/glob)
- `shell_script` authorization now checks segmented command composition (e.g. `echo ... | head -1` validates both segment leaders)
- tests added/updated across `step`, `tools`, `config`, and new `shell_grants` coverage

## Side-Quest Notes

- code smell observed: shell grant semantics and display strings are still spread across `step.py`, `tools.py`, and help text; follow-up could centralize rendering/usage copy in one helper to reduce drift.
