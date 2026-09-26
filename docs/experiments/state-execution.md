# Explicit-state execution experiment

This runner is an experimental comparison, not a TOAS `step` mode. It compares
fresh `state_only` packets with `history_plus_state` packets that additionally
include prior assistant responses and observations. Both modes use the same
procedure, schema, action protocol, settings, and state patches. This controls
history exposure; it is not the paper's ReAct baseline and does not isolate all
effects of explicit state maintenance.

## Offline paired demo

Run from the repository root and choose an output directory outside the source
checkout:

```sh
uv run python -m toas.experiments.state_execution --output /tmp/toas-state-run
```

The demo needs `jj`, but no network or API key. It initializes two independent
temporary-style repositories under the selected output directory, creates a
baseline and two dirty purposes, runs a multi-turn scripted adapter, makes real
jj commits, and evaluates the resulting repositories. It is a harness smoke
check, not evidence of model effectiveness. For a live run, construct
`LiveAdapter(Settings.from_env())` from a Python caller and pass it to
`run_episode` for each independently initialized fixture. Live calls are
stateless; no conversation, thread, or previous-response identifier is passed.
The adapter uses TOAS's `NO_THINKING` option for strict structured responses and
records that choice in its run manifest.

## Bounds and actions

The model receives one `user` message (`user_only`). It contains the fixed
procedure, authored schema guidance, supplied repository customs, current state,
and latest observation. In history mode it also contains accumulated prior
responses and observations. The generic state fields are an authored experiment
choice, not an author-provided domain schema. The first version supplies customs
in the common packet (`customs_source: supplied`); discovering them from
`AGENTS.md` is deferred.

The bounded actions are `inspect`, `read`, `write`, `commit`, `continue`,
`finish`, and `blocked`. `inspect` is a fixed summary: `jj status`,
`jj diff --summary`, and the last five `jj` log entries. It identifies changed
paths and recent commits, but does not show file contents or diff hunks; use
`read` for file contents. Each model response proposes exactly one action, so
each read or commit costs another inference turn. A commit may include several
paths. There is no arbitrary shell action. Reads, writes, and commit paths are
resolved beneath each fixture and symlink traversal is rejected. Action
timeouts, maximum turns, retry count, and state/observation character limits
are explicit. Limits do not truncate evidence. Invalid proposals leave state
unchanged; one corrective retry retains the triggering observation. A valid
patch is applied before its action; failed actions become observations without
rolling state back. This follows Algorithm 1's ordering, while failure handling
is an experiment choice rather than a production TOAS decision.

Patch semantics are recursive object merge, array/scalar replacement, and null
deletion. Required state fields and the native notes categories are validated on
the complete candidate. The model does not receive the evaluator's expected
partition, expected file contents, reports, or controller data.

## Artifacts and interpretation

The selected output contains `state_only/` and `history_plus_state/` fixture
roots, `pair.json` with exact adapter-boundary request messages, responses,
state transitions, observations, timings and independent repository checks, and
`summary.json` with a concise paired result. The manifest records procedure and
schema hashes, model/provider/transport settings, role layout, mode, budgets,
initial fixture and model-input fingerprints, and intervention count. Provider
defaults are recorded as such when decoding parameters are not explicitly set.
Usage remains null when unavailable;
character counts are not represented as token usage. No credentials are copied
to reports. Keep run artifacts out of tracked source.

In the guided/no-thinking local Qwen pair, state-only issued five consecutive
`inspect` actions before reading a file; later it repeated `inspect` twice more
and reread `tasks/WORKBOARD.md`. Those summaries were identical when the working
copy had not changed. In history-plus-state, the first two `inspect` actions
were also repeats, then it read six files, updated the board, and committed the
two purposes in separate actions. It passed the repository evaluator but used
all 12 turns and did not emit `finish`. The paired trace therefore points to
three concrete limits: `inspect` is less informative than its name suggests,
state-only loses the previous action/observation unless the model writes them
into state, and the controller accepts only one action per inference. More
explicit anti-repeat instructions did not prevent state-only repeats in this
single run. These traces locate plausible failure seams; they do not establish
which change would generalize best. The endpoint-returned model was
`Qwen3.8-27B-Q8_0.gguf`; `qwen3.5-35b-a3b` was only the configured alias.

Evaluate actual preserved files, descriptions, clean status, and real jj history.
The evaluator checks the documentation and behavior task evidence and verifies
the matching task/workboard entries at each material commit boundary. It allows
multiple commit ids and chronological descriptions instead of requiring exact
hashes.
The paper's budget-matched controls motivate keeping settings aligned; its
rollback-retry behavior for invalid patches informs state-preserving retries.
The paper's limitation section emphasizes that state may omit facts that become
relevant later. A scripted pair is only a mechanics check; one live pair is not
a statistical result. Provider-injected instructions remain uncontrolled in
live runs.

## Current limitations

The scripted demo proves request isolation mechanics and exercises real jj
operations, but the scripted responses are predefined behavior and do not test
model capability. The live adapter is opt-in and requires normal TOAS provider
configuration. The evaluator checks this fixture's two expected task families
and their workboard references at commit boundaries; it is not a general commit
quality judge. The first guided local Qwen pair showed different outcomes in
these fixtures, but one pair cannot establish general effectiveness.
