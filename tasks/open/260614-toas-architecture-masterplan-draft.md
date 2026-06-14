Filed as: 260614-toas-architecture-masterplan-draft
FKA:
AKA: big architecture; architecture masterplan; domain map; runtime bloat guardrail
Legacy index:

keywords: architecture, masterplan, runtime, domains, boundaries, dependency-injection, active

# TOAS Architecture Masterplan Draft

## Current Reality

TOAS has successfully moved major behavior out of the old broad CLI and daemon surfaces. That was a real improvement, but the next risk is moving too much semantic weight into `runtime/` without naming separate domains clearly enough.

Current architecture documents capture several important pieces:

- `docs/vision.md`: transcript/event-log operator substrate.
- `docs/runtime-direction.md`: session-rooted, stdio-first, persistent runtime direction.
- `docs/runtime-ownership.md`: current module ownership guidance while decomposition continues.
- `tasks/open/260614-runtime-owned-backend-lifecycle-architecture.md`: backend lifecycle ownership target.

What is missing is a single top-down proposal that says how the world should look when these ideas are reconciled.

## Desired Reality

TOAS should have a domain-oriented architecture map that prevents `runtime/` from becoming the next broad compatibility module.

The proposal should distinguish:

- durable state
- transcript and alignment mechanics
- operator consequence semantics
- activities and streams
- tool/capability execution
- model/backend interaction
- host/session supervision
- transport/protocol adapters
- CLI and presentation surfaces

The document should be explicitly draft/proposal material so it can be criticized before it becomes contribution guidance.

## Gap Analysis

Without this masterplan, useful local refactors can drift into:

- runtime bloat by accretion
- dependency injection used as a substitute for ownership
- daemon/host/backend vocabulary blur
- tests targeting incidental wiring rather than domain contracts
- decomposition under `400` that improves file size while leaving architecture shape ambiguous

## Known Facts

- `525` closed the primary `step`/`step --async`/`watch`/`cancel` runtime-ownership push.
- Backend lifecycle remains the highest-leverage documented ownership gap.
- The public service-like CLI cluster currently includes `daemon`/`service`, `host`/`transport`, and `backend`.
- `daemon` is compatibility transport, not semantic owner.
- `host` is the primary local session transport.
- `backend` is model/provider lifecycle, not the TOAS service.

## Decisions

- Draft `docs/architecture-masterplan.md` as a DIRECTIONAL proposal.
- Treat the first draft as material for critique, not as settled normative guidance.
- Use this task to keep the critique loop explicit before translating any proposal into implementation constraints.

## Next Actions

- [x] Draft the first top-down architecture proposal.
- [ ] Critique the proposal with attention to domain boundaries, dependency-injection discipline, and service vocabulary.
- [ ] Convert accepted parts into updates to `docs/runtime-direction.md` and `docs/runtime-ownership.md`.
- [ ] Split implementation tasks only after the proposal survives critique.
