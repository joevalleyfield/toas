Filed as: 261001-local-check-pre-hook
FKA:
AKA: declutter pre-check hook; check.sh local hook; venv audit hook
Legacy index:

keywords: tooling, verification, declutter, audit, site-local, portability

# Optional Site-Local Pre-Flight Hook In check.sh

Add an optional site-local pre-flight hook to `scripts/check.sh` and provide a user-level audit script to enforce declutter boundaries (e.g., forbidding `.venv` in cloud-synced project workspaces) without sacrificing portability in clean/CI environments.

## Context

On developer workstations where projects reside in cloud-synced storage (e.g. iCloud/Drive/Dropbox), `declutter-dev-local` routes Python environments and cache artifacts to `~/Library/Caches/dev.local/` via `.envrc`. If a `.venv` directory is inadvertently created inside the project root, it causes cloud-sync churn and can cause directory-walking tools (such as `get_structure` or `code_survey`) to choke on third-party dependencies.

`scripts/check.sh` is intended to be portable across environments (Codex Cloud, CI, developer machines), so it must not hardcode site-specific paths or tools unconditionally. However, adding an optional pre-flight hook enables local developer machines to enforce site-specific declutter policies early in verification.

## Desired Reality

1. **Portable Hook in check.sh**:
   - `scripts/check.sh` checks for an optional hook file specified by `TOAS_LOCAL_PRECHECK`, `DEV_LOCAL_PRECHECK`, or defaulting to `~/.config/dev.local/check-pre.sh`.
   - If present, `check.sh` sources it before running tests or linters.
   - If absent, `check.sh` proceeds normally with zero overhead or failures.

2. **Site-Local Audit Script**:
   - A reusable script at `~/.config/dev.local/check-pre.sh` checks for `.venv` in the current working directory and exits with a helpful error message guiding the user to clean it up.
   - Optionally audits other transient directories via `declutterctl env audit` if available.

## Acceptance Criteria

- `scripts/check.sh` sources `${TOAS_LOCAL_PRECHECK:-${DEV_LOCAL_PRECHECK:-$HOME/.config/dev.local/check-pre.sh}}` if it exists.
- The hook fails early if `.venv` is present in the workspace root when the local hook script is active.
- `~/.config/dev.local/check-pre.sh` exists, is executable, and audits for `.venv`.
- In environments where the hook file does not exist, `scripts/check.sh` continues to pass without errors.
- Tests and checks pass.

## Completion Log

- **2026-10-01**: Implemented and verified site-local pre-flight check hook:
  - Added optional hook resolution in `scripts/check.sh` pointing to `${TOAS_LOCAL_PRECHECK:-${DEV_LOCAL_PRECHECK:-$HOME/.config/dev.local/check-pre.sh}}`.
  - Created executable user-level audit script at `~/.config/dev.local/check-pre.sh` that detects `.venv` in the working directory, outputs configured `UV_PROJECT_ENVIRONMENT`, and halts early.
  - Verified `scripts/check.sh` fails immediately with exit code 1 when `.venv` is present.
  - Verified `scripts/check.sh` runs cleanly when `.venv` is absent or when running in environments without the local hook.

