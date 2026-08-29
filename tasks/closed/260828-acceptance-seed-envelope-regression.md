Filed as: 260828-acceptance-seed-envelope-regression
FKA:
AKA: v2 seed envelope; acceptance bootstrap seed; leading user marker
Legacy index:

Parent: `260803-seed-prompt-operator-stance`
Related: `260803-seed-prompt-composition-study`; `260823-handoff-successor-focus-naming`

keywords: runtime, projection, active, correctness, acceptance, defaults, transcript

# Acceptance Seed Envelope Regression

Keep acceptance setup aligned with the current `pragmatic-default_v2` seed
contract. The v2 seed is prompt content without a `## TOAS:USER` marker;
acceptance fixtures add exactly one marker when writing it as transcript text.
Assertions should target the current v2 stance wording rather than the retired
v1 social-contract text.

## Acceptance Criteria

- [x] The complete acceptance suite passes in replay-only mode.
- [x] The staged-frontier fixture writes exactly one seed envelope and no
  leading empty user event.
- [x] The fixture asserts the current v2 role-and-working-stance text.

## Implementation Evidence

- Aligned the staged-frontier acceptance fixture with the seed boundary: the
  plain v2 seed is wrapped exactly once when written as transcript text.
- Updated the stale v1 social-contract assertion to match the v2 role section.
- Added projection assertions for the first content block and absence of a
  leading blank message.
- Focused acceptance test: 7 passed.
- Full acceptance suite: 9 passed.

## Closure

Closed after the replay-only acceptance suite passed with the current v2 seed
composition and single-envelope transcript setup.
