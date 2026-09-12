Filed as: 260912-models-single-endpoint-default
FKA:
AKA: implicit models endpoint; single endpoint model commands
Legacy index:

Parent: `260912-model-observation-raw-details`

keywords: models, endpoints, surface, implementation, usability, active

# Infer the endpoint for model observations when unambiguous

## Objective

Make `/models live`, `/models refresh`, and `/models known` convenient when
exactly one endpoint is configured, while retaining explicit endpoint
selection as the unambiguous form for multi-endpoint configurations.

## Contract

- With exactly one configured endpoint, each model operation may omit
  `ENDPOINT` and uses that endpoint.
- With zero configured endpoints, omission fails with a useful configuration
  hint.
- With multiple configured endpoints, omission fails with a useful ambiguity
  hint that names the explicit form.
- An explicitly supplied endpoint continues to work unchanged.
- Help presents `ENDPOINT` as optional only under the single-endpoint rule.

## Acceptance criteria

- `live`, `refresh`, and `known` each accept the endpoint-less form with one
  configured endpoint.
- Endpoint-less forms do not silently choose with zero or multiple endpoints.
- Existing flag behavior and explicit endpoint forms remain covered.

## Allowed write surfaces

- `/models` operator parsing and usage text;
- focused unit/acceptance tests;
- this task and generated workboard.

## Completion evidence

Implemented endpoint inference for all three model operations. With exactly
one configured endpoint, `/models live`, `/models refresh`, and `/models known`
now use it when the endpoint argument is omitted. Zero endpoints produce a
configuration hint; multiple endpoints produce an explicit-selection error
listing the available endpoint names. Help and asset guidance now show the
optional argument while retaining explicit examples.

Focused result: `182 passed` across operator and help tests.
Full result: `3230 passed, 17 deselected`; coverage `100%`; acceptance and
integration `17 passed`; Ruff and mypy passed.

## Status

Closed 2026-09-12.
