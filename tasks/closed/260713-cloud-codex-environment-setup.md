# Cloud Codex environment setup

Filed as: 260713-cloud-codex-environment-setup
FKA:
AKA: Codex Cloud setup; hosted Codex environment; cloud uv setup
Legacy index:
keywords: tooling, migration, active, compatibility, codex, cloud, uv

## Intent

Make the repository's documented verification path usable in a Codex Cloud
environment. The checked-in `.codex-local/bin/uvt` wrapper is intentionally
machine-local because it sources a developer-specific declutter environment;
cloud tasks must invoke `uv` directly.

## Acceptance criteria

- `scripts/check.sh` works in a clean environment with `uv` and no local
  `/Users/tim/...` dependencies.
- `AGENTS.md`, `README.md`, and `docs/checks.md` distinguish the local wrapper
  from the portable `uv` command.
- Focused documentation checks confirm that no active cloud setup instruction
  requires `.codex-local/bin/uvt`.

## Progress

- [x] Make the check script portable.
- [x] Align active documentation with the portable command.
- [x] Verify the resulting command and references.

## Completion evidence

- `scripts/check.sh` now invokes `uv` directly.
- Active `AGENTS.md`, `README.md`, `docs/checks.md`, and
  `docs/acceptance/pytest-options.md` use `uv` for shared commands and label
  `.codex-local/bin/uvt` as a local-only wrapper.
- `bash -n scripts/check.sh` passed.
- The acceptance command reached dependency installation but could not run in
  this sandbox because DNS access to `files.pythonhosted.org` is unavailable.
