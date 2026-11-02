Filed as: 261102-executable-log-harvester-and-policy-scaffolder
FKA:
AKA: command harvester; policy scaffolder; harvest events; toas policy harvest; toas policy scaffold
Legacy index:

keywords: runtime, policy, authority, harvester, events, scaffolding, matchers, cli

Parent: `260803-language-exec-fenced-block-lane`
Related: `260830-exec-grant-policy-matchers`; `261102-executable-policy-module-and-validators`

# Harvest Past Event Log Commands And Scaffold Executable Matcher Policies

Extract observed executable commands from append-only event logs (`.toas/events.jsonl`)
to profile assistant and user tool usage and scaffold tailored `.toas/policy.py`
matcher rules.

## Intent

With post-resolution executable grants (`260830-exec-grant-policy-matchers`) and
workspace policy discovery (`261102-executable-policy-module-and-validators`) now in
place, operators need an empirical bridge between what assistants actually attempt
to run in a repository and the policy rules that govern them.

Rather than authoring policies by intuition or guesswork, operators should be able
to harvest observed command patterns from canonical history (`.toas/events.jsonl`).
This tool extracts all historical executable invocations, profiles binaries,
subcommands, and flags, and can scaffold a clean starter `.toas/policy.py`
tailored to the workspace.

## Scope

- **Event Log Extraction Engine**:
  - Scan `.toas/events.jsonl` (or an explicitly provided path) for:
    - Assistant `tool_request` events containing `shell`, `shell_script`,
      `python_script`, `powershell_script`, and `interpreter_script`.
    - User shell shorthand executions (`$ ...`).
  - Normalize script strings into discrete command lines using the existing
    `shell_script_segment_commands` segmenter.
  - Tokenize invocations into executable prefix, subcommand candidate (via
    `extract_subcommand`), and flag sets.

- **Command Usage Profiling & Reporting**:
  - Group invocations by executable prefix (e.g. `git`, `uv`, `pytest`, `cargo`,
    `cat`, `rg`).
  - Aggregate statistics:
    - Total call count and authority breakdown (assistant vs user).
    - Distinct subcommands observed per prefix.
    - Flags and options observed per prefix.
  - Produce a structured CLI summary report (`toas policy harvest`).

- **Policy Scaffolder (`toas policy scaffold`)**:
  - Generate a valid, documented Python `.toas/policy.py` file based on harvested
    command profiles:
    - Common read utilities mapped to `allow_all()`.
    - Multi-command tools (e.g. `git`) scaffolded with `allow_subcommands(...)`
      using observed subcommands and recommended `deny_flags(...)` safety guards.
    - Comment annotations citing observation counts from the event log.
  - Provide `--output <path>` and `--dry-run` options (refusing to overwrite an
    existing `.toas/policy.py` unless `--force` is specified).

- **CLI Surface**:
  - Expose `toas policy harvest [events_path]` and `toas policy scaffold [events_path]`.

## Non-Goals & Deferred

- Real-time telemetry streaming: this is an offline analysis and scaffolding tool
  operating over durable event history.
- Automatic policy mutation: the scaffolder creates or previews starter files for
  human review; it never automatically updates live policy behind the operator's back.

## Acceptance Criteria

- The harvester cleanly processes `.toas/events.jsonl` logs containing mixed tool
  requests, script segments, and user shell commands.
- The command profiler correctly groups binaries, isolates subcommands, and
  tabulates flag occurrences.
- `toas policy harvest` outputs a human-readable table or summary of observed
  commands.
- `toas policy scaffold` emits a syntactically valid `.toas/policy.py` module
  that loads and executes cleanly under `load_executable_policy`.
- Safety guards prevent accidental overwrites of existing policies without `--force`.
- Full test suite passes at 100.00% statement coverage.

## Likely Ownership

- Harvester and profiler engine: `src/toas/runtime/command_harvester.py`.
- Policy generator: `src/toas/runtime/policy_scaffolder.py`.
- CLI commands: `src/toas/cli_policy_commands.py` or `src/toas/cli_dispatch_ops.py`.
- Tests: `tests/test_runtime_command_harvester.py`, `tests/test_runtime_policy_scaffolder.py`.

## Progress

- 2026-11-02: Task opened following completion of `261102-executable-policy-module-and-validators`
  and documentation of matcher development in `docs/executable-policy.md`.
