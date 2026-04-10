## Goal

Add semi-durable shell grant management that can live in transcript scope (regional/branch-aware) and config scope (durable/global-ish).

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
