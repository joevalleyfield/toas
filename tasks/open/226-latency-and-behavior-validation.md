## Goal

Validate that daemon/channel transport materially improves interaction latency while preserving behavior.

## Scope

- benchmark step latency across three paths:
  - spawn-per-step (`:r !toas step` / local CLI)
  - CLI-to-daemon RPC
  - Vim direct persistent channel
- compare behavior parity for stdout and history side effects
- record p50/p95 latency and representative variance notes

## Intended Inputs

- completed `223` and `224` flows
- representative session/transcript scenarios
- local environment constraints and measurement harness

## Intended Outputs

- repeatable benchmark procedure and captured results
- parity checklist results for behavior correctness
- recommendation on default interaction path

## Constraints

- comparisons must use equivalent workloads
- behavior regressions block perf conclusions
- results must be documented in repository docs

## Non-Goals

- no further architectural changes in this task
- no tuning based on synthetic microbenchmarks alone

## Done When

- latency comparisons are captured and reproducible
- behavior parity is explicitly validated across paths
- docs include practical guidance on when to use each path
