# Acceptance Pytest Options

Acceptance backend mode can be controlled directly from pytest CLI.

Precedence:
1. Explicit pytest option
2. Environment variable
3. Built-in default

Defaults:
- mode: `replay_only`
- live cutoff knobs: unset
- write live captures: `false`

Options:
- `--acceptance-backend-mode {replay_only,live_only,hybrid}`
- `--acceptance-live-from-step <int>`
- `--acceptance-live-from-label <label>`
- `--acceptance-write-live-captures {true,false}`

Examples:
- Replay-only (default):
  - `uv run pytest tests/acceptance -m acceptance --no-cov`
- Force live-only:
  - `uv run pytest tests/acceptance -m acceptance --no-cov --acceptance-backend-mode=live_only`
- Hybrid from step index:
  - `uv run pytest tests/acceptance -m acceptance --no-cov --acceptance-backend-mode=hybrid --acceptance-live-from-step=1`
- Hybrid from label:
  - `uv run pytest tests/acceptance -m acceptance --no-cov --acceptance-backend-mode=hybrid --acceptance-live-from-label=recovery_check`
