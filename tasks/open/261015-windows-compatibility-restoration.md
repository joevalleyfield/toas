# Windows Compatibility Restoration

Filed as: 261015-windows-compatibility-restoration
FKA:
AKA: Windows restoration master task; Windows check spine; win32 compatibility
Legacy index:

keywords: runtime, hardening, active, compatibility, windows, parity, coverage

Related: `260621-windows-shell-launcher-and-path-resolution`; `260515-apply-patch-windows-crlf-hardening`; `260628-project-checks-and-ci-posture`

Status: OPEN; coordinate restoration of native Windows behavior and routine verification

## Intent

Restore the routine check spine on native Windows while preserving portable
runtime semantics. This master task owns the baseline, gap inventory,
prioritization, and progress ledger. Open focused child tasks with `Parent:`
pointing here as each seam gains a clear owner, acceptance shape, and test
story; link their evidence and closure back here.

Distinguish actual product failures from platform-specific test assumptions
and unsupported harness dependencies. Do not obtain green checks by silently
weakening coverage or skipping supported Windows behavior.

## Initial Baseline

Observed in this chat on 2026-10-14, recorded 2026-10-15:

- Checkout: empty jj merge working copy `891e4615`, parents
  `b9e28ea5d2847257f8555d454e778b1778afc92a` (preview inspection) and
  `b96d61b98936baf02ebe240aea30f888792c93ec` (inference investigation).
- Native win32, Python 3.12.13, pytest 9.0.2; Git Bash launches
  `scripts/check.sh`, with `uv` directly as the runner.
- Default suite: **79 failed, 3,424 passed, 8 skipped, 17 deselected** in
  157.48 seconds. Coverage: **99.68%**, 72 missing statements across nine
  files; the 100% and zero-missing-files gates fail.
- Replay acceptance: two attempts exited with code 1 after six passing
  scenarios, without a final summary or traceback. Cause remains unknown;
  this is not evidence that the remaining scenarios passed.
- Ruff: one PLR0913 violation, `src/toas/cli.py::_run_step`, 13 arguments
  against the configured limit of 12.
- Mypy: six errors in `src/toas/graph_journal_lock_edges.py`, involving
  unused ignores for `msvcrt.locking` and unavailable `fcntl` attributes.
- Initial sandbox execution failed before tests due to runtime/cache access;
  the baseline above came from execution outside that sandbox.

Darkengram reported 3,511 passes and 100% coverage for the preview branch.
That is useful comparison evidence, not verification of the combined Windows
checkout or proof that every observed failure is Windows-specific.

## Restoration Ledger

| Order | Slice | Evidence / initial targets | Status |
| --- | --- | --- | --- |
| 1 | Prompt asset discovery | Shared loader emitted native separators in logical references; repaired and verified through actual CLI. Child: `261015-portable-asset-discovery`. | Complete on Windows |
| 2 | Paths and filesystem behavior | Path assertions, native controls, search rendering, and file-edit fixtures repaired in the linked closed children. Symlink behavior and remaining filesystem classification remain. | In progress |
| 3 | Subprocess pipes and streaming | Synchronous client, subscription observation, typed cancellation, and reader-stall simulations repaired in closed children. Full stand-in integration module passes (11 tests). | Focused checks green |
| 4 | Shell, execution, and environment | Native default launcher and explicit WSL/Git Bash/Windows PowerShell/pwsh matrix verified in `261015-shell-launcher-reader-portability`. State experiments restored in `261017-state-experiment-windows`; broader full-spine verification remains. | In progress |
| 5 | Vim harness portability | Native ConPTY harness and 30 original failures restored in `261017-vim-harness-windows`. Native Vim selected explicitly from Git Bash is verified; mixed MSYS/native-host behavior is tracked separately in `261017-msys-vim-native-host`. | Native Windows complete |
| 6 | Static checks | Resolve Ruff argument-count violation and platform-aware journal-lock typing without blanket suppression. | Not started |
| 7 | Acceptance early exit | Safe Windows process liveness probes replace console-control signals. Acceptance now completes all 17 scenarios: 16 pass, one direct-echo launch fails with WinError 2. | Completion restored; shell failure remains |
| 8 | Coverage and full spine | Reassess remaining gaps after functional fixes; preserve the documented 100% coverage contract. | Not started |

These are investigation groups, not a complete causal attribution of all 79
failures. Other failures include daemon runner, backend lifecycle writer, task
capture, and safe-overwrite tests; assign each to a verified cause or a new
focused slice rather than assuming it belongs to an existing group.

## Verification and Closure

- [x] Capture initial Windows check-spine results and establish this master task.
- [ ] Reproduce and classify every baseline failure; link focused children and
  record targeted red/green evidence as fixes land.
- [ ] Inspect real CLI/transcript artifacts for user-facing repairs, following
  the operator-perspective verification requirements in `AGENTS.md`.
