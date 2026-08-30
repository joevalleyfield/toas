Filed as: 349-json-callable-lane-separate-parser-and-policy-arc
FKA: 349-json-callable-lane-separate-parser-and-policy-arc
AKA: json lane; json callable; parser policy
Legacy index: 349

keywords: tooling, decomp, inception, compatibility, json, callable, serialization

Parent: `260803-language-exec-fenced-block-lane`
Related: `299`; `260803-tool-intent-ingress-separation`

# JSON Callable Serialization Corollary

Add JSON as a serialization sibling to the fenced-YAML callable lane, sharing
the same normalized tool-plan, authority, execution, and result semantics after
deserialization.

## Status Note

This is a narrow follow-on to the executable-fence scanner/lane registry. It is
not a separate policy arc unless implementation evidence finds a post-
normalization semantic difference from YAML.

## Why Now

`src/toas/graph.py` already separates YAML deserialization from
`normalize_tool_plan`. Once the general fence scanner can select a JSON handler,
JSON can deserialize a mapping/list and enter that same normalizer. This is a
close corollary rather than an alternate execution model.

## Scope

- settle whether the active form is `json exec`, plain `json` as a YAML-parity
  structural form, a generic/unlabeled structurally callable fence, or multiple
  named activation profiles
- deserialize JSON mappings/lists and pass them to `normalize_tool_plan`
- preserve callable aliases, validation, intention, and error behavior after
  normalization
- define deterministic coexistence and textual arbitration with YAML and other
  executable fences
- preserve the same user/assistant authority and transcript/result projection
  used by equivalent YAML calls

## Intended Behavior

- Equivalent YAML and JSON bodies normalize to identical tool plans.
- Serialization errors remain lane-specific; tool validation and execution
  errors remain shared.
- No prompt advertises executable JSON before recognition and policy wiring
  exist.

## Constraints

- no parallel JSON tool validator, executor, or policy resolver
- preserve direct user intent versus model-addressable capability
- fail closed on ambiguous mixed structured-callable fences
- keep ordinary illustrative JSON inert under the settled activation grammar
- preserve a structural activation option that remains usable when a proxy
  strips overt execution metadata but leaves an exact callable body

## Done When

- JSON activators, precedence, proxy-transformation specimens, and inert escape
  are explicit and test-covered.
- Equivalent YAML/JSON specimens normalize identically.
- Mixed YAML/JSON arbitration, malformed JSON, duplicate/conflicting keys, and
  multiple-candidate ambiguity fail deterministically.
- Authority, execution records, results, replay/restaging, and prompt guidance
  remain shared with the YAML callable model.

## Allowed Write Surfaces

- the shared fence scanner/lane registry established by the parent task
- the structured-callable extraction adapter near `src/toas/graph.py`
- focused tests under `tests/`
- prompt/help assets only after the runtime lane exists
- this task file and mechanically generated `tasks/WORKBOARD.md` sections

## Outcome

Implemented the explicit `json exec` serialization corollary. JSON fence
bodies deserialize through the shared `normalize_tool_plan` path, reject
duplicate keys deterministically, remain inert without the explicit `exec`
activator, and participate in the existing source-ordered YAML/Bash candidate
stream. Authority, execution, durable recording, and result projection remain
shared with the incumbent callable path.

Verification: focused executable-fence and arbitration tests passed (`24
passed`); Ruff passed for all changed source and test files.

The broader structural/proxy-recovery activation option remains deferred until
a concrete transformed transport specimen justifies it.
