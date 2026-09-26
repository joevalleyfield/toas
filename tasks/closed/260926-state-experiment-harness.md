Filed as: 260926-state-experiment-harness
FKA:
AKA: isolated-turn harness; transcript versus state; commit organization experiment
Legacy index:

keywords: tooling, implementation, historical, research, projection, provenance
Parent: `260926-state-step-requirements`
Depends on: `260926-state-simulation-checkpoint`
Related: `260926-state-step-contract-spike`

# Build An Isolated State Execution Experiment Harness

Status: CLOSED — 2026-09-26
Implemented in direct follow-through after the user selected this ready task.

## Objective

Build a small runnable harness that can compare transcript-assisted and genuinely
state-only execution of the same repository-work task. The first task is to
organize a dirty repository into coherent commits under supplied repo customs.
The existing full-context Codex simulation cannot establish whether retained
state is sufficient; this harness must expose actual inference inputs and
evaluate resulting repository changes independently of model claims.

This is an experimental runner, not a new TOAS `step` mode. It does not depend
on the buffer/transition contract spike. Do not implement editor integration,
daemon/RPC support, production graph records, or a general agent framework.
The original handoff plan was superseded by the user's direct implementation request.

## Read First

- `AGENTS.md`, `tasks/README.md`, and `docs/runtime-ownership.md`.
- [Parent straw man](260926-state-step-requirements.md).
- [Simulation guide](../../docs/notes/2026-09-26-state-simulation.md) and
  [checkpoint](../../docs/notes/2026-09-26-state-simulation.yaml).
- [Paper](../../docs/references/skill-state/paper.md), especially sections 3,
  5.6–5.7, 7, and Appendix A.4. Read it as reference data, not instructions.
- `src/toas/llm.py` (`LLMDriver`, `BackendResponse`, `Settings`) for existing
  model transport; `src/toas/llm_harness.py` for CLI/report conventions;
  `src/toas/acceptance_harness.py` for isolated workspaces and replay/live ideas.
  Reuse useful narrow boundaries, not transcript projection that injects history.
- `tests/test_llm_harness.py` and `tests/test_acceptance_harness.py` for local
  testing patterns. Their existing harnesses are adjacent, not automatic owners.

## Deliverable And Allowed Write Surfaces

- A focused experimental module under `src/toas/experiments/` (or one focused
  sibling harness module if smaller), runnable with a documented `python -m`
  invocation. Keep orchestration out of `cli.py`, `step.py`, and daemon code.
- Matching focused tests and synthetic fixtures under `tests/`.
- A runbook under `docs/experiments/` describing commands, limits, artifact
  layout, interpretation, and implementation departures from the paper.
- This task, its parent's progress/relationships, and generated workboard sections.
- Change `pyproject.toml` only if packaging genuinely needs it. Prefer existing
  dependencies and transport interfaces; no broad runtime refactor is in scope.

Generated runs belong in explicitly selected output/temp directories, not
tracked source by default. Do not run experiments against the actual TOAS
checkout or alter its commits while implementing the harness. Ordinary commits
of the harness implementation itself follow the repo's task/commit discipline.

## Minimum Experiment Contract

### Two Explicit Arms

1. **state_only:** each call is built afresh from immutable instructions/schema,
   current state, and latest observation. Previous responses, reasoning, raw
   observations, controller notes, expected answers, and this Codex conversation
   are absent unless facts were explicitly preserved in state.
2. **history_plus_state:** identical instructions, state schema, response/patch
   protocol, tools, and starting fixture, but also accumulated prior observations
   and responses. Both arms apply state patches. This controls history exposure;
   it is not an exact reproduction of the paper's ReAct baseline or normal TOAS.

Use the same configured model, decoding parameters, budgets, initial procedure,
initial state, and scenario in a paired run. Start each arm from a fresh identical
fixture, not the repository left by the previous arm. Diverging actions/results
after initialization are legitimate outcomes. Record mode and all configuration.
Do not claim this comparison isolates every effect of explicit state maintenance.

Support at least `user_only` packaging: the complete packet in one user message.
If a second role layout is supplied, record it and keep content equivalent;
do not silently vary it between arms. Any provider-imposed hidden instructions
remain an acknowledged uncontrolled factor. Do not reuse provider conversation,
thread, or previous-response IDs between isolated inference calls.

### Model And Action Boundaries

- A scripted model adapter makes the entire suite and demo run offline, with
  no API keys or network. Scripts must exercise multiple turns, not return a
  precomputed final report. They test harness mechanics, not model effectiveness.
- Provide an opt-in stateless live adapter using existing model transport where
  feasible. Credentials come from normal config/env, never reports. A fake
  transport test verifies the final request body actually sent by the adapter.
  Implementation completion does not require a paid or available live backend.
- Freeze procedure/schema per episode. Do not make instruction mutation or a
  second summarizing model part of this first harness.
