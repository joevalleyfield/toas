# State goal and instruction placement

Follow the payload-representation screen with three interleaved trials each of
four conditions. Retain the original instruction words, response schema, tools,
single user message, control-free observations, model settings, and output budget.
No examples or prior turns are supplied.

| Condition | Single change |
| --- | --- |
| `json_clean` | Fresh compact JSON baseline |
| `state_empty_goal` | Set `state.goal` to the empty string; the original plan and observations remain |
| `instructions_last` | Move the existing `instructions` member to the end of the JSON object; the decoded packet is exactly identical |
| `instructions_plaintext` | Place the exact instruction text before the compact data JSON in the same user message, instead of encoding it as a JSON string |

The empty-goal condition removes information and is a localization probe, not a
proposed product behavior. The last two probe whether instruction recency and
quotation/escaping matter without introducing stronger wording or message roles.
The plain-text condition retains the same semantic fields outside `instructions`.

`inputs/NAME.txt` is the exact message text; `variants.json` is the explicit
condition file consumed by the shared runner. The file construction asserted
decoded equality for `instructions_last`, unchanged observation for the goal
ablation, and exact instruction-text retention for the plain-text condition.
SDK inputs and raw responses are saved per trial. No generated tools are executed
and no proposals enter dogfood history. Three trials only screen hypotheses;
measure any promising condition more broadly before adopting a production change.

Run from dogfood with the shared runner, `--rounds 3`, and this directory's
`variants.json` and `--output-dir`. See the [payload screen](../README.md).
