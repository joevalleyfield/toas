## Goal

Make command-plane authoring and staging ergonomic for multiline scripts while keeping execution intent explicit, inertable, and selectable by projection shape.

## Why Now

Recent staging regressions highlighted a broader product gap: compact projections can become hard to author or non-executable, and there is no explicit operator control over projection shape (`yaml` vs `$` shell shorthand vs future forms). We also lack a first-class inert/escape contract for callable and slash-command content.

## Scope

- define command-plane projection modes for adopted/staged callable content:
  - `yaml` (canonical structured callable block)
  - `shell` (`$ ...` shorthand where executable and unambiguous)
  - `auto` (policy-driven selection with deterministic fallback)
  - reserve extension point for additional shapes
- define multiline authoring ergonomics:
  - preserve multiline scripts without brittle escaping
  - avoid shape loss during assistant->user staging
- define inert/escape semantics for:
  - callable-looking YAML/tool-call content
  - slash-command-looking content
  - mixed text where execution should be suppressed
- define how operators select shape at author-time and/or runtime policy level
- add regression tests covering staging, replay/adoption, and inert rendering paths

## Intended Behavior

- multiline script authoring is practical and predictable
- staged/adopted content remains executable when intended, inert when requested
- projection shape is explicit and operator-controlled, not implicit parser luck
- fallback behavior is deterministic and test-covered

## Constraints

- preserve append-only durable history invariants
- preserve user-intent vs model-addressable capability split
- avoid silent semantic drift between displayed and executed forms

## Links

- follows immediate precedence fix thread in `441`
- complements arbitration/ID work in `442`
- should reuse queue durability/continuation semantics from `331` where multi-intent continuation applies

## Done When

- projection-shape policy is implemented and documented
- inert/escape rules are implemented with clear examples
- multiline script authoring/staging tests pass across adopted/staged/replay paths
- operator help/docs explain when to use each shape and how to force inert text