- [x] Resolve acceptance's unexplained early termination and record a complete run.
- [ ] Pass `uv run pytest`, including 100% coverage and zero missing files.
- [ ] Pass `uv run pytest tests/acceptance -m acceptance --no-cov -q`.
- [ ] Pass `uv run ruff check src tests` and `uv run mypy`.
- [ ] Pass the complete `scripts/check.sh` entrypoint on Windows and verify
  affected portable behavior on a POSIX checkout before closure.

Record revision, environment, commands, results, remaining failures, and child
task dispositions in this file as progress occurs. Any unavoidable platform
exception needs an explicit rationale and verification contract.

## Progress — 2026-10-15

- Closed `261015-portable-asset-discovery`: canonical slash-separated asset
  identifiers restore nested prompt discovery. Regression reproduced red/green;
  124 related tests pass, loader targeted coverage is 100%, changed-file Ruff
  passes, and real CLI listing was inspected. This addresses the eight baseline
  prompt-discovery failures; the full suite has not yet been rerun.
- Closed `261015-portable-path-assertions`: reproduced eight failures caused by
  test assumptions about separators, regex escaping, and translated newlines.
  Five complete test modules now pass (209 tests); both LF and CRLF physical
  index offsets are checked, including actual seek/read behavior. Ruff passes
  for those modules. No production behavior changed in this slice.
- Closed `261015-native-control-path-parsing`: shared parser preserves native
  Windows backslashes in directory/workspace/config path controls, consistently
  across execution and branch replay. Five baseline product failures pass;
  explicit LF/CRLF config digest fixtures address a sixth test failure. Combined
  focused run: 388 passes; new parser coverage 100%; real CLI native paths with
  spaces and durable command context inspected.
- Closed `261015-search-rendering-file-edit-portability`: fixed grouped search
  separators and drive-colon parsing; repaired LF/CRLF file-edit/safe-overwrite
  fixtures and escaped a diagnostic regex. Seven baseline failures addressed.
  110 focused tests pass; rendering/basic-ops targeted coverage is 100% across
  566 statements. Inspected actual search and CRLF-preserving range-edit output.
  The byte-exact overwrite guard remains enforced, including a new mismatch test.
- The broad tools reproduction also exposed shell environment, executable launch,
  and cwd failures (11 failures / 187 passes before this slice). These remain
  distinct from repaired search/file-edit behavior and are not yet revalidated.
- Closed `261015-sync-host-pipe-portability`: replaces socket-only pipe waits
  with a portable reader queue, drains final output after exit, and bounds the
  silent-child timeout path. Four baseline failures addressed; 106 tests pass,
  100% targeted coverage over 466 statements, and a real TOAS host status response
  was inspected. Remaining stand-in tests use the separate async client.
- Closed `261015-host-stream-cancellation`: test subscriptions renew at the
  unchanged bounded host deadline using the last sequence. Explicit escalation
  exposed and fixed a worker bug that classified typed cancellation as failure.
  Four baseline stand-in failures addressed. Broader checks: 101 passed with
  three known unrelated failures explicitly deselected; worker targeted coverage
  100%. Inspected a real durable cancelled run record.
- Closed `261015-shell-launcher-reader-portability`: repaired native default shell
  discovery and POSIX reader-stall test targeting. Four shell/reader modules pass
  (260 tests, 100% shell/streaming targeted coverage); full real-host integration
  passes (11 tests). Four explicit runtime cases pass independently: WSL Bash,
  Git Bash, Windows PowerShell, and pwsh. WSL declares environment transfer through
  WSLENV; no global PATH mutation or implicit runtime unification.
- Next: rebaseline the remaining suite, including state execution experiments,
  symlink behavior, Vim harness portability, static checks, and acceptance exit.
- Closed operator-requested capability gap `261015-selectable-shell-runtime`:
  project/effective `runtime.shell_runtime` argv prefix, per-call `shell_script`
  override, executable-fence forwarding, user/assistant parity, visible failures
  for missing runtimes, and unchanged executable authorization. Final related
  run: 786 passed; shell-selection targeted coverage 100%; actual CLI config and
  help inspected. No runtime-setting rename was attempted.

## Full-Suite Rebaseline — 2026-10-15

Git Bash `uv run pytest --tb=short` after the restoration slices and shell runtime
selection: **3,524 passed, 38 failed, 9 skipped, 17 deselected**, 117.42 seconds.
Coverage: **99.90%**, 23 missing statements across three files (daemon lifecycle,
state-execution experiment, journal locking). The 100% gate remains open.

The failure inventory was one newly changed prompt golden signature, six
state-execution experiment failures, one task-capture failure, and 30 Vim harness
failures. The golden was inspected and updated for the intentional `runtime`
argument advertisement; all 786 related tests subsequently passed. Keep the
full-run aggregate above as evidence of that run, not an inferred new total.

