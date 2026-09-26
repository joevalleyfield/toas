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

The tools are `inspect`, `read`, `write`, `commit`, and `script`; terminal
outcomes are `continue`, `finish`, and `blocked`. `inspect` returns `jj status`,
the complete `jj diff --git` patch, and the last five `jj` log entries. `read`
returns a named file. `write` replaces an existing file with complete text.
`commit` selects one or more relative paths and a description. A proposal may
contain one tool call or an ordered plan of up to eight calls. Plans run in
order without intermediate model feedback; execution stops on the first error,
and every call result is captured separately. Terminal outcomes cannot be
placed inside a plan.

`script` accepts Python or Bash source such as
`{"type":"script","language":"bash","snippet":"jj status"}` and runs it
with the fixture as its working directory and fixture-local HOME/TMPDIR. Each
snippet passes a caller-supplied safety review after the model proposes it and before execution;
without an explicit reviewer, it is rejected. The report records the full
snippet and decision. This is not an OS sandbox: an approved snippet can still
read or modify host paths or use the network. The reviewer must inspect such
effects and reject anything not needed for the fixture task. Prefer focused
tools when they suffice.

The state-only procedure explicitly says prior tool results are absent unless
preserved in state. It asks for completed progress only after results arrive
and permits concise plans to reduce inference turns. This makes instruction
and plan adherence observable while allowing the same tools in both arms.
Action timeouts, maximum turns, retries, and state/observation character limits
remain explicit. Limits do not truncate evidence. Invalid proposals leave
state unchanged; one corrective retry retains the triggering observation. A
valid patch is applied before its action; failed actions become observations
without rolling state back. This follows Algorithm 1's ordering, while failure
handling is an experiment choice rather than a production TOAS decision.

The tools expose common repository operations plus reviewed Python/Bash
snippets for work that does not fit the focused calls. `write` accepts the
documented `content` field and the common `text` alias; script source accepts
`snippet` plus common `content`, `code`, or `command` aliases. The response
capture retains the exact model proposal. An explicit review callback receives
the fixture root and exact script before launch; without a callback scripts
fail closed. A rejected script is an ordinary action error observed by the next
inference. The review hook is a human/controller decision point, not a sandbox
or an automatic safety classifier.

Patch semantics are recursive object merge, array/scalar replacement, and null
deletion. Required state fields and the native notes categories are validated on
the complete candidate. The model does not receive the evaluator's expected
partition, expected file contents, reports, or controller data.

## Artifacts and interpretation

The selected output contains `state_only/` and `history_plus_state/` fixture
roots, `pair.json` with exact adapter-boundary request messages, responses,
state transitions, observations, timings and independent repository checks, and
`summary.json` with a concise paired result. The manifest records procedure and
schema hashes, configured model and endpoint-returned model identities,
provider/transport settings, role layout, mode, budgets, initial fixture and
model-input fingerprints, and intervention count. Provider
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

## Full-diff and planned-tools follow-up

The paired run at
`/private/tmp/toas-state-live-plans-20260926T212500Z/pair.json` used identical
fixture and initial model-input hashes. The configured alias was
`qwen3.5-35b-a3b`; both runs reported
`Qwen3.8-27B-Q8_0.gguf` as the returned model. The separate
`reevaluation.json` records the current evaluator results. Both arms passed all
repository checks after treating WORKBOARD bullet order as immaterial while
still requiring the same entries and valid task/board boundaries.

State-only took three inference calls: inspect, one four-tool plan, then finish.
History-plus-state took eight calls and passed after recovering from an initial
`write` proposal that used `text` instead of `content`; the model then proposed
`echo '- subtract' >> tasks/WORKBOARD.md`. The reviewer checked the exact
snippet and fixture contents, approved this fixture-local append, and the run
recorded that decision before execution. Earlier in the iteration, the same
review gate rejected `jj abandon`, and the model repeated that destructive
request despite the rejection observation. The revised fixture instructions
now explain that an empty working-copy commit is already clean.

The run also exposed fixture/evaluator issues: adding subtraction is a feature
and its `feat(...)` description is conventional; WORKBOARD task lines are
unordered bullets; and every task reference must be valid at each commit
boundary. Those semantics are now represented directly in customs and
evaluation. One paired run remains a smoke observation, not a general model
effectiveness result.

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
