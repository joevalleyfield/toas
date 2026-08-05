Filed as: 260804-noncoercive-compaction-handoff
FKA:
AKA: advisory handoff shape; preserve partial compaction; non-vetoing reconstitution
Legacy index:

keywords: projection, hardening, historical, correctness, transcript, compaction, continuation, boundaries

Parent: `260803-llm-native-compaction-projection`
Depends on: `260804-successor-continuation-remediation`
Related: `260803-session-rotation-lifecycle`

# Make Compaction Handoff Structure Advisory Everywhere

## Objective

Preserve every string returned by the assistant for `/compact` as assistant
content, even when it is incomplete, free-form, empty, or missing requested
handoff/reconstitution headings. Mechanical structure may support optional
diagnostics and restoration extraction, but it must never veto or replace
model content that the operator should be allowed to inspect and judge.

Apply the same non-coercive rule to explicit successor continuation: a last
user turn ending in `/compact` followed by any assistant turn is sufficient.
Missing or malformed restoration sections reduce the safely extractable
command set; they do not reject continuation or alter the handoff.

## Required Contract

- Successful generation with a string `content` value always projects and
  persists that exact value as an assistant message.
- Empty string is still content and remains durable; only generator exceptions
  or non-message/non-string transport shapes produce harness errors.
- Required headings in the compaction prompt are advisory output guidance, not
  runtime policy.
- Continuation does not require `# Handoff Summary`, `## Current Objective`, or
  reconstitution headings after the transcript-local `/compact` predicate is
  satisfied.
- Restoration extraction is best-effort. Missing sections and malformed or
  unsafe entries are skipped; valid entries retain their order.
- When nothing safe is extractable, successor composition retains an editable
  empty user slot after the assistant handoff.
- Suggested naming falls back deterministically when no objective section can
  be extracted.
- Any advisory about missing requested material must be separate from and must
  not rewrite, hide, replace, or prevent projection of the assistant content.

## Acceptance Criteria

- [x] Complete, partial, free-form, and empty assistant strings all project and
  persist unchanged through `/compact`.
- [x] Generator exceptions and non-dict/non-string responses remain explicit
  errors without creating a compaction projection.
- [x] `/compact` followed by arbitrary assistant content is eligible for
  continuation.
- [x] Missing Files/Commands sections do not reject continuation.
- [x] Partially malformed restoration sections preserve the handoff and yield
  only safely extractable commands.
- [x] A no-command successor ends in an editable empty user message.
- [x] Missing objective text uses the session-handoff naming fallback.
- [x] Focused and full tests pass with complete coverage.

## Allowed Write Surfaces

- compaction operator handling under `src/toas/runtime/`;
- compaction persistence/projection edges;
- successor continuation and restoration extraction under `src/toas/runtime/`;
- focused step, projection, continuation, and CLI tests;
- this task and generated `tasks/WORKBOARD.md` sections.

## Required Completion Evidence

- content-preservation matrix covering complete/partial/free-form/empty output;
- continuation matrix covering absent and malformed optional sections;
- proof that protocol/transport failures remain errors;
- exact successor projection with an empty editable user slot;
- focused and full-suite results.

## Completion Evidence

- `/compact` projection and durable compaction updates preserve complete,
  partial, free-form, empty, and whitespace-bearing string content verbatim.
- Non-dict and non-string generation results, plus generator exceptions, remain
  explicit errors and create no compaction update.
- Continuation now recognizes only the transcript-local boundary: the last user
  turn ends in `/compact` and the following turn is an assistant turn. Handoff
  headings do not participate in eligibility.
- Restoration extraction skips absent, malformed, and unsafe optional entries
  while retaining valid `$ cat ...` and command entries in source order.
- Arbitrary and empty handoffs produce a successor containing seed user context,
  the assistant handoff, and an editable empty user message when no commands
  can be extracted. Missing objective text names the suggestion
  `YYMMDD-session-handoff`.
- No advisory message was added: the requested shape remains prompt guidance,
  and the harness neither alters the content nor adds transcript noise.
- Focused verification: 30 session-continuation tests at 100% targeted coverage;
  379 compaction/runtime tests passed.
- Full verification: 2,808 passed, 9 deselected, 100% coverage.
