#!/usr/bin/env bash
set -euo pipefail

# Minimal outer affordance for iterative TOAS spike runs.
# Usage:
#   tools/toas_spike_loop.sh /path/to/workdir
# Expects an existing session.md in the target workdir.

WORKDIR="${1:-}"
if [[ -z "${WORKDIR}" ]]; then
  echo "usage: tools/toas_spike_loop.sh <workdir>" >&2
  exit 2
fi

if [[ ! -d "${WORKDIR}" ]]; then
  echo "workdir does not exist: ${WORKDIR}" >&2
  exit 2
fi

if [[ ! -f "${WORKDIR}/session.md" ]]; then
  echo "missing ${WORKDIR}/session.md" >&2
  exit 2
fi

(
  cd "${WORKDIR}"
  toas step >> session.md
)

