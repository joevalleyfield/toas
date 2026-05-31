# 490 Alternative Operator Frontends (VSCode / Zed / Antigravity / Web)
keywords: surface, explore, parked, research, frontend, editor, web, alternate

## Objective
Evaluate and stage a medium-horizon path for operator frontends beyond Vim, including VS Code, Antigravity, and/or Web surfaces.

## Why
Vim remains functional, but frontend diversity improves operator fit, reduces single-client coupling risk, and can surface protocol/runtime assumptions earlier.

## Horizon
Medium-term (important, not immediate critical path).

## Scope
In scope:
- define candidate frontend targets and baseline capability expectations
- identify integration seams (daemon/RPC/watch/session controls) that should remain client-agnostic
- run one bounded proof-of-concept or adapter spike for at least one non-Vim frontend
- document compare/contrast criteria against Vim baseline

Out of scope:
- replacing Vim immediately
- full feature parity across all frontends in one pass
- UI/branding redesign

## Deliverables
- short design note: frontend options and integration seam expectations
- at least one bounded spike artifact for a non-Vim frontend
- recommended next-step sequence (adopt/defer/split)

## Done When
- candidate frontends and seam requirements are explicit
- one non-Vim path is exercised enough to produce actionable tradeoffs
- follow-on implementation tasks (if any) are clearly scoped

## Related
- 470 operator API seam and CLI-thin migration
- 489 daemon self-shell elimination via operator API
- 483 command stdout streaming to Vim plugin (closed baseline)