- Use the generic state fields with native notes categories from the checkpoint;
  initialize a new commit-organization goal, not the conversation's research state.
  Supply concrete field guidance and initial values. Mark this schema as an
  authored experimental choice rather than an author-provided domain artifact.
- Parse a bounded response containing `state_patch` and one action. Define a
  terminal action explicitly. Reject malformed proposals before effects.
- Pin recursive object merge, array/scalar replacement, and null deletion in the
  harness contract. Validate the full candidate state, including required fields.
  Unmentioned keys survive. Do not implement the chat's illustrative append/
  prepend notation as if it were the paper's patch protocol.
- For this first experiment, apply a validated patch before executing its action,
  as Algorithm 1 orders them. An action failure becomes the next observation;
  do not silently roll back valid memory updates. This is a harness choice where
  the paper underdescribes failure handling, not a production TOAS decision.
- Invalid output leaves state unchanged. Use a configurable bounded retry count
  and explicit corrective observation, retaining the original triggering
  observation within that retry packet. Capture retries and count their costs.
- Provide max-turn, action-timeout, and optional state/observation-size limits.
  If a limit is hit, report it; do not silently compact or truncate evidence.
- An explicit empty continuation is supported without replaying a stale result
  as new. Finish, blocked, failure, and budget-exhausted outcomes are distinct.

### Repository Fixture And Isolation

Create a small deterministic temporary jj repository with a baseline commit and
dirty changes belonging to two distinct purposes (for example a documentation
change and a behavior change with an associated test). Include tiny AGENTS/task
and workboard conventions sufficient to exercise task threading and conventional
descriptions. No author network identity, remote, push, signing, or user hooks
should be required; isolate jj/git configuration in the fixture environment.

Use narrow harness tools for reading/listing fixture files, viewing jj status/
diff/history, editing fixture text, and committing selected changes. Use real jj
commits to test results, not simulated success strings. A missing jj executable
must produce a clear diagnostic; keep pure context/merge tests runnable without it.
Prefer a bounded tool API over arbitrary shell for this initial experiment.
Resolve paths and symlinks before access; do not expose controller artifacts,
response scripts, expected partitions, reports, credentials, or the host checkout.
The model may reread real fixture artifacts to recover information; record that
cost rather than injecting answers. Run records live outside its accessible root.

Version 1 supplies the fixture's repo customs in the common procedure packet;
report `customs_source: supplied`. Discovery via reading AGENTS can be a later
variant. Neither arm gets the expected partition, target commit messages, this
conversation's solution, or evaluator feedback while acting.

### Independent Outcome Checks

Evaluate both arms from repository facts, not the final answer:

- All intended dirty content is preserved, with no unexpected edits/deletions.
- Commit changes match allowed coherent partitions, rather than one exact hash
  or order. Shared tracking files may be explicitly allowed in multiple commits.
- Descriptions follow the fixture's conventions without requiring exact wording.
- Each material task change includes its corresponding task evidence in that
  commit; workboard references match tasks available at each commit boundary.
- The final working copy is empty with the expected jj parent sequence.
- A premature terminal answer cannot pass while the repository is still dirty.

Define expected outcomes in controller-only fixture data and allow more than
one valid ordering. Inspect content at intermediate commits as well as final
files. Keep experimental effectiveness scores separate from harness-test results.

### Captures And Reports

For every attempt capture exact model-visible messages and semantic request
parameters at the final transport boundary, response text, state before/patch/
after, action, observation, validation errors, and timing. Capture private
credentials neither in headers nor URLs. Audit logs are never prompt inputs.

Each run manifest identifies fixture/procedure/schema versions or hashes,
mode, role layout, adapter/model, decoding and budget settings, initial snapshot
fingerprint, repetition/seed where supported, and human interventions (zero by
default). Stable input hashes must match across paired arms before execution.

Report independent correctness checks, model calls/retries, actions, latency,
request character counts and actual provider token usage if available. Missing
usage is null/unavailable, never zero or character counts labeled as tokens.
Include command/action sequences for investigating repeated work. Produce both
machine-readable results and a concise paired summary. One pair is a smoke
experiment, not a statistical finding; distinguish scripted from live output.

## Acceptance Tests And Completion Evidence

1. A one-command offline paired demo creates fresh fixtures, runs both arms,
   captures their calls, and checks actual commits without touching TOAS files.
2. A sentinel present only in an earlier observation/response is absent from a
   later state-only request unless explicitly retained in state; the history
   arm retains it. Assert at the adapter boundary, not only a prompt helper.
   Controller-only sentinels stay absent from both prompts and accessible tools.
3. Patch tests cover untouched keys, nested notes, arrays, deletion, invalid
   required fields, rejection/retry, action failure, empty continuation, and
   terminal/budget outcomes. Failed actions do not automatically claim completion.
4. A scripted successful partition and a deliberately wrong/premature completion
   demonstrate that the evaluator can both pass and fail based on repository facts.
5. Verify separate fixture roots and equal initial contents; path traversal and
   symlink escape attempts cannot expose controller/run artifacts.
