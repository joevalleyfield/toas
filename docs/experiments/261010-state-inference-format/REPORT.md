# State Inference Format Pilot: Results

The larger [reliability follow-up](reliability/REPORT.md) now provides 44
additional trials and state-maintenance inspection. This report retains the
original two-trial discovery results.

The subsequent [payload investigation](payload-ablation/REPORT.md) tests lighter
content/representation changes and finds instruction member order worth pursuing
before adding prior exchanges.

Twelve isolated local-model calls completed: two trials per condition, with no generated tool calls executed and no proposals applied to state or dogfood history. See [runbook](README.md), [manifest](manifest.json), [evaluations](results.json), and [runner](run.py).

## Result

Separate plain instructions in a system message plus readable JSON data, and an actual prior accepted exchange containing a valid state patch, each produced valid bare-JSON proposals in both trials. The added unrelated-task example did not improve the original packaging in these trials. YAML also failed under the same separate system instructions. These are promising directions for further matched experiments, not measured reliability estimates.

| Condition | Valid under current parser + explicit proposal fields | Valid allowing preceding prose | XML-style tool syntax |
| --- | ---: | ---: | ---: |
| `original_reference` | 0/2 | 1/2 | 1/2 |
| `json_clean` | 0/2 | 0/2 | 2/2 |
| `split_json` | 2/2 | 2/2 | 0/2 |
| `split_yaml` | 0/2 | 0/2 | 2/2 |
| `json_example` | 0/2 | 0/2 | 2/2 |
| `json_prior_turn` | 2/2 | 2/2 | 0/2 |

## Per-Trial Evidence

| Trial | Strict valid | Valid after prose | Seconds | Response | SDK request |
| --- | --- | --- | ---: | --- | --- |
| `r1-original_reference` | False | True | 76.237 | [text](r1-original_reference.response.txt) | [JSON](r1-original_reference.sdk-request.json) |
| `r1-json_prior_turn` | True | True | 12.486 | [text](r1-json_prior_turn.response.txt) | [JSON](r1-json_prior_turn.sdk-request.json) |
| `r1-split_yaml` | False | False | 11.398 | [text](r1-split_yaml.response.txt) | [JSON](r1-split_yaml.sdk-request.json) |
| `r1-split_json` | True | True | 37.27 | [text](r1-split_json.response.txt) | [JSON](r1-split_json.sdk-request.json) |
| `r1-json_clean` | False | False | 5.797 | [text](r1-json_clean.response.txt) | [JSON](r1-json_clean.sdk-request.json) |
| `r1-json_example` | False | False | 17.062 | [text](r1-json_example.response.txt) | [JSON](r1-json_example.sdk-request.json) |
| `r2-json_prior_turn` | True | True | 21.648 | [text](r2-json_prior_turn.response.txt) | [JSON](r2-json_prior_turn.sdk-request.json) |
| `r2-json_example` | False | False | 10.183 | [text](r2-json_example.response.txt) | [JSON](r2-json_example.sdk-request.json) |
| `r2-split_yaml` | False | False | 8.574 | [text](r2-split_yaml.response.txt) | [JSON](r2-split_yaml.sdk-request.json) |
| `r2-split_json` | True | True | 19.673 | [text](r2-split_json.response.txt) | [JSON](r2-split_json.sdk-request.json) |
| `r2-json_clean` | False | False | 4.302 | [text](r2-json_clean.response.txt) | [JSON](r2-json_clean.sdk-request.json) |
| `r2-original_reference` | False | False | 9.299 | [text](r2-original_reference.response.txt) | [JSON](r2-original_reference.sdk-request.json) |

## Operator-Perspective Inspection

- `r1-original_reference` contains a long prose analysis followed by one complete JSON proposal with retained CLI facts and bounded exploratory requests. The current parser rejects it. This is concrete evidence for the requested prose-prefix tolerance, independent of the XML-only failures.
- Both split-JSON trials retain useful findings from the current grep observations in state, and request relevant source reads. The first also records speculative implementation direction as a pending proposal; it does not claim the change is implemented. The second produces a compact CLI line map and a focused bounded read.
- Both prior-turn trials return nonempty patches and relevant source requests. The second reintroduces AGENTS/task block references from the older exchange but does not persist the new grep-derived line map. Prior-turn context can improve format adherence while drawing attention back to earlier observations; assess that tradeoff in a longer episode.
- The example trials contain no JSON state proposal. One proposes a shell argv containing literal pipe tokens while trying to inspect tasks, illustrating that output format failure and poor requested-call semantics can coexist. No requests were executed.
- The YAML and clean JSON failures likewise return prose/XML tool syntax without a state update. No amount of prefix stripping alone can accept those responses.

## Limits and Next Experiments

All twelve responses report the same returned model: `Qwen3.8-27B-Q8_0.gguf`; the configured alias remains `qwen3.5-35b-a3b`. Thinking is disabled, stream mode enabled, and each call has the same 1,800-token output budget. No output requested tool execution in the experiment itself; requests were collected as data. Sampling settings and server prompt rendering were not changed, and no deterministic decoding claim is made.

Two trials per condition are too few to establish reliability or a causal account of the original regression. Original-reference outcomes themselves varied: one valid proposal after prose, one XML-only response. Removing the control result did not resolve the failure in this pilot, but it remains unwanted visibility independently of inference performance.

The split-JSON condition changes instruction placement and pretty-printing together; a next matched comparison should separate those effects. The prior-turn condition includes actual prior observations in addition to a valid patch, so a next comparison should separate a compact synthetic exchange demonstrating a state diff from full historical exposure. The tested example was appended inside the JSON instructions string, not a separate message; failure here does not rule out examples in another arrangement.

A reasonable next matrix is plain prose instructions outside the JSON payload in a user-only layout versus a separate system message, each with identical pretty-printed JSON data; then add a compact demonstration exchange to each. Keep the clean observations fixed. Compare final-payload adherence, preservation of fresh findings, useful next requests, and tolerance for prose before the proposal. Production prompt/parser changes remain unimplemented.
