#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

# Optional site-local pre-flight hook (e.g. declutter / cloud-drive boundary checks)
LOCAL_PRECHECK="${TOAS_LOCAL_PRECHECK:-${DEV_LOCAL_PRECHECK:-$HOME/.config/dev.local/check-pre.sh}}"
if [[ -f "$LOCAL_PRECHECK" ]]; then
    # shellcheck disable=SC1090
    source "$LOCAL_PRECHECK"
fi

# Use the portable runner so this script works in Codex Cloud and other clean
# environments. Local contributors may still invoke .codex-local/bin/uvt
# directly when they need the declutter-managed developer environment.
uv run pytest
uv run pytest tests/acceptance -m acceptance --no-cov -q
uv run ruff check src tests
uv run mypy
