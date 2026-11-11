Filed as: 261111-yaml-action-block-misfire-auto-heal
FKA:
AKA: yaml misfire auto-heal; structured action block parser robustness
Legacy index:

keywords: yaml, extraction, parser, action-block, auto-heal, robustness, defect
Depends on:
Related: `261111-result-turn-id-namespace-advance` (flagged as sibling defect there)

# Structured action block YAML misfires need auto-heal

Status: OPEN; defect observed repeatedly, parser seam located, awaiting spike

## Objective

Make structured action block extraction robust to the YAML shapes the
system itself prompts the model toward, and add an auto-heal / repair path
for the misfire shapes that currently hard-fail extraction. Today certain
valid, idiomatic YAML shapes are rejected, forcing a retry loop that wastes
a turn and erodes operator/model momentum.

## Defect (observed, repeatedly)

Structured action blocks fail YAML extraction on two idiomatic shapes:

1. **Block-list `argv` in a multi-op plan.** A `shell` / `shell_script`
   argument given as a YAML block sequence (one item per line):
       - operation: shell
         arguments:
           argv:
             - "find"
             - "src"
             - "-type"
             - "f"
   is rejected ("yaml parse error ... use block list style for argv, one
   item per line" -- i.e. the parser wants it, the model emits the flow
   form, and the error message is contradictory). The flow form
   `argv: ["find", "src"]` and the block form should both be accepted.

2. **Intent-only single-op block / retry shape.** A block that carries
   `operation` + `arguments` + `intent` where the arguments or the
   surrounding indentation does not match the strict expected shape
   (the "Retry failed operation (edit directly, then step)" pattern, and
   the "unknown argument(s): intent" misfire where `intent` is placed as a
   sibling rather than recognized). These are shapes the operator and the
   system both produce and expect to be recoverable.

The error messages are actively misleading: they tell the model to use the
block-list form for `argv`, but the parser rejects the block-list form in
the multi-op context, so the model cannot converge.

## Root Cause / Seam (to confirm in spike)

- Structured action block extraction (the YAML parse of model-emitted
  TOAS-local action blocks) is stricter than the shapes the prompt
  templates and the operator's own shorthand produce.
- Locate the extraction parser (the "callable-looking assistant block is
  not valid YAML for extraction" error source) and enumerate the exact
  accepted/rejected shape matrix.

## Scope

- Accept BOTH flow (`argv: ["a","b"]`) and block-list (`argv:\n  - a\n  - b`)
  forms for `shell` / `shell_script` `argv` in single-op and multi-op
  plans.
- Accept and correctly route `intent` (and the compatibility aliases
  `intention`, `tool_name`, `args`/`params`) in the shapes the system
  prompts the model toward, including the retry/recovery shape.
- Add an AUTO-HEAL path: when a block is close-but-misshaped, normalize it
  (e.g. flow<->block `argv`, sibling-vs-nested `intent`) and re-parse
  before hard-failing, and only surface an error when the shape is
  genuinely unrecoverable. The error message, when it does fire, must be
  actionable and non-contradictory.
- Keep the fix in the extraction/parse seam; do not loosen to the point of
  accepting genuinely ambiguous or provider-native tool-call syntax (the
  "TOAS-local YAML action blocks exclusively" invariant).

## Verification

- `uv run pytest` green; `./scripts/check.sh` green; 100.00% statement
  coverage on the touched extraction/parse path.
- Operator-perspective end-to-end (mandatory):
  - A multi-op plan with block-list `argv` extracts cleanly (no misfire,
    no retry).
  - A flow-form `argv` still extracts (no regression).
  - An intent-only / retry-shaped block either extracts or auto-heals to a
    valid block; when it cannot, the error is actionable and consistent
    with the shape it asks for.
  - Genuinely invalid / provider-native syntax is still rejected.
- Test the public extraction seam (a real model-style block through the
  extraction entrypoint), not private `_` helpers.
         intent: Create the YAML action-block misfire auto-heal task