Mypy is back to the six original journal-lock platform errors; the earlier pipe
reader IO annotation mismatch was corrected. The PowerShell-launched suite
exited early without summary; Git Bash completed. Acceptance's earlier unexplained
exit and the remaining Ruff argument-count violation still need restoration work.
- Baseline counts above remain historical; do not infer a current suite total
  by subtracting this slice without rerunning the suite.

## Planning Review

2026-10-15: skimmed `docs/roadmap.md` and the manually curated workboard
triage. Their history/runtime and reproducible-check priorities remain
applicable; left their strategic claims unchanged. This task tracks the fresh
Windows evidence without rewriting the roadmap as a task ledger.

## Progress — 2026-10-17

Closed `261017-state-experiment-windows`: six reproduced experiment failures
repaired through Bash selection, short real jj fixtures, junction containment,
and evaluator separator normalization. Final focused run under Git Bash:
27 passed, 394 statements at 100% coverage; Ruff passes. Actual CLI artifacts
show both arms finished with every independent evaluator check passing.

Full suite before the final absolute-Bash-path correction: **3,532 passed,
32 failed, nine skipped, 17 deselected**, 153.77 seconds, **99.97% coverage**,
six missing statements. One experiment failure exposed Windows executable lookup
selecting the WSL shim despite Git Bash discovery; fixed and verified by the
complete focused run. The other failures were task capture (one) and Vim harness
(30). These are measured run totals, not a post-correction aggregate.

Next slices: task-capture portability, Vim harness support, journal-lock typing
and coverage, daemon lifecycle coverage, Ruff, acceptance exit, then full spine.
Closed `261017-task-capture-windows`: micro captures now return and durably
record slash-separated workspace-relative paths consistently with other routes.
Reproduced one failure / 32 passes, then 33 passes with 100% targeted coverage
across 492 statements. Ruff passes. Inspected real registry JSON, task Markdown,
and durable event; repeated capture neither duplicates the checklist nor ledger.
Next functional slice is Vim harness portability (30 failures in last broad run).
No newer full-suite aggregate is claimed.
Closed `261017-vim-harness-windows`: native ConPTY exercises every original Vim
contract, including live keystrokes and real Python hosts. The related native
run passed 37 tests; the final terminal module separately passes four tests,
including explicit runtime override precedence. Safe host owner/record probes
replace Windows console-control signals with the existing process-query API,
now runtime-owned with a daemon compatibility import. Runtime process/host/state
coverage: 94 passes, 284 statements at 100%. Changed-file Ruff and focused mypy pass.
Inspected actual successful answer and thinking-lane Vim transcripts.

### Native PowerShell rebaseline — 2026-10-17

uv run pytest --tb=short completed: **3,565 passed, six failed, eight skipped,
17 deselected**, 207.66 seconds, **99.96% coverage**, nine missing statements:
cli_session_commands (three), daemon lifecycle (two), journal locking (four).
All Vim checks pass. Native PATH exposes shell/frontier failures tracked in
`261017-native-shell-frontier`; do not conflate this environment with Git Bash.
The later runtime-override regression passed separately; totals remain measured.

Acceptance also completes: **16 passed, one failed**, 9.34 seconds. Direct echo
launch in mixed multi-instance in_order fails with WinError 2 and is tracked with
the shell/frontier slice. Earlier premature termination is no longer reproduced
following the owner-probe repair; acceptance success remains an open gate.

Git Bash explicitly selecting native Vim passes baseline, live timer input,
and real-host smoke (three tests). Its default MSYS Vim is a separate runtime:
baseline path repair passes, but real-host exit hits E282 on an MSYS temporary
file. Track that contract in `261017-msys-vim-native-host`; do not report the
stopped mixed-runtime exploratory suite as a completed rebaseline.

Next: native shell/frontier classification, static checks and remaining coverage,
then complete check.sh with an explicit native Vim selection and POSIX parity.

### Upstream integration — 2026-10-20

Committed restoration as `0bf3fe6d`, then merged upstream
`push-orkquzksqvxv` at `05ea49fb` (includes release 0.0.4.0).
Only textual conflict was generated WORKBOARD content; regenerated from merged
tasks with upstream manual triage preserved. Roadmap and manual triage skimmed;
strategic claims left unchanged. Both explicit shell runtime selection and the
upstream streaming context/environment fix survive the merge.

Adjusted two real streaming-process fixtures to pass a complete environment
and use `sys.executable`, matching the upstream subprocess contract on Windows.
Focused merge regressions: 651 passed in 8.73 seconds. Ruff passes for merged
code and changed fixtures. Inspected actual endpoint help output. This is
focused merge validation, not a new full-suite or acceptance rebaseline; the
remaining gates above stay open.
