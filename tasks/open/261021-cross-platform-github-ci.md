Filed as: 261021-cross-platform-github-ci
FKA:
AKA: github actions ci; cross-platform runners; big three runners; hosted ci
Legacy index:

keywords: tooling, implementation, active, compatibility, ci, checks, parity

Parent: `260628-project-checks-and-ci-posture`
Related: `261015-windows-compatibility-restoration`; `260628-acceptance-replay-in-routine-checks`

# Cross-Platform GitHub Actions CI

Establish automated cross-platform continuous integration across Ubuntu, Windows, and macOS runners mirroring the routine verification check spine.

## Current Reality

- Routine checks are defined canonically in `docs/checks.md` and orchestrated locally by `scripts/check.sh`.
- The routine check set is:
  - `uv run pytest` (default unit test suite with `--cov=toas --cov-fail-under=100 --cov-max-missing-files=0`)
  - `uv run pytest tests/acceptance -m acceptance --no-cov -q` (deterministic replay acceptance scenarios)
  - `uv run ruff check src tests` (linter and import ordering)
  - `uv run mypy` (type checking against Python 3.12)
- Up to now, no GitHub Actions workflow exists in `.github/workflows/`.
- Sibling repository `../toas-rhizome-pyzo-ui-smashup` runs GitHub Actions CI across the "big three runners" (`ubuntu-24.04`, `windows-2022`, and `macos-15`).
- Cross-platform restoration on native Windows and macOS has recently verified that the check spine passes on both platforms.

## Desired Reality

- A GitHub Actions workflow (`.github/workflows/ci.yml`) runs on push to main branches and pull requests.
- Matrix targets the big three runner platforms: `ubuntu-24.04`, `windows-2022`, `macos-15`.
- Environment setup installs Python 3.12, portable `uv` with cache enabled, `jj` (Jujutsu), and native `vim` (with timers/jobs/channels) across all runners.
- The workflow executes the full routine check set (`pytest` with 100% statement coverage gate, replay acceptance, `ruff`, and `mypy`), providing clear per-step diagnostics and timings.
- Documentation in `docs/checks.md` reflects the active hosted CI posture and links to the workflow contract.

## Gap Analysis

1. Absence of `.github/workflows/ci.yml`.
2. Cross-runner dependency setup (Jujutsu binary and native Vim) needs standard, reliable installation steps for Linux, Windows, and macOS.
3. `docs/checks.md` notes hosted CI was "not adopted yet" with an open trigger; that section needs updating to reflect active adoption.

## Known Facts / Assumptions / Unknowns

- Facts:
  - Pytest requires 100.00% statement coverage over all package files.
  - State execution experiments require the `jj` executable to exercise Jujutsu repository fixtures.
  - Vim terminal drivers require native Vim on PATH.
  - On macOS, `/usr/bin/vim` is preinstalled; on Linux, package `vim` provides timer/channel support; on Windows, native Vim can be set up via Chocolatey (`choco install vim -y`) or `rhysd/action-setup-vim`.
- Assumptions:
  - GitHub Actions runners have fast network connectivity and sufficient memory to run the suite in under 3 minutes per runner.
- Unknowns:
  - Whether specific Windows PATH ordering differences in Git Bash vs Command Prompt in GitHub Actions require explicit shell configuration (addressed by using `defaults: run: shell: bash`).

## Investigations

- Inspected `../toas-rhizome-pyzo-ui-smashup/.github/workflows/platform-acceptance.yml` for runner matrix conventions.
- Inspected `tests/vim/README.md` and `tests/test_state_execution_experiment.py` for external binary requirements (`vim` and `jj`).
- Measured local run time of the routine suite (~40 seconds).

## Transformations

- Create `.github/workflows/ci.yml` defining the matrix job across `ubuntu-24.04`, `windows-2022`, and `macos-15`.
- Update `docs/checks.md` to reflect the hosted CI mirror of the routine check set.
- Sync `tasks/WORKBOARD.md` to register the new open task.

## Evidence

- `scripts/check.sh` passes locally (3,595 unit tests passed with 100.00% statement coverage, 17 acceptance scenarios passed, ruff and mypy passed).
- Workflow syntax is validated via PyYAML.
- `docs/checks.md` accurately describes the remote matrix and cache strategy.
- Task tracked in `tasks/WORKBOARD.md`.

## Decisions

- Mirror all four gated routine checks in discrete workflow steps for granular UI reporting and timing.
- Target `ubuntu-24.04`, `windows-2022`, and `macos-15` as the matrix baseline.
- Use `astral-sh/setup-uv@v5` with caching, `taiki-e/install-action@v2` with `tool: jj-cli` (downloading precompiled binary rather than compiling from source), and `rhysd/action-setup-vim@v1` for cross-platform native Vim setup.
- Use `shell: bash` across all matrix platforms for unified shell execution semantics.

## Progress & Verification

- Created `.github/workflows/ci.yml` defining the matrix job across `ubuntu-24.04`, `windows-2022`, and `macos-15`.
- Updated `docs/checks.md` with active hosted CI posture, platform matrix, and tooling cache strategy.
- Synchronized `tasks/WORKBOARD.md`.
- Verified local check spine passes 100% and workflow YAML is valid.

## Open Fronts

- None.

## Next Actions

- Commit workflow and documentation changes using standard `ci:` / `tooling:` conventions.
