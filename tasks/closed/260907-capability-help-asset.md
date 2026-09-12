Filed as: 260907-capability-help-asset
FKA:
AKA: capability discovery; tool availability help; capture task thread help
Legacy index:

Parent: `260901-help-system-design-survey`
Related: `260907-history-help-asset`

keywords: docs, implementation, closed, usability, discoverability, capability, policy

# Capability Help Asset

## Objective

Add an asset-backed capability orientation for the model-facing help path,
using `capture_task_thread` to distinguish configured profile, runtime
visibility, callable shape, and operating policy.

## Acceptance criteria

- `/help capabilities` is rendered from packaged help assets.
- The topic explains that registry identity, configured profile, effective
  visibility, callable argument shape, and operating policy are distinct.
- It points to `capability_help` for focused callable detail and to the
  capability configuration keys without claiming that configured means
  currently callable.
- The focused `capture_task_thread` path is represented with required and
  optional argument guidance and its side-thread policy.
- Add focused catalog and acceptance coverage; preserve dynamic prompt and
  tool behavior.

## Completion evidence

- Added the asset-backed `capabilities` plain facet with explicit distinctions
  among registry identity, configured profile, runtime visibility, callable
  shape, and operating policy.
- Added focused `capture_task_thread` guidance for required/optional
  arguments and its side-thread fork behavior.
- Added compact `/help` discovery and acceptance coverage.
- Focused catalog, prompt/tool, and acceptance tests pass: 100 passed, 1
  deselected.
- Full suite passes: 3212 passed, 17 deselected, 100% coverage.
