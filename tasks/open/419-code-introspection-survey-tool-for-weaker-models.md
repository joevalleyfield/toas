## Goal

Add a first-class code introspection survey tool so models can request module/function/class size diagnostics without reconstructing shell one-liners.

## Why Now

We are actively prioritizing decomposition slices under `400`, and weaker models need a reliable catalog tool for structural surveys.

## Scope

- add a new callable tool in `tools.py` for Python code-size survey output
- include module line-count ranking and largest function/class spans
- expose shape/examples through capability help/advertisement surfaces
- add direct tests for runner behavior and argument validation

## Intended Behavior

- a model can call one operation and get deterministic, parse-friendly rankings for:
  - largest Python files
  - largest Python functions/methods
  - largest Python classes
- output remains workspace-bounded and safe for follow-on planning

## Constraints

- no shell invocation in the tool implementation
- no behavior changes to existing tools
- preserve current rendering contracts (summary + optional content block)

## Done When

- tool is registered and callable with stable arguments
- capability help includes the new tool and example shape
- tests cover happy path and argument validation
