# State Inference Format Pilot — 2026-10-10

Task: `261010-state-inference-response-resilience`.

This is a bounded, inference-only comparison prompted by the dogfood model's
repeated prose/XML responses to an unchanged JSON state-update contract. No
proposed tool calls are executed, no patches are applied, and no model proposals
are written to dogfood history.

## Conditions

| Condition | Input difference |
| --- | --- |
| `original_reference` | The exact recorded failed packet, including the unwanted control result |
| `json_clean` | Same packet with `observation.control_results` removed |
| `split_json` | Same clean data, pretty-printed as JSON; unchanged instructions placed in a separate system message |
| `split_yaml` | Same clean data in YAML; same separate system instructions and JSON response contract |
| `json_example` | Clean original JSON packaging; one unrelated-task response example appended to instructions |
| `json_prior_turn` | Clean original JSON packaging; actual preceding accepted user/assistant exchange included before the current request |

The control result is an unwanted visibility slip, not the assumed explanation
for the central failure. Keeping it in a separate reference condition measures
its possible effect without carrying it into the alternatives.

All current-request states, tool observations, tool definitions, and output
schemas otherwise match. The prior-turn condition intentionally adds the earlier
observations and valid model response as well as the format demonstration; it
does not isolate format priming from added history. The split-JSON condition
changes message roles and textual layout together. The YAML comparison against
split JSON keeps roles/instructions constant. An example uses an unrelated task
to reduce direct copying of the expected answer.

## Run

From the dogfood workspace, using the configured loopback-only model endpoint:

```sh
uv run --no-sync python /absolute/path/to/toas/docs/experiments/261010-state-inference-format/run.py --rounds 2 --max-tokens 1800
```

On the developer machine the local `.codex-local/bin/uvt` wrapper supplies the
configured Python environment. `--offline-check` validates evaluation fixtures
and builds the variants without network calls. Live requests use the current
TOAS model settings with a fixed 1,800-token output budget, no SDK network
retries, and no automatic format repairs. The six conditions are interleaved in
a reproducible shuffled order within each of two rounds. No provider conversation
or previous-response ID is reused.

## Artifacts and Evaluation

- `manifest.json`: settings, local destination, output budget, and trial order;
  credentials and headers are not saved.
- `prior-accepted-exchange.json`: the source accepted exchange from transition
  `st_b0c9fc434f7748ddae666d60b8e709e3`.
- `rN-CONDITION.sdk-request.json`: exact arguments at the SDK boundary.
- `rN-CONDITION.response.txt`: complete response content returned by the TOAS
  model driver, without transcript projection.
- `results.json`: syntax/schema evaluation, returned model, duration, and parsed
  proposal where present.

`current_parser_json` reports whether the current bare/whole-fence parser can
decode the response. `strict_valid_proposal` additionally requires explicit
`state_patch` and `tool_calls`, matching the intended state-update envelope, and
checks basic tool argument requirements. `valid_proposal_after_prose` measures
whether one unambiguous terminal JSON proposal can be recovered after prose.
Its diagnostic extraction is not a proposed production parser. XML syntax and
empty versus nonempty state patches are reported separately.

Human inspection must assess whether retained findings are supported by the
observation, requests advance the actual goal, and the model avoids claiming
unperformed work or copying example-only facts. A syntactically valid proposal
alone does not establish task success.

Two trials per condition are exploratory evidence, not a statistical benchmark.
Sampling and server chat-template behavior remain partly uncontrolled. The
fixed response budget can truncate a long answer; conclusions must consider
whether an incomplete proposal ended because of that limit.

## Reliability Follow-Up

The follow-up adds 18 trials each for `split_json` and `json_prior_turn`, and
eight for `json_clean`. Discovery and follow-up outputs remain separate:

```sh
uv run --no-sync python /absolute/path/to/toas/docs/experiments/261010-state-inference-format/run.py --start-round 3 --counts split_json=18 json_prior_turn=18 json_clean=8 --output-dir /absolute/path/to/toas/docs/experiments/261010-state-inference-format/reliability
```

Each trial records SDK finish reasons. The same source packet, output budget,
model settings, and loopback destination are used. Conditions are interleaved;
each call starts with the specified messages and receives no earlier experimental
response. `condition_counts` and `start_round` in the manifest define scheduling.
The independent follow-up is the primary comparison; combined counts include
the two samples that selected these conditions for further study.

Report 95% Wilson binomial intervals for repeated responses on this input.
These intervals assume independent Bernoulli trials with a constant success
probability; uncontrolled server sampling and testing just one state limit that
interpretation. They are not estimates of reliability across tasks or a claim
that these input arrangements isolate the causal variable.

The terminal-JSON diagnostic can also recover JSON preceded by an XML opening
tag. Report those cases separately: this is broader than prose tolerance and
does not authorize executing XML tool calls. Inspect accepted patches and tool
arguments as well as counting format success.
