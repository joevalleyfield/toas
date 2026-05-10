# 505 Function-Intent Test Audit (Coverage vs Behavioral Confidence)

## Objective
Audit critical runtime and tooling functions by intended behavior (intent) and verify that tests assert those behaviors explicitly, not just lines executed.

## Why
Coverage ratchets improved line execution signal, but they do not guarantee intent-level correctness. We need an explicit `(function, intent) -> assertion` map to identify silent blind spots.

## Scope
- define audit method and artifact format
- run first-pass audit on current active-change surfaces (`500`, `501`, `504`, `483`, `485` vicinity)
- identify concrete missing assertions and prioritize follow-on test additions
- link findings to existing/open tasks when possible; open focused follow-ons when needed

## Done When
- a committed audit artifact exists with at least one full pass over active surfaces
- each audited function has intents and current assertion status noted
- actionable gaps are listed with proposed test targets

## Related
- `374` coverage-led refactor pass
- `379` coverage noise burndown
- `400` decomposition umbrella
- `504` missing-files ratchet gate

## Progress
- expanded intent assertions for replay script/runtime boundaries in `tests/test_replay_runner.py`:
  - missing-script and invalid-yaml errors
  - malformed top-level/steps contracts
  - invalid step-field typing and source normalization
  - artifact write payload shape and newline termination
- expanded daemon async worker behavioral assertions in `tests/test_daemon_async_runner.py`:
  - terminal-emitted stdout-proxy suppression with pending-line flush behavior
  - in-process worker exception path (error + llm_done + terminal record)
  - env restoration branch where prior env value existed
  - start_async_step fallback branch when config/event discovery raises
- opened task and defined first-pass audit scope/artifact
- closed first behavioral gap slice on `shell_streaming` exception-tolerance intents:
  - added explicit tests for `stdout is None` reader short-circuit behavior
  - added explicit tests for reader-loop tolerance of `set_blocking` errors, `BlockingIOError`, and `unregister` failure
  - revalidated full suite with `-n 14`
- closed debug-disabled logging intent assertion for `shell_streaming`:
  - added explicit test that `_stream_debug` performs no write when debug flag is disabled
- stabilized `rpc_unix` intent assertions to reduce xdist coverage nondeterminism:
  - added deterministic `_serve_connection` protocol-error path assertion
  - added deterministic `_serve_connection` success path assertion
- closed operator API session-path compatibility intent assertions:
  - added explicit rebuild-session test for legacy `session.md` copy-forward into configured `.toas/session.md`
  - added explicit compatibility-copy error-tolerance test for `_ensure_session_path_compat` when target parent cannot be created
- closed shell-ops intent assertion gaps on parsing/normalization/rendering branches:
  - added windows env normalization assertion for canonical-key preservation when alias variants are present
  - added shell-script validation assertion for unparseable command segment rejection
  - added shell-script env override merge assertion for valid mapping path
  - added subprocess content-shaping assertion that includes non-empty `stderr` in rendered content
  - added user-shell argv fallback assertion for shlex parse failure and blank-command normalization path
