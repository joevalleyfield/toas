Filed as: 261108-workspace-presentation-overrides
FKA:
AKA: workspace presentation asset overrides and customization
Legacy index:

keywords: closed, feature, runtime, assets, presentation, customization, overrides

Parent: `261108-operator-command-registry-and-descriptors`
Blocked by: `261108-operator-command-registry-and-descriptors`

# Workspace Presentation Asset Overrides and Customization

## Intent

Enable workspace-level presentation asset overrides via `.toas/assets/presentation/<family>/<name>.txt` with packaged fallback and context-aware resolution during operator command dispatch.

## Context & Motivation

Now that all slash command presentation text has been extracted from Python strings into declarative `.txt` templates across the 5 domains (`models`, `shell`, `workspace`, `transcript`, and `replay`), users and projects need the ability to customize or brand command presentations locally in `.toas/assets/presentation/`. The presentation loader should check workspace roots and command working directory overrides before falling back to packaged assets, and command dispatch should automatically activate the current context's roots and working directory.

## In Scope

- [x] Author `src/toas/assets/presentation_loader.py` with `load_presentation_template`, `list_presentation_templates`, `clear_presentation_template_cache`, and `set_active_presentation_context` / `reset_active_presentation_context`
- [x] Wire edge loaders in all 5 families (`models`, `shell`, `workspace`, `transcript`, `replay`) to delegate to `load_presentation_template`
- [x] Integrate active presentation context activation into `OperatorCommandRegistry.dispatch` so slash command execution automatically respects `.toas/assets/presentation/` overrides
- [x] Author comprehensive test suite in `tests/test_assets_presentation_loader.py` maintaining 100.00% statement coverage under `./scripts/check.sh`
- [x] Mandatory operator-perspective end-to-end verification

## Out of Scope

- Extensible runtime plugin loading (future capability track)

## Acceptance Criteria

1. [x] Workspace presentation asset overrides loaded from `<root>/.toas/assets/presentation/<family>/<name>.txt` taking precedence over packaged assets.
2. [x] Precedence order: workspace roots in order -> command cwd -> current working directory fallback -> packaged asset.
3. [x] Slash command dispatch automatically activates the operator command context's workspace roots and cwd.
4. [x] All 5 domain edge loaders updated without breaking existing contracts.
5. [x] Full test suite passing with 100.00% statement coverage (4,089 passed) under `./scripts/check.sh`.
6. [x] Operator inspection confirms live workspace override on slash commands.

## Outcome & Evidence

- Built `src/toas/assets/presentation_loader.py` with `load_presentation_template`, `render_template`, `list_presentation_templates`, `clear_presentation_template_cache`, and `contextvars`-backed active context binding, supporting both domain YAML catalogs (`<family>.yaml`) and per-template `.txt` overrides in `.toas/assets/presentation/`.
- Updated `OperatorCommandRegistry.dispatch` to activate the command context's workspace roots and working directory during command execution.
- Added `tests/test_assets_presentation_loader.py` achieving 100.00% statement coverage.
- Verified live command override in an isolated workspace directory (`execute_operator_command("env", ...)` picking up a custom `.toas/assets/presentation/shell/env_help.txt` override).
