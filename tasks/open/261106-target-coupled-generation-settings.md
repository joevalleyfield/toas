Filed as: 261106-target-coupled-generation-settings
FKA:
AKA: endpoint generation settings; target-coupled generation; model-specific thinking budgets; endpoint rate limits; client-side throttling
Legacy index:

keywords: llm, runtime, configuration, targets, endpoints, generation, thinking, transport, rate-limiting, throttling, active

Related: `261106-bounded-step-quiescence`; `260509-multi-operator-orchestration`

# Target- and Endpoint-Coupled Generation Settings and Client-Side Throttling

## Intent

Couple generation parameters (`thinking_mode`, `thinking_budget_tokens`,
`transport_mode`, `max_tokens`) and client-side pacing/rate-limiting directly
to model targets and endpoints. When operators or subagents switch models,
generation settings and throttling policies flip automatically, eliminating
manual configuration churn and preventing burst-induced `429 Too Many Requests`
errors during bounded multi-turn stepping (`toas step n`).

## Context & Motivation

Generation settings are fundamentally model- and provider-specific:
1. **Thinking Posture & Budgets**: Extended thinking / reasoning models (e.g.
   Claude 3.7 with a 4096 thinking budget, DeepSeek R1) require specific
   `thinking` configurations. Fast non-reasoning models or local runners (e.g.
   Ollama, vLLM) reject requests with `400 Bad Request` if thinking parameters
   are passed in `extra_body`.
2. **Transport Mode Compatibility**: Streaming SSE chunks vs. non-streaming
   JSON responses vary across local runners, custom gateways, and cloud APIs.
3. **Flat Global Posture Friction**: In TOAS, generation knobs currently reside
   in a flat global `config.generation`. Switching models via `/model select`
   leaves prior thinking budgets or transport modes active, forcing tedious
   manual `/config set ...` commands to avoid API errors.
4. **Autonomous Burst Rate-Limiting**: With the introduction of bounded
   multi-turn stepping (`toas step n`), rapid tool-execution turnarounds can
   trigger a rapid succession of LLM calls within seconds. Without client-side
   endpoint pacing, fast autonomous runs quickly trigger provider `429` rate
   limits, causing brittle retry loops or failed tasks.

Because rate limits and generation mechanics are intrinsic to the provider
endpoint and model target, they should be defined and enforced at that boundary.

## In Scope

### 1. Three-Tier Generation Hierarchy

Resolve generation settings using a clear precedence hierarchy:

$$\text{Target Overrides} \longrightarrow \text{Endpoint Defaults} \longrightarrow \text{Global Config Fallback}$$

- **Target Overrides** (`TargetCatalogEntry.generation`):
  Specific overrides for a named target (e.g., target `claude-3-7-thinking`
  mandates `thinking_mode: enabled` and `thinking_budget_tokens: 4096`).
- **Endpoint Defaults** (`EndpointCatalogEntry.generation`):
  Baseline generation traits shared by all models on that endpoint (e.g., an
  endpoint for a local vLLM instance defaulting to `thinking_mode: disabled` and
  custom `transport_mode`).
- **Global Config** (`config.generation`):
  Fallback defaults applied only when neither target nor endpoint specifies a value.

### 2. Endpoint Client-Side Throttling & Rate-Limiting

Introduce rate-limiting knobs on `EndpointCatalogEntry`:
- `min_interval_s: float = 0.0`: Minimum delay enforced between consecutive
  outbound calls to this endpoint.
- `requests_per_minute: int | None = None`: Rolling window RPM ceiling.
- **Client-Side Throttler**:
  The generation runner checks the active endpoint throttler before issuing
  the HTTP/transport call. If the request would exceed the rate limit or violates
  `min_interval_s`, the runner smoothly sleeps client-side rather than hitting
  provider 429 errors.

### 3. Automatic Profile Flipping on Model Switch

- When selecting a target (`/model select <target>`) or an endpoint model
  (`/model select <endpoint> <model>`), the active generation and throttling
  policies flip immediately to the corresponding target/endpoint profile.
- Restores prior posture when switching back, with no manual `/config set`
  fiddling required.

### 4. Interactive Configuration & Inspection Surface

- Extend `/config` commands to inspect and update target/endpoint generation:
  - `/config target <target_id> set generation.thinking_budget_tokens <tokens>`
  - `/config endpoint <endpoint_id> set generation.transport_mode <mode>`
  - `/config endpoint <endpoint_id> set rate_limit.min_interval_s <seconds>`
  - `/config endpoint <endpoint_id> set rate_limit.requests_per_minute <rpm>`
  - `/config show target <target_id>` displaying resolved generation traits.

## Out of Scope

- Distributed multi-process rate limiting (per-process / client-side in-memory
  tracking is sufficient for the TOAS runtime and daemon).
- Automatic provider quota discovery (rates are user-configured or defaulted).

## Proposed Data Shapes

```python
@dataclass(frozen=True)
class EndpointRateLimitPolicy:
    min_interval_s: float = 0.0
    requests_per_minute: int | None = None

@dataclass(frozen=True)
class EndpointCatalogEntry:
    id: str
    base_url: str
    default_model: str = ""
    models: tuple[str, ...] = ()
    api_key_source: str = "env"
    api_key_ref: str = "TOAS_LLM_API_KEY"
    provider: str = ""
    generation: TargetGenerationOverrides = field(default_factory=TargetGenerationOverrides)
    rate_limit: EndpointRateLimitPolicy = field(default_factory=EndpointRateLimitPolicy)
    tags: tuple[str, ...] = ()
    notes: str = ""
```

## Acceptance Criteria

1. **Hierarchy Precedence**: Target settings take precedence over endpoint
   settings, which take precedence over global `config.generation`.
2. **Seamless Switching**: Switching from a target with `thinking_mode: enabled`
   to a target with `thinking_mode: disabled` immediately adjusts the request
   payload without manual `/config` interventions.
3. **Client-Side Pacing in `step n`**: Running `toas step 5` on an endpoint with
   `min_interval_s: 1.0` spaces consecutive model calls by at least 1.0 second,
   preventing burst API rejection.
4. **429 Prevention**: Rapid tool-turn loops do not trigger 429 errors on
   endpoints configured with valid RPM or interval constraints.
5. **Configuration Parity**: `/config show target <id>` and `/config target <id> set ...`
   work across both CLI and transcript slash command surfaces.
