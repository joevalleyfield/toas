Filed as: 260803-assistant-execution-authority
FKA:
AKA: execution authority refresh; longer tool timeouts; local tool lane friction
Legacy index:

keywords: runtime, decomp, inception, usability, authority, policy, shell, timeout

Related: `260530-shell-lane-spawn-semantics`; `260614-architecture-follow-through-coordination`; `260803-seed-prompt-operator-stance`; `260803-first-failure-plan-recovery`; `260803-tool-intent-ingress-separation`

# Assistant Execution Authority And Tool-Lane Friction

## Objective

Revisit assistant execution limits so the local TOAS tool lane supports normal
repo work, including intentionally longer-running commands, without collapsing
the important distinction between direct user intent and model-addressable
authority.

## Current Reality

Assistant `shell` and `shell_script` calls default to five seconds and reject
timeouts above thirty seconds. Command allowlists, workspace bounds, shell
operator parsing, environment handling, staging behavior, and transport
timeouts add further constraints. Some are integrity boundaries; others may be
historical friction whose cost now exceeds its demonstrated value.

The runtime ownership contract requires effective policy and authority to be
explicit and observable. This task should therefore audit constraints by
purpose before changing numeric limits or bypassing the local tool lane.

## Desired Contract

- Assistants can request a longer execution window when the operation and
  expected duration justify it.
- Timeout is an execution/liveness parameter, not a substitute for command
  authorization, cancellation, or workspace scope.
- Longer requests remain cancellable and expose progress or liveness where the
  underlying lane supports it.
- Direct user intent may retain broader authority, but ordinary assistant work
  should not be pushed into the user lane merely to escape arbitrary limits.
- Effective limits and their provenance are inspectable in capability help and
  runtime evidence.
- Restrictions remain when backed by data-integrity, cross-platform, or
  concrete misuse evidence; convenience-only restrictions require fresh
  justification.

## Audit Matrix

Classify each current constraint by owner, purpose, evidence, and proposed
disposition:

- default and maximum command timeout;
- subprocess termination and descendant cleanup on timeout/cancel;
- assistant command allowlist and session/workspace grants;
- workspace/cwd boundaries;
- `shell` versus `shell_script` syntax restrictions;
- environment mutation and inherited environment behavior;
- buffered versus streaming execution;
- host/RPC request timeout versus underlying command lifetime;
- staging/escalation into direct user intent;
- platform-specific launcher and process-group behavior.

## Requirements Questions

- Should assistants request any positive timeout, choose from policy tiers, or
  request an explicit durable grant above a configurable ceiling?
- Which commands need progress/liveness guarantees before they may exceed the
  current bound?
- How should a transport client distinguish “command still running” from a
  failed request timeout?
- Can the default remain short while the ceiling becomes policy-driven?
- What evidence proves a restriction is necessary rather than inherited?
- How should capability guidance explain available authority without training
  models to route around it?

## Acceptance Criteria

- [ ] A checked-in audit classifies every constraint above with current owner,
  safety rationale, and keep/change/remove disposition.
- [ ] Assistants can express an appropriate longer-running command request
  through the TOAS lane without converting it to direct user intent solely for
  timeout reasons.
- [ ] The resulting timeout policy is configurable or explicitly tiered rather
  than hidden as duplicated numeric caps.
- [ ] Long-running calls remain cancellable and reach one durable terminal
  outcome, including timeout and process-cleanup cases.
- [ ] Transport request deadlines do not falsely imply that an underlying
  command was terminated.
- [ ] Capability help reports the effective timeout/authority policy and its
  relevant provenance.
- [ ] Existing workspace-boundary and command-authorization invariants remain
  intact unless separately justified by the audit.
- [ ] Tests cover short success, requested long success, timeout, cancellation,
  authorization denial, and transport-lifetime separation.

## Non-Goals

- Giving model-addressable tools unrestricted host access.
- Merging direct user intent with assistant authority.
- Solving backend model-generation timeouts under the shell timeout label.
- Retaining every current restriction merely because it already has tests.

## Allowed Write Surfaces

- policy/authority resolution under `src/toas/runtime/` and config modules
- shell execution under `src/toas/tools_cluster/`
- transport adapters only where request lifetime must be separated from command
  lifetime
- capability guidance/help and focused tests under `tests/`
- execution/authority documentation and this task file
- mechanically generated `tasks/WORKBOARD.md` sections

## Required Completion Evidence

- completed audit matrix with evidence links;
- focused long-run, cancellation, cleanup, and transport tests;
- effective-policy/help output before and after;
- representative dogfood run exceeding thirty seconds through the assistant
  lane;
- default suite result.

## Operator Input Welcome

Useful additions include commands currently blocked by the thirty-second cap,
desired timeout tiers, examples of avoidable user-lane staging, and artifacts
showing which current restrictions are still valuable.
