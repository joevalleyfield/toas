Filed as: 261029-openai-model-probe-auth-header
FKA:
AKA: openai model list auth; fetch_models bearer token; models refresh authorization header
Legacy index:

keywords: runtime, implementation, closed, auth, transport, models, probe

Parent:
Depends on: `260906-endpoint-model-discovery`; `260906-model-catalog-refresh`
Blocks:
Blocked by:
Related: `261020-endpoint-auth-discoverability`

# Transmit Authorization Header for OpenAI-Compatible Model Probes

Enable `fetch_models` to transmit the configured/resolved API key as an
`Authorization: Bearer <token>` header when probing OpenAI-compatible endpoints
during `/models live` and `/models refresh`.

## Current Reality

When `/models live` or `/models refresh` probes an endpoint,
`_handle_models_refresh` (and `_handle_models_live`) resolves the endpoint's
configured secret via `resolve_secret(source=endpoint.api_key_source, ref=endpoint.api_key_ref)`
and passes it into `Settings(llm_api_key=...)`.

However, the underlying probe implementation in `fetch_models()` (`src/toas/llm_harness.py`)
only handles authentication for `gemini-rest` (via query parameter `?key=...`).
For OpenAI-compatible providers, it invokes `_request_json(f"{settings.llm_base_url.rstrip('/')}/models")`
with empty headers (`headers = {}`).

As a result, any authenticated OpenAI-compatible endpoint (such as OpenRouter,
Groq, OpenAI, Mistral, Together, or an auth-gated proxy) returns 401 Unauthorized
on model discovery, even though `api_key_ref` is correctly configured and resolved.

## Desired Reality

When `fetch_models()` probes an OpenAI-compatible endpoint with a resolved
`settings.llm_api_key` that is set and not `"not-needed"`:
1. `_request_json` accepts an optional custom headers mapping.
2. `fetch_models()` attaches `Authorization: Bearer {settings.llm_api_key}` to
   the request headers.
3. Unauthenticated local endpoints (where `llm_api_key` is empty or `"not-needed"`)
   continue to send requests without an `Authorization` header.
4. `/models live` and `/models refresh` against authenticated OpenAI-compatible
   endpoints succeed in discovering model lists.

## Acceptance Criteria

- `_request_json` in `src/toas/llm_harness.py` accepts and includes caller-supplied
  HTTP headers.
- `fetch_models` passes `Authorization: Bearer <key>` when `settings.llm_provider`
  is not `gemini-rest` and `settings.llm_api_key` is non-empty and not `"not-needed"`.
- Unit tests verify header propagation for authenticated OpenAI-compatible probes
  and omission of headers when `llm_api_key` is `"not-needed"` or empty.
- Existing tests for Gemini REST query parameter auth and unauthenticated calls remain green.

## Completion

- `_request_json` in `src/toas/llm_harness.py` now accepts an optional `headers: dict[str, str] | None`
  mapping and passes it to `urllib.request.Request`.
- `fetch_models` attaches `Authorization: Bearer {settings.llm_api_key}` when
  probing OpenAI-compatible endpoints with a non-empty key that is not `"not-needed"`.
- Added unit tests in `tests/test_llm_harness.py` covering:
  - Custom header propagation in `_request_json`.
  - OpenAI model probe with `Authorization: Bearer <key>`.
  - OpenAI model probe with `include_raw=True`.
  - Header omission when `llm_api_key="not-needed"` or `""`.
- Added unit test in `tests/test_runtime_operator_command_handlers.py` verifying
  that `/models refresh` resolves `api_key_ref` from environment and passes it to
  `fetch_models`.

## Verification

- `./scripts/check.sh` — 3611 unit tests passed, 9 skipped, 17 acceptance tests passed, 100.00% statement coverage across all 154 files, ruff passed, mypy clean across 156 files.
- Manual inspection of CLI help and command surfaces.
