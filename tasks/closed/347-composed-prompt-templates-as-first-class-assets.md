## Goal

Make composed prompt templates first-class prompt assets so operators can browse/render them with the same `/prompt` and `toas prompts` surface used for leaf fragments.

## Why Now

Current composition power exists, but practical use is friction-heavy because operators must remember CLI flags and composition choices. The better model is: templates are assets; composition is an implementation detail.

## Scope

- add a template-asset namespace (for example `session-start/templates/*`)
- define template manifests as data (role/session/protocol/constraints/mode) rather than ad hoc CLI invocation
- resolve template manifests through existing `PromptComposer` machinery
- expose template assets in normal prompt browsing/listing output
- keep rendering semantics unchanged: `/prompt <ref>` renders asset content for transcript insertion

## Intended Behavior

- operators can discover full-size templates via `toas prompts` and `/prompt` browsing
- rendering a template uses the same command and output style as rendering a fragment
- leaf fragments and composed templates share one conceptual asset model

## Constraints

- avoid introducing a parallel command surface for template composition
- preserve current leaf prompt refs and compatibility aliases
- keep template composition deterministic and inspectable

## Done When

- at least one template asset is browsable and renderable as a first-class ref
- composition inputs are represented as asset data, not only transient CLI flags
- docs and help text reflect template assets as part of the standard prompt library
