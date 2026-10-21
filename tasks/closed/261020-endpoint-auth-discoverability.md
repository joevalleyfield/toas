Filed as: 261020-endpoint-auth-discoverability
FKA:
AKA: endpoint environment-variable authentication help
Legacy index:
keywords: config, implementation, closed, usability, surface

# Endpoint authentication discoverability

Make endpoint configuration fields discoverable from `/help config endpoint`,
including environment-variable API-key configuration, and point operators to
`api_key_ref` when `/config endpoint add` succeeds.

Acceptance:

- `/help config endpoint` names the endpoint fields and explains that
  `api_key_ref` is an environment variable name (defaulting to
  `TOAS_LLM_API_KEY`).
- `/config endpoint add NAME BASE_URL` includes a next-step command for setting
  `NAME.api_key_ref`.

## Completion

- `/help config endpoint` now lists endpoint fields and describes
  environment-variable authentication and its default variable name.
- `/help config endpoint set` resolves to the same full endpoint guidance.
- An incomplete `/config endpoint set` prints the full field list and
  environment-variable auth syntax/defaults.
- Endpoint-add output points directly to `api_key_ref` setup.
- Endpoint help now uses `NAME` consistently in endpoint-set examples.
- Updated the exact-output assertion for endpoint addition.

Verification:

- Rendered `/help config endpoint` from the local runtime and inspected the
  complete output.
- Rendered `/help config endpoint set` from the local runtime and inspected
  the complete output.
- Focused help and endpoint tests — 197 passed.
- `./scripts/check.sh` — 3512 passed, 100.00% coverage, all checks passed.