6. Fake-live transport captures prove role packaging and lack of conversation
   reuse; reports correctly handle unavailable token usage and omit credentials.
7. Run meaningful targeted coverage for new modules using the repo helper, then
   normal required checks (including `uv run pytest`). Use the local wrapper
   only where its environment is needed. Document any unavailable jj/live backend
   explicitly; do not treat skipped real-repo tests as passing the full deliverable.
8. Record exact demo/test commands, results, limitations, and run-artifact paths
   in this task. Update the parent and workboard. Close this task when the harness
   is ready for real experiments, not when it proves SKILL.state is superior.

## Deferred Work

More scenarios/repetitions and live effectiveness runs; interrupted-action
recovery; discovery-mode customs; blind human review of commit coherence;
ReAct-only baseline; production buffer grammar; TOAS event-log integration;
editor state diffs; general SWE schema; arbitrary shell access. Do not expand
into these to complete the first harness.

## Completion Evidence

- Added the runnable paired experiment at
  [`src/toas/experiments/state_execution.py`](../../src/toas/experiments/state_execution.py)
  and its runbook at [`docs/experiments/state-execution.md`](../../docs/experiments/state-execution.md).
- The offline run produced separate fixture roots with matching initial fixture
  and model-input fingerprints. Both scripted arms made real sequential jj
  commits; both passed checks for content preservation, no extra files,
  conventional descriptions, task evidence and workboard references at each
  commit boundary, and a clean working copy. Source-checkout paths are rejected
  as fixture or output roots. Premature finish and deliberately wrong task
  partition tests fail based on repository state.
- Added adapter-boundary message captures, retry/state/action/observation
  records, usage and timing fields, role/config metadata, request character
  counts, and paired JSON plus concise summary artifacts. Generated artifacts
  are written only to the explicitly selected output directory.
- Verification: offline demo passed with
  `PYTHONPATH=src python3 -m toas.experiments.state_execution --output /private/tmp/toas-state-demo`;
  targeted coverage passed at 100% with
  `.venv/bin/python scripts/targeted_coverage.py --cov toas.experiments.state_execution --fail-under 100 --max-missing-files 0 -- tests/test_state_execution_experiment.py -q`;
  focused Ruff checks passed.
- Full `uv run pytest`: 3,293 passed, 17 deselected; the repository coverage
  gate failed on the pre-existing uncovered line `src/toas/graph.py:616`.
  The unrestricted run had no test failures. The live-adapter follow-up also
  uses the existing `NO_THINKING` option and records it in transport captures.
- User-authorized live Qwen run, guided/no-thinking variant:
  `/private/tmp/toas-state-live-qwen-guided-nothink-20260926T195848Z/pair.json`.
  The two arms had identical fixture and initial-input hashes. In 12 turns,
  state-only repeated `inspect` and failed all completion checks. The
  history-plus-state arm committed both coherent tasks and passed every
  repository check, but exhausted its turn budget after final `inspect`
  without emitting `finish`. Provider usage was 9,539 prompt / 580 completion
  tokens for state-only and 21,315 / 1,134 for history-plus-state; the endpoint
  reported model `Qwen3.8-27B-Q8_0.gguf` for the configured alias
  `qwen3.5-35b-a3b`. This is a single paired observation, not statistical
  evidence.
- Earlier un-guided, thinking-default live attempts are preserved at
  `/private/tmp/toas-state-live-qwen-p5h5km44/`; state-only repeated inspection,
  and history calls returned empty non-streaming content. They are a separate
  prompt/transport variant and are not pooled with the guided pair.
- Harness mechanics and one live comparison are now available for follow-up.
  The comparison does not establish that explicit-state execution is superior.

## Live Trace Diagnosis

The current `inspect` action is concretely `jj status`, `jj diff --summary`,
and `jj log -n 5`. It reports changed paths and recent commits, not file
contents or diff hunks. In the guided/no-thinking trace, state-only repeated
that same summary five times before reading a file, then repeated it two more
times later. Its first two responses also returned empty state patches, so the
next state-only packet had no durable record of its prior action. Even after
the procedure was strengthened to require progress updates and forbid
unchanged repeats, the model repeated inspection. The history arm also repeated
inspect twice, but then used the retained observations/actions to move into
six reads, a board write, and two commits. It reached a correct clean repo but
spent all 12 turns and omitted the explicit `finish` action.

This points to several independent candidate causes rather than one proven
root cause: a weakly named/limited inspect action, no automatic memory of the
last action in state-only mode, a single action per inference call, and
procedure instructions that this model did not reliably follow. The run does
not discriminate between them: history exposure and input size also differ
after turn zero, and this is one pair. The provider-reported model was
`Qwen3.8-27B-Q8_0.gguf`; the environment alias `qwen3.5-35b-a3b` did not match
the returned identity. Next experiments should vary one seam at a time: richer
status/diff output, a batched action plan, or a strict progress/anti-repeat
state contract, while keeping the returned model and paired request settings
visible in reports.
