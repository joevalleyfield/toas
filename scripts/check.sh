#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

UVT="./.codex-local/bin/uvt"

"$UVT" run pytest
"$UVT" run pytest tests/acceptance -m acceptance --no-cov -q

if [[ "${1:-}" == "--advisory" ]]; then
  "$UVT" run ruff check src tests
  "$UVT" run mypy
fi
