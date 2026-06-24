Filed as: 260622-enable-generation-budgets
FKA:
AKA: generation max tokens config; thinking budget per request; request token budgets
Legacy index:

keywords: config, implementation, active, correctness, llm, defaults, policy

# Enable thinking and max generation tokens budgets

## Current Reality
Generation behavior is governed by `GenerationPolicy` in `src/toas/config.py`. 
It currently exposes `thinking_mode`, `avoid_terms`, `max_retries`, `retry_delay_s`, and `transport_mode`. 
Token limits are absent. A legacy `thinking_budget_tokens` exists under `BackendStartupPolicy` but is isolated and not wired to per-request generation constraints. `max_tokens` (output limit) is missing entirely.

## Desired Reality
`GenerationPolicy` includes `thinking_budget_tokens` and `max_tokens`. 
Both are exposed via the standard config lane: 
`/config set generation.thinking_budget_tokens <n>` 
`/config set generation.max_tokens <n>`
The runtime respects these limits when constructing LLM calls, passing them to the provider API (via `max_tokens` and appropriate `extra_body`/provider-specific fields for thinking).

## Gap Analysis
1. `GenerationPolicy` lacks the new fields.
2. `src/toas/llm.py` `call_backend` does not inject `max_tokens` or thinking limits into the OpenAI client call.
3. `/help config` and `/config show` will not advertise the new keys until `config.py` is updated.
4. Need to decide default values (likely `0` or `None` to mean "unbounded").

## Known Facts / Assumptions / Unknowns
- `GenerationPolicy` is frozen; defaults apply when unset.
- OpenAI-compatible clients accept `max_tokens` directly. Thinking budgets often require `extra_body` (e.g., `thinking: { budget_tokens: N }` or similar provider-specific shape).
- Assumption: We'll use `0` or `null` to indicate "no limit".
- Unknown: Exact provider field name for thinking budget; we'll abstract it via `extra_body` injection in `backend_policy.py` or `llm.py`.

## Investigations
- Verify OpenAI client signature for `max_tokens`.
- Check if existing `BackendStartupPolicy.thinking_budget_tokens` is used anywhere; if so, deprecate or alias it to `generation.thinking_budget_tokens`.

## Models / Forecasts / Risks
- Risk: Hard limits may truncate valid reasoning or output. Mitigation: Defaults to unbounded (`0`/`null`).
- Risk: Provider incompatibility for thinking budget. Mitigation: Wrap injection in `backend_policy.py` to normalize to provider shape.

## Transformations
1. Add `max_tokens: int | None = None` and `thinking_budget_tokens: int | None = None` to `GenerationPolicy`.
2. Update `backend_policy.py` or `llm.py` to merge these into the API call kwargs/extra_body.
3. Update `step.py` `/help` examples to document the new keys.
4. Ensure `valid_config_keys()` auto-picks them up (already handled by `build_valid_config_keys`).

## Evidence
- `/config show` lists `generation.max_tokens` and `generation.thinking_budget_tokens`.
- `/config set generation.max_tokens 4096` persists and reflects in `OperatorConfig`.
- `call_backend` includes `max_tokens=4096` in the request.
- Tests/inspection confirm no regressions in default (unbounded) behavior.

## Decisions
- Default to `0` (interpreted as unbounded) to match existing numeric config patterns.
- Place fields under `generation.*` namespace for consistency.

## Open Fronts
- Provider-specific thinking budget field name (OpenAI vs Anthropic vs local). Will abstract via `extra_body` mapping.

## Next Actions
- Update `src/toas/config.py`: add fields to `GenerationPolicy`.
- Update `src/toas/backend_policy.py` / `llm.py`: wire limits into request construction.
- Verify with `/config set ...` and a dry-run generation.

## Progress
- Added `generation.thinking_budget_tokens` and `generation.max_tokens` to runtime config shape.
- Planned request wiring split: `max_tokens` stays a top-level chat-completions arg, while thinking budget is normalized into provider `extra_body` only when thinking is enabled.

## Completed
- Added `generation.thinking_budget_tokens` and `generation.max_tokens` to `GenerationPolicy` and `/config` parsing.
- Wired `generation.max_tokens` to omit the request field entirely when unbounded and to pass a concrete integer when set.
- Wired `generation.thinking_budget_tokens` through backend policy shaping only when thinking is enabled.
- Updated config/help surfaces and landed focused regression coverage for config parsing, backend policy, and request construction.
