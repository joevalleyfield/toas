# 526 Primary-Path RPC Dependency Inventory and Exception Governance

## Objective
Produce a concrete inventory of RPC/daemon dependencies across `step`/`step --async`/`watch`/`cancel` (including Vim surfaces) and define what qualifies as a temporary RPC-only exception.

## Why
"Remove from primary paths unless no alternative exists" is directional but needs explicit inventory and governance to be enforceable.

## Scope
- map current path selection and fallback behavior for primary CLI and Vim surfaces
- identify where RPC/daemon dependency is still primary vs fallback
- define exception record shape for RPC-only cases (reason, evidence, removal intent)
- classify each dependency as removable now, removable later, or currently unavoidable

## Done When
- dependency matrix exists for all primary surfaces
- exception rule is concretely documented and testable
- follow-on implementation slices are opened from matrix findings

## Related
- `525` umbrella
- `470` operator API seam
