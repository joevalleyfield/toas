Filed as: 260705-runtime-hook-validation-contract
FKA:
AKA: optional hook validation; step runner guardrails; replay execute hook errors
Legacy index:

keywords: runtime, hardening, inception, compatibility, contract, policy

Parent: `260614-architecture-follow-through-coordination`
Related: `260615-runtime-package-growth-boundary-audit`; `260614-legacy-and-fidelity-adapter-precedence`; `260619-daemon-package-facade-shrinkage`

# Runtime Hook Validation Contract

## Current Reality

Some compatibility and test seams still allow optional call hooks to arrive as
`None` or non-callable values. A peeled follow-on experiment added explicit
runtime errors in two places:

- `operator_api.step_once()` when the imported step runner is unavailable
- replay execution when `context.execute` is not callable

Those checks may be worthwhile, but they are a contract choice rather than a
lint/type cleanup. Right now the motivation lives mostly in defensive clarity
and monkeypatch-heavy test seams, not in a written runtime policy.

The architecture notes make this a transition-boundary question, not just a
defensive-programming one:

- historical files and facades are intentionally preserved while ownership
  moves underneath them
- facade symbols should remain when they preserve an existing public/import
  contract
- those facades should shrink only when the contract no longer needs them

That means the key architectural question is: which hook seams are real
compatibility contracts in the transition architecture, and which are merely
incidental test scaffolding that should not be hardened into long-lived
behavior?

## Desired Reality

If TOAS wants explicit hook validation failures, it should say so clearly:

- which hooks are required vs optional
- what error shape callers should see when those hooks are invalid
- whether these are public compatibility guarantees or merely internal
  assertions

If a seam is still part of the repo's intentional compatibility strategy, new
validation behavior should be treated as an architectural change to that
transition contract, not as a casual cleanup.

## Scope

- inventory the specific hook seams that need explicit validation
- classify which seams are real transition contracts worth preserving versus
  incidental scaffolding that should not be hardened
- decide whether explicit errors improve runtime ergonomics enough to justify
  the new contract
- land narrow tests only for the seams that become deliberate guarantees

## Non-Goals

- broad exception taxonomy redesign
- converting every internal callable use into defensive validation
- using test-only monkeypatch pressure as the sole reason to broaden or harden
  public runtime behavior

## Exit Evidence

- [ ] the relevant hook seams are classified as required, optional, or internal
- [ ] any explicit validation errors are intentional and tested
- [ ] compatibility-facing hook validation is separated from purely incidental
  test scaffolding
- [ ] any newly enforced hook behavior is justified as part of transition
  architecture rather than accidental fallout from cleanup pressure
