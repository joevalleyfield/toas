Filed as: 260906-endpoint-model-discovery
FKA:
AKA: endpoint models probe; served model discovery; backend model status
Legacy index:

Parent: `260906-endpoint-backend-separation`
Depends on: `260906-endpoint-backend-separation`
Blocks: `260906-model-catalog-refresh`
Related: `260901-help-system-design-survey`; `260614-shell-owned-backend-lifecycle`; `docs/notes/2026-09-06-endpoints-models-and-targets.md`

keywords: runtime, config, surface, implementation, active, provenance, contract

# Explicit Endpoint Model Discovery

## Objective

Expose endpoint-discovered model information as an explicit runtime observation
surface, using the existing model-list probe where compatible, without
conflating it with configured model values.

## Current evidence

`src/toas/llm_harness.py` already provides `fetch_models(settings)`, issuing a
GET request to the provider-compatible `/models` endpoint for non-Gemini
providers. Gemini REST has a provider-specific `/v1beta/models` path. Existing
tests cover URL construction and probe failure shaping.

## Contract

Keep these meanings distinct:

```text
configured model/catalog  static operator configuration
requested model           identifier TOAS sends for generation
endpoint models           models reported by an explicit runtime probe
```

The discovery surface must be explicit and opt-in. `/config show` remains a
local deterministic projection and must not perform network I/O implicitly.

## Scope

- Choose and document the narrow operator-facing status/inspection surface for
  endpoint model discovery.
- Reuse or extract the existing `fetch_models` transport behavior rather than
  duplicating provider URL rules.
- Return a compact success projection that distinguishes endpoint-reported
  model identity from configured/requested model values.
- Return a bounded, actionable failure projection for unavailable or
  unsupported endpoints.
- Preserve provider-specific URL behavior, including Gemini REST.
- Add tests for success, malformed/empty responses, endpoint failure, and
  read-only projection.

## Non-goals

- Do not change `llm.model`, `llm.models`, or `llm.backends` configuration
  semantics.
- Do not silently replace the configured/requested model with endpoint data.
- Do not make `/config show`, help rendering, or ordinary generation perform a
  discovery request.
- Do not assume every OpenAI-compatible server implements `/models`.
- Do not add automatic model selection based on the probe.

## Acceptance criteria

- An explicit operator action can request endpoint model discovery.
- Successful output labels endpoint-reported models as runtime observations.
- Configured/requested values remain separately identifiable.
- Probe failure is compact, bounded, and does not mutate config or history.
- `/config show` remains network-free and behaviorally unchanged.
- Existing `fetch_models` provider URL behavior remains parity-safe.

## Allowed write surfaces

- a narrow runtime/operator status or inspection seam;
- `src/toas/llm_harness.py` only for shared probe extraction or contract fixes;
- focused runtime/help tests;
- this task file and generated `tasks/WORKBOARD.md` sections.

## Required completion evidence

- example success and failure projections;
- explicit distinction between requested/configured and endpoint-reported
  model identity;
- proof that `/config show` performs no probe;
- focused and full required test results;
- compatibility notes for providers without `/models`.

## Progress Evidence

The first implementation slice adds an explicit `/models` observation action.
It reuses `fetch_models`, reports provider/endpoint/requested-model context
alongside endpoint-reported model IDs, and bounds unavailable or malformed
responses without mutating config or history. The command is registered in
full help, while `/config show` remains unchanged and network-free.

Selection, catalog refresh, and provider-specific fallback policy remain open.
