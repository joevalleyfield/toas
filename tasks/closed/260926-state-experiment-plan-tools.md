Filed as: 260926-state-experiment-plan-tools
FKA:
AKA: state experiment richer tools; planned tool calls; reviewed repo scripts
Legacy index:

keywords: tooling, implementation, historical, usability, exploration, shell
Parent: `260926-state-step-requirements`
Related: `260926-state-experiment-harness`; `260926-state-step-contract-spike`

# Improve tools and plans in the state execution experiment

Status: CLOSED — 2026-09-26

## Objective

Improve the experiment protocol at the failure seams found in its first local
Qwen pair: inspection did not expose the actual patch, one inference could
request only one tool action, and instructions did not reliably prevent repeat
work. Consider repository work as open-ended: offer a general script tool as
well as focused repository tools, with a safety review before script execution.

## Acceptance

- `inspect` reports complete `jj diff --git` output, status, and recent history.
- A response may request an ordered plan of several calls; the runner records
  each call and observation and stops when a call fails.
- The procedure clearly describes tool capabilities, plan semantics, and
  progress memory. The endpoint-returned model remains the reported identity.
- Python and Bash snippets are expressible as a script tool. Each script passes
  a caller-supplied safety review after proposal and before execution; absent
  reviewer or rejection must fail closed. Reports preserve the exact proposal,
  review result, and execution observation without credentials.
- Scripts run from the fixture root with fixture-local temporary/home paths;
  documentation states that this is not an OS security sandbox and the safety
  reviewer must inspect effects outside the fixture, network access, and
  destructive operations.
- Run a paired live comparison with the same returned model/configuration and
  initial fixture, and record limits without claiming statistical proof.

## Completion Evidence

- `inspect` now includes status, full `jj diff --git`, and recent history.
- Proposals may contain ordered plans of up to eight calls. Results are
  captured per call, and execution stops on the first failure.
- The prompt describes the tools and plan behavior, asks state-only runs to
  preserve important facts explicitly, and provides exact JSON examples.
- Python/Bash snippets run from the fixture with a reduced fixture-oriented
  environment. A caller-supplied reviewer sees the exact proposal before
  execution. No reviewer or an explicit rejection fails closed. This is not an
  OS sandbox; the runbook records the limits and review criteria.
- Reports distinguish the configured alias from endpoint-returned model names
  and preserve script proposals, review decisions, observations, and timing.
- `write` accepts `content` and the common `text` alias; scripts accept the
  canonical `snippet` plus `content`, `code`, and `command` aliases. The exact
  proposed action remains in the record.
- The fixture customs/evaluator now recognize `feat(...)` for new capability
  work, require valid task/WORKBOARD boundaries, and ignore WORKBOARD bullet
  ordering while checking entry preservation. A terminal `finish` is reported
  as failure when any independent check fails.
- User-authorized paired live run:
  `/private/tmp/toas-state-live-plans-20260926T212500Z/pair.json`;
  current-evaluator reassessment is in `reevaluation.json`. Initial fixture and
  input fingerprints matched. Both arms reported
  `Qwen3.8-27B-Q8_0.gguf` despite the configured `qwen3.5-35b-a3b` alias. Both
  arms passed every repository check after reassessment. State-only used one
  four-call plan and finished in three model calls. History-plus-state took
  eight calls, recovered from a `write` field alias error through a reviewed
  fixture-local Bash snippet, and finished. This is one paired smoke run.
- Earlier live iteration rejected a proposed `jj abandon` command before
  execution; Qwen repeated it after rejection. The fixture procedure now
  explicitly states that an empty working copy is clean.
- `python3 -m py_compile src/toas/experiments/state_execution.py` passed.
  The repository test suite was not rerun during this follow-on.

The production TOAS `step` contract remains out of scope.
