#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

# Use the portable runner so this script works in Codex Cloud and other clean
# environments. Local contributors may still invoke .codex-local/bin/uvt
# directly when they need the declutter-managed developer environment.
uv run pytest
uv run pytest tests/acceptance -m acceptance --no-cov -q
uv run ruff check src tests
uv run mypy
