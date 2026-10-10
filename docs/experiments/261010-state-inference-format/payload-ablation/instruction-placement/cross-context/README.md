# Cross-context and field-placement screen

This follow-up uses captured `state_transition.model_call.request_messages` from
the dogfood event log. Each baseline is the recorded one-user-message packet;
the `instructions_last` arm changes only top-level JSON member order. The packets
were parsed and re-serialized byte-for-byte identically for the baseline, and
the reordered decoded objects compare equal to their baselines. Each condition
ran three interleaved inference-only calls with the same configured local model,
generation settings, and 1,800-token budget. Proposed tools were not executed.

| Captured context | Original order | Instructions last |
| --- | ---: | ---: |
| `st_b0c9fc434f7748ddae666d60b8e709e3` — preview-task initialization, large observation | 3/3 | 3/3 |
| `st_9e620f98ede546d384a13cb08333aa80` — open-tasks initialization, small packet | 3/3 | 3/3 |
| `st_e0f9806dfae9441ba3c6434ec399eeae` — state-seed slash-command task, large observation | 3/3 | 3/3 |

Here a success is an unambiguous, strict-schema proposal using only advertised
tools, not merely syntactically valid JSON. Instructions-last did not improve
the score across these packets because the original order also scored 9/9.
This does not reproduce the earlier 7/7 versus 0/7 contrast on the original
failing packet, and shows that format success depends on context or call
conditions beyond member order.

## Field placement

Using the state-seed packet, a second screen moved one JSON member group at a
time while preserving all decoded values and leaving the instruction text first:

| Condition | Change | Strict proposals |
| --- | --- | ---: |
| `json_clean` | Recorded order | 3/3 |
| `goal_last` | Move `state.goal` to the end of the state object | 3/3 |
| `plan_last` | Move `state.progress` and `state.next_steps` to the end of the state object | 3/3 |
| `schema_last` | Move the output schema member to the end of the packet | 3/3 |

All twelve responses were valid under the packet's advertised schema and tool
definitions. The position screen found no difference in this binary measure;
it does not rule out effects on proposal usefulness or state maintenance.

## Role-separated comparison

On the same state-seed packet, compared the original one-user-message packet,
instructions-last, and the exact instruction string in a system message with
the other packet fields as user JSON. Three interleaved trials per layout gave
3/3 strict proposals in every arm. This small screen does not reproduce the
earlier split-JSON advantage on the original failing context, but it confirms
that role separation can also produce valid proposals on this held-out packet.

## Scoring correction

Final review found that the initial experimental evaluator hard-coded a
four-tool allowlist. The three new captured contexts advertise different tool
sets, including `search` and `get_structure`, so the original provisional scores
misclassified valid proposals. The runner now extracts `tools.available` from
each captured SDK request and validates against that packet's advertised tools
and the local registry. All results in this directory were rescored with this
logic and carry `scorer_version: captured-tools-advertisement-v2`. The earlier
experiments used captured packets advertising exactly the four hard-coded tools,
so their counts are unaffected.

Strict proposal validity does not measure task correctness, patch quality, or
whether a suggested command is well formed for the shell; inspect those
separately. Full trial requests and responses are stored beside each result.
`*.source.json` records the captured transition and packet fingerprint. The shared runner's
`--source-transition` argument preserves that provenance in each run manifest.
No packet, proposal, or tool result was written into dogfood history.
