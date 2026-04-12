## Goal

Add a model-addressable, read-only capability help/introspection tool so capability-detail lookup is not gated on operator relay, while keeping startup advertisement compact via profile-based visibility.

## Why Now

Prompt-based capability advertisement alone is too coarse for active sessions: critical-path progress slows when the model needs deeper tool/policy detail and must ask the operator to run extra prompt commands.

## Scope

- add a new read-only tool (working name: `capability_help`) that returns compact capability detail by topic/tool
- support lookup topics such as:
  - `core`
  - `shell`
  - `editing`
  - `debug`
  - specific tool names
  - optional `all` for explicit full dump
- include in tool output:
  - allowed arguments and shapes
  - key constraints/policy boundaries
  - short usage examples
- add profile-based advertisement controls for dynamic capability prompts:
  - `core|full|debug` profile lanes
  - optional hidden-tool filtering for startup prompt rendering
- keep help surface side-effect free (no execution, no writes)

## Intended Behavior

- startup capability ad stays short/high-signal by default
- model can fetch deeper capability detail on demand via tool call without waiting for operator shell/prompt relay
- low-relevance tools can be omitted from default ad while remaining available when explicitly requested

## Constraints

- preserve separation of direct user intent and model-addressable capability
- do not introduce a second execution lane disguised as help
- keep help output deterministic and concise enough for model context budgets

## Done When

- `capability_help` (or final chosen name) is available in registry and callable by model plans
- dynamic capability advertisement supports profile-based compact rendering
- tests cover topic lookup, unknown-topic handling, and profile filtering behavior
- docs/help mention the new help/introspection mechanism and profile controls

## Outcome

Implemented in current pass:
- added `capability_help` read-only model-addressable tool in `tools.py` with topic/tool lookup (`core|shell|editing|debug|all|<tool>`)
- added config-backed advertisement controls:
  - `capability_advertisement.profile = core|full|debug`
  - `capability_advertisement.hidden_tools = ...`
- wired dynamic capability prompts to honor profile/hidden-tool filtering
- added tests for help-topic lookup, unknown-topic handling, and profile filtering
- updated docs/help surfaces to advertise capability-help and profile controls
