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
- `tasks/closed/260614-runtime-owned-backend-lifecycle-architecture.md`: backend lifecycle ownership target.

What is missing is a single top-down proposal that says how the world should look when these ideas are reconciled.

## Desired Reality

TOAS should have a domain-oriented architecture map that prevents `runtime/` from becoming the next broad compatibility module.

The proposal should distinguish:

- durable state
- transcript and alignment mechanics
- operator consequence semantics
- activities and streams
- tool/capability execution
- model invocation and model backend lifecycle
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
- `backend` is model-serving/provider lifecycle, not the TOAS service and not a generic worker supervisor.

## Decisions

- Draft `docs/architecture-masterplan.md` as a DIRECTIONAL proposal.
- Treat the first draft as material for critique, not as settled normative guidance.
- Use this task to keep the critique loop explicit before translating any proposal into implementation constraints.

## Investigations

- Reader pass: the first draft was clear to an already-warm maintainer but assumed too much TOAS vocabulary. Added a current-to-target bridge, local term definitions, and example `toas step` / `toas backend status` domain paths so someone less familiar can recover the shape.
- Force-mapper pass: constrained `backend` to the current LLM/model-serving shape and split the draft domain into `Model Invocation` and `Model Backend Lifecycle` so ambitions do not expand into generic worker supervision by accident.
- Force-mapper follow-up: renamed `Transcript And Alignment` to `Transcript Reconciliation`, split surface adaptation from projection/rendering, and added `Effective Policy And Authority` as a missing force so config/identity/grant precedence does not stay implicit.
- State-ownership pass: added critique notes rather than final decisions, capturing canonical vs projected state, live vs durable activity state, model backend process keying, effective-policy resolution, host-loss semantics, and daemon adapter-only state risk.
- Flow pass: added critique notes for six cross-domain flows and preserved flow-derived invariants to evaluate, including host liveness vs activity terminality, projection vs durable state, config change vs backend restart, and health observation vs lifecycle ownership.
- Failure-ownership pass: added critique notes for host/process death, stale RPC compatibility, transcript branch ambiguity, stream reconnection, cancellation, config/backend mismatch, health-after-start failure, authority resolution, policy denial, and projection failure without making them final contracts yet.
- Split/merge pass: added critique notes recommending splits for transcript reconciliation/operator semantics, model invocation/model backend lifecycle, session host supervision/activity lifecycle, and surface adapters/projection rendering while leaving package-layout decisions open.
- Architecture-decision extractor pass: added an extracted decision ledger with proposed/accepted/unresolved statuses and a not-decision-ready list for active async durability, effective policy resolution, compatibility precedence, cancellation convergence, transcript handoff shape, and model/lifecycle failure handoff.
- Editor pass: compressed the repeated domain mini-sections into a single `Domain Map`, grouped the review material under `Critique Notes`, renamed `Open Critique Questions` to `Remaining Questions`, renamed the extractor section to `Decision Ledger`, and normalized `Session Host Supervision` / `Activity Lifecycle` vocabulary for clearer reader affordance.
- Boundary-invariant pass: promoted candidate hard guardrails into the main document, covering what each domain may know, must not decide, what may cross boundaries, and what would prove a boundary has failed.
- Port/DI pass: added per-domain dependency-boundary critique, acceptable ports, injection smells, easy test doubles, and semantic leakage risks under the `inject ports, not implementation steps` rule.
- Template extraction pass: added `tasks/recurring/templates/architecture-role-review-templates.md` so future architecture work can reuse the focused roles as task/review templates rather than rediscover the process; extended it with implementer, maintainer, verifier, risk-reviewer, decision-recorder, and editor-revisit roles.
- Implementer pass: added continuity notes for the first model backend lifecycle implementation slice, including candidate module targets, contract sketch, ports, expected tests, explicit hand-wavy questions, guardrails to avoid creating a new broad process-control module, and architecture-role prompts so the unresolved implementation concerns get picked back up by later critique passes.
- Backend-lifecycle revisit pass: walked the implementer follow-up prompts one hat at a time across boundary invariants, state ownership, flow, failure ownership, port/DI, and decision extraction; promoted proposed decisions for a shared lifecycle command/result contract, startup-config identity or stale marker, and provider-failure/lifecycle-failure separation.
- Maintainer/verifier/risk/decision/editor pass sequence: separated durable architecture from current migration plan, added exit criteria, evidence obligations, must-not-regress checks, a risk register, and decision-status recording rules so the draft can stop expanding and feed runtime-direction/ownership docs or follow-up tasks.
- Promotion pass: lifted durable target-shape guidance, domain ownership, backend lifecycle direction, routing questions, and must-not-regress checks into `docs/runtime-direction.md` and `docs/runtime-ownership.md` while leaving migration-only critique material in the masterplan.
- Closure triage: backend lifecycle implementation split landed under `260614-runtime-owned-backend-lifecycle-architecture`, so the masterplan has served its purpose as a directional critique/promotion artifact.

## Next Actions

- [x] Draft the first top-down architecture proposal.
- [x] Critique the proposal with attention to domain boundaries, dependency-injection discipline, and service vocabulary.
- [x] Run maintainer, verifier, risk-reviewer, and decision-recorder passes after the backend lifecycle revisit has settled enough to distinguish durable architecture from current plan.
- [x] Convert accepted parts into updates to `docs/runtime-direction.md` and `docs/runtime-ownership.md`.
- [x] Split implementation tasks only after the proposal survives critique.
