## Goal

Run a focused coverage-led refactor pass that improves testability and uses uncovered seams to expose and address code smells we have deferred.

## Why Now

Coverage trend has been slipping while complexity has accumulated in high-churn runtime paths. Using targeted tests as the forcing function is the fastest way to improve reliability and reveal architectural cleanup priorities.

## Scope

- establish a prioritized low-coverage target list in `src/toas` (start with high-complexity/high-churn modules)
- add focused tests that lock intended behavior at seam boundaries before refactoring internals
- refactor for testability where needed (smaller units, clearer boundaries, lower closure/state coupling)
- document code smells uncovered during the pass and either fix them or open follow-on tasks immediately
- keep behavior and durable-history invariants unchanged

## Intended Behavior

- coverage improves in targeted modules
- newly added tests are deterministic and scenario-focused rather than snapshot-heavy
- refactors reduce cognitive load and make failure modes easier to isolate

## Constraints

- no semantic drift in transcript/history contracts
- no broad speculative rewrites; iterate in small validated slices
- each material change stays stitched to this task and roadmap focus

## Done When

- targeted module list is completed or explicitly triaged into follow-on tasks
- coverage rises in touched areas with passing test suite
- at least one concrete deferred smell is resolved or split into a tracked follow-up task

## Progress

- added focused branch tests for newly extracted operator-command handlers in `tests/test_runtime_operator_command_handlers.py`
- raised post-extraction coverage in new runtime modules:
  - `operator_command_extract_replay.py`: `74%` -> `85%`
  - `operator_command_config_help.py`: `56%` -> `73%`
  - `operator_command_prompt_workspace.py`: `68%` -> `73%`
- full-suite validation (elevated env): `935 passed`, total coverage `89.15%`
- added post-decomposition branch tests for extracted daemon facade modules (`tests/test_daemon_facade_helpers.py`, `tests/test_daemon_facade_process.py`) covering no-op/error/delegation paths
- raised full-suite coverage after facade tightening: `89.56%` -> `89.64%` (`963 passed`)
- added focused parsing/error-path coverage for `cli_dispatch` and validation/edge-path coverage for `daemon_run_store`
- raised full-suite total coverage to `90.05%` (`970 passed`) and bumped repo coverage gate from `80` to `90` in `pyproject.toml`
- removed UTF-8 BOM from `src/toas/reconcile.py` so `code_survey` no longer skips it on AST parse
- post-`433` reassessment opened helper branch-tightening follow-on `437` targeting extracted runtime command handler helpers
- completed helper branch-tightening follow-on `437` with focused tests across extracted runtime helper seams; coverage now includes improved runtime module confidence (`operator_command_config_help` to `82%`, `operator_command_prompt_workspace` to `80%`, `operator_command_extract_replay` to `89%`)
- added folded-flag parser negative-path tests for `operator_command_prompt_workspace` (`/lens packet --folded/--expand`) to lock usage/error branches and keep extraction-command handler coverage tightening under active runtime changes
- code-survey checkpoint rerun (editable-project `uv run` AST pass) confirms remaining highest-size hotspots are still `cli.py`, `graph.py`, `step.py`, `llm.py`, then runtime command handlers (`operator_command_prompt_workspace.py`, `operator_command_extract_replay.py`); next tightening slices will continue targeting runtime command handlers before broader top-level modules
- removed an unreachable post-parse `/lens packet` argument guard in `operator_command_prompt_workspace` after folded-flag parser introduction (small deferred smell cleanup with no behavior change)
- added folded-outline edge-case tests (`no artifacts`, ref-cap without explicit expansion) to tighten `runtime/context_assembly` branch confidence around compact packet projection behavior
- reduced repeated message-id lineage collection in `runtime/operator_command_prompt_workspace._handle_lens` by extracting a shared helper used by packet/doctor/set paths (small branch-density and maintenance-smell reduction)
- extracted `/lens packet` flag parsing to a dedicated helper (`_parse_lens_packet_args`) and added direct parser tests for mode/auto-fold/error paths to keep command-path branch behavior explicit
- extracted lens packet summary rendering and lens-doctor suggestion selection into dedicated helpers (`_render_lens_packet_summary`, `_lens_doctor_suggestions`) with direct helper tests to reduce literal/branch density inside `_handle_lens`
- extracted lens-set frontier-content and source-pointer validation helpers (`_frontier_user_content`, `_validate_lens_source_ids`) with direct helper tests to flatten the `/lens set` branch and keep error construction deterministic
- extracted replay-queue payload iteration helper (`_iter_queue_payloads`) in `runtime/operator_command_extract_replay.py` and reused it across latest-state collectors, with direct iterator filtering tests
- added deterministic `procedures.py` branch-matrix coverage (invalid-name, invalid-YAML, invalid-asset-shape, placeholder-missing, defaults-shape, and list filtering/sorting) via monkeypatched resource-root fixtures in `tests/test_procedures.py`
- full-suite validation after coverage pass: `1130 passed`, total coverage `91.04%`
- expanded `tools_cluster/shell_ops.py` coverage with validation/context/launcher/timeout branch tests (`validate_shell_args`, `validate_shell_script_args`, `run_user_shell`, `execute_shell_call`, `run_subprocess` timeout path)
- expanded `tools.py` boundary coverage with procedure-argument forwarding/failure-path tests plus workspace/shell policy helper-path tests (`workspace_policy`, `shell_allow_policy`, `_workspace_path`, `_effective_shell_allowed`)
- full-suite validation after shell+tools pass: `1140 passed`, total coverage `91.36%` (`tools_cluster/shell_ops.py` now `93%`)
- added mixed-intent ordering regression coverage for source-order arbitration behavior (`in_order`/`first_wins`/`last_wins`) plus help-surface coverage for compact/full/approvals and tool default-arg rendering
- full-suite validation after 451/452/453 sequence: `1144 passed`, total coverage `91.39%`
- post-455 code-survey-driven overlap pass with `400` landed three bounded refactor slices (`operator_config_backend_ops`, `config_parsing`, `session_step_edges`) that reduced branch concentration without semantic drift
- full-suite validation after the survey-driven pass: `1151 passed`, total coverage `91.43%`
- added direct helper-seam coverage for extracted lens parser helpers in `runtime/operator_command_prompt_workspace.py` and refactored `_handle_lens` to consume those module-level helpers
- full-suite validation after lens-helper decomposition pass: `1152 passed`, total coverage `91.45%`
- removed legacy duplicate matcher/diagnostic helper block from `tools.py` after prior extraction to `tools_cluster/file_match_ops.py`; this reduced denominator noise and surfaced true wrapper coverage signal (`tools.py` `59%` -> `89%`)
- full-suite validation after tools duplicate-removal pass: `1152 passed`, total coverage `92.43%`
