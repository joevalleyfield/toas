## Goal

Probe which action syntaxes and trigger words are least likely to collide with backend-native tool prompting.

## Scope

- compare YAML, JSON, and alternate action-block framings
- compare terms like `tool`, `tool-call`, `action`, `operation`, and similar trigger vocabulary
- capture concrete failures such as chatty drift, provider-protocol leakage, or malformed outputs

## Behavior

- the harness or related notes record which forms appear to activate backend-native behavior
- TOAS has evidence about which structural lane is safest to lean on

## Done When

- the repo contains concrete evidence about collision-prone versus collision-resistant action syntax
