## Goal

Fix shell-grant resolution correctness so `/shell allow|deny|reset` behaves predictably in append-style transcripts.

## Why Now

Current effective-grant computation can drop prior grants because it inspects only the last line of each user message block. This causes regressions where later `/shell allow` commands appear to overwrite earlier ones unintentionally.

## Scope

- process all relevant shell-modifier command lines in user transcript content, not just trailing line
- ensure monotonic grant behavior under sequential `/shell allow ...` appends within the same user block
- ensure `reset` semantics remain explicit and deterministic
- include `shell_script` in user-context plan routing parity with `shell`
- add regression tests covering multi-command append flows and mixed prose/command blocks

## Intended Behavior

- `/shell allow mv` then `/shell allow jj` yields effective grants containing both `mv` and `jj` (unless denied/reset)
- user-frontier `shell_script` executes with user-intent shell semantics rather than assistant-bounded policy checks

## Done When

- grant-resolution regressions in append-style sessions are fixed and test-covered
- user-context shell parity includes both `shell` and `shell_script`
