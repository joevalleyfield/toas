Filed as: 260903-user-lane-timeout-recovery
FKA:
AKA: direct user timeout; no user retry frontier; source-preserving run recovery; executable-fence recovery
Legacy index:

keywords: runtime, projection, implementation, historical, correctness, contract, transcript, frontier, provenance, authority, policy, timeout

Status: closed (2026-09-19)

Parent: `260831-transcript-source-reference-operations`
Related: `260803-assistant-execution-authority`; `260803-language-exec-fenced-block-lane`; `260901-retry-materialization-adapters`; `260901-source-reference-recovery-integration`

# User-Lane Timeout and Source-Preserving Recovery

Make direct user execution unbounded by default and distinguish its terminal-on-failure behavior from recovery of assistant source reached through `/run`, without losing the source notation that was actually executed.

## Current Reality

Assistant-originated executable work has a five-second default timeout unless
its executable source supplies `timeout_s`. The Python fence grammar now
accepts `timeout_s`, and the retry-materialization adapter can preserve an
executable fence while adding or updating that attribute for bounded
assistant-source recovery.

The remaining behavior has not been made explicit at the user-lane/recovery
boundary: a direct user Python fence may inherit the assistant five-second
default, and generic failure handling may synthesize an editable `Retry failed
operation` frontier even though the user action should stop at its result.
Earlier recovery work also concentrated on normalized YAML plans, leaving a
risk that a failure reprojection chooses YAML solely because it is executable.

## Desired Reality

Direct user execution has no TOAS-imposed timeout by default. An active,
explicit `timeout_s=N` remains a supported and enforced bound. Host safety,
cancellation, and process cleanup remain available; “unbounded” is not a
promise that a process cannot be interrupted.

When a directly executed user action fails—whether it is the original turn, a
user edit, or a user-adopted retry—TOAS records and displays the result, then
stops that action. It must not append a synthesized retry user message or
create a retry frontier.

A `/run` is instead an execution of selected assistant source under the
assistant policy lane. If it fails, the established generic recovery path may
produce recovery, but it must reproduce the closest available source form:
Python and Bash fences stay fences, YAML stays YAML, and normalized tool-call
YAML is only an explicit input form or last-resort fallback. This distinction
is based on execution/source semantics, not authorship alone.

## Required Contract

```text
direct user executable source
  -> direct-user timeout policy (unbounded unless source says timeout_s)
  -> execute
  -> failure result only; no generated retry frontier

/run selected assistant source
  -> assistant policy/timeout lane
  -> execute selected source
  -> generic recovery on failure, preserving the selected source notation
```

Recovery/source reproduction must use the closest authored source available
for any origin. Authorship can describe authority of the executed lane, but it
must not be the discriminator for source representation or whether a generic
recovery frontier is justified.

## Scope

- Locate and make explicit the direct-user timeout-policy resolution seam for
  executable fences and existing YAML/tool execution.
- Preserve explicit `timeout_s` in active Python fences and prove it reaches
  execution.
- Make direct-user failure terminal for the current action across original,
  corrected, and adopted-retry user turns.
- Route `/run` failure through generic assistant-plan recovery using the
  representation-neutral materialization seam; preserve fence source and its
  body/formatting where the adapter supports it.
- Retain normalized YAML/tool execution as supported explicit input and as a
  clearly diagnosed fallback only when no closer faithful source exists.

## Non-goals

- Removing cancellation, process cleanup, or external host limits.
- Changing the assistant default timeout or broad grant/authority policy.
- Adding new executable languages or fence attributes beyond established
  contracts.
- Replacing the source-reference selection grammar or creating a second
  recovery state machine.

## Acceptance Evidence

- A direct user Python fence sleeping longer than five seconds succeeds without
  an explicit timeout.
- `timeout_s=N` in an active Python fence is honored, including a timeout
  failure fixture that distinguishes it from the default.
- Failed direct user source produces a visible error result and no synthesized
  `Retry failed operation` user message, for an original turn, a user-edited
  correction, and a user-adopted retry.
- A failing `/run` against Python and Bash fences may recover, and its
  projection retains the original fence notation, header/body formatting, and
  lineage; a YAML source remains YAML.
- Tests prove recovery disposition is selected from execution/source semantics,
  not a test such as `author == "assistant"` alone.
- Existing explicit YAML/tool-call execution remains covered, including its
  documented fallback when faithful source reproduction is unavailable.
- Focused runtime tests, formatter/lint checks, and the full suite pass; record
  the owner seam, fixtures, verification commands, and commit in this task.

## Likely Ownership

- Timeout and consequence routing: `src/toas/runtime/`.
- Fence parsing/source spans: `src/toas/runtime/markdown_fence.py` and the
  existing retry-materialization adapter.
- Tool timeout contract: `src/toas/tools_cluster/` through the public
  `tools.py` registry facade.
- Integration tests: the existing runtime source-reference, fence, and
  step-runtime test modules.

## Next Actions

1. Add a failing end-to-end direct-user Python-fence fixture for a six-second
   sleep with no timeout, then trace policy resolution to the missing lane
   default.
2. Add paired explicit-timeout and direct-user-failure fixtures covering the
   three user-origin scenarios.
3. Extend `/run` failure integration fixtures for Python, Bash, and YAML;
   assert source form and byte-preservation rather than merely parsed command
   equivalence.
4. Refactor the generic recovery input, if needed, to use source/execution
   semantics rather than authorship as its decision key.

## Completion Evidence

- Direct-user execution now passes an explicit unbounded timeout policy for
  timeout-capable tools when no `timeout_s` is authored; explicit positive
  `timeout_s` values remain enforced.
- Direct-user failures now project only their result and stop. This covers
  original user plans and user-edited/adopted retry frontiers. Assistant-side
  `/run` recovery retains its existing generic recovery behavior.
- Executable-fence recovery preserves Python and Bash fence source, including
  the authored body and header while materializing the assistant timeout.
  YAML/source-span recovery remains covered by the existing representation-
  neutral tests.
- Owner seams: timeout policy in `src/toas/step.py` and
  `src/toas/tools_cluster/execution.py`; terminal disposition in
  `src/toas/runtime/step_runtime.py`; source-preserving `/run` recovery in
  `src/toas/runtime/source_reference_operations.py`.
- Verification: `./.codex-local/bin/uvt run pytest -q` — 3235 passed, 17
  deselected, 100% coverage; focused direct-user/source-reference tests — 296
  passed; Ruff clean on changed files.
