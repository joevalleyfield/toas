# 541 Primary-Surface RPC Exception Ledger And Retirement Plan

## Goal
Document, qualify, and sequence retirement for any remaining RPC-only exceptions on primary operator surfaces.

## Why
`525` requires RPC to be removed from primary paths except where no non-RPC path exists. Remaining exceptions need explicit rationale and de-risked retirement sequencing.

## Scope
In scope:
- enumerate current RPC-only exceptions for `step --async`, `watch`, `cancel`, and Vim primary surfaces
- record hard rationale for each exception
- define concrete removal path and validation hook per exception
- wire findings into roadmap/task sequencing

Out of scope:
- implementing every retirement in one pass

## Done When
- exception ledger exists and is current
- each exception has rationale + removal plan + test/probe hook
- roadmap reflects execution order for retirement slices

## Related
- `525`
- `526`
- `531`
- `534`
