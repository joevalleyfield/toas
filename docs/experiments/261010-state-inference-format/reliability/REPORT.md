# State inference reliability follow-up — 2026-10-10

Prior accepted turns gave the strongest format adherence on this captured state. Separate system instructions and readable JSON improved the original layout, but still slipped into XML or omitted the patch. Format success did not ensure reliable state maintenance.

Task: [261010-state-inference-response-resilience](../../../../tasks/open/261010-state-inference-response-resilience.md).

## Independent follow-up

44 inference-only calls: 18 per promising condition and eight baseline calls. The two discovery samples per condition are excluded from this primary table. All current observations exclude the unwanted control result.

| Condition | Valid explicit diff with current parser | 95% Wilson interval | Terminal JSON after any prefix | XML syntax |
| --- | --- | --- | --- | --- |
| Actual prior accepted exchange | 18/18 | 82.4%–100.0% | 18/18 | 0/18 |
| Separate system instructions + readable JSON | 12/18 | 43.7%–83.7% | 13/18 | 5/18 |
| Original JSON packaging, control result removed | 0/8 | 0.0%–32.4% | 3/8 | 6/8 |

Combined descriptive totals, including discovery: prior turns **20/20**, split JSON **14/20**, original clean packaging **0/10**. Combined Wilson intervals are 83.9–100%, 48.1–85.5%, and 0–27.8%, respectively. Conditions were selected using discovery results; the independent follow-up is the stronger evidence.

Every follow-up call ended with `finish_reason=stop`; no output-budget truncation or transport error was recorded. All returned the same model: `/Users/tim/Applications/text-generation-webui/user_data/models/Qwen3.8-27B-Q8_0.gguf`. The configured model alias remains `qwen3.5-35b-a3b`. SDK arguments were identical across repetitions within each condition. No generated tools were executed or proposals applied to dogfood history.

## What the format counts mean

A strict success requires a proposal the current response parser can decode, an explicit object `state_patch`, an explicit array `tool_calls`, valid outcome/report types, advertised tools, and their required argument shapes. This is stricter than current runtime acceptance: [r10-split_json](r10-split_json.response.txt) omitted `state_patch`, and the runtime currently supplies `{}`. The current parser decoded 13/18 split-JSON responses, but only 12/18 met the intended contract.

The terminal-JSON diagnostic is deliberately broader than prose tolerance. Its extra split-JSON success and two of the baseline successes are JSON preceded by an unclosed `<tool_call>` tag. Those need an explicit envelope decision; they are not evidence that accepting prose alone fixes all three. The remaining baseline recovery, [r9-json_clean](r9-json_clean.response.txt), is prose followed by a complete fenced JSON proposal. No XML call is executed by this experiment or treated as a replacement for a state proposal.

## State and request inspection

All 18 prior-turn strict successes contained a nonempty patch and requested relevant source reads/searches. Only 17 changed the supplied state when merged. Three patches offered limited factual retention: r13 saved a new uncertainty, r14 repeated unchanged notes, and r15 saved a question and next steps. The other 15 retained fresh CLI facts or locations in progress, notes, or artifacts; that count does not assert every retained detail was accurate.

All 12 split-JSON strict successes changed state and retained fresh CLI findings or locations. Several still had semantic defects. Notable examples:

- [r8-json_prior_turn](r8-json_prior_turn.response.txt): Fresh implementation insights and relevant requests; artifact associates CLI lines 196-266 with ib_876d18a0ab1bc9e3, the older AGENTS.md block.
- [r14-json_prior_turn](r14-json_prior_turn.response.txt): Relevant CLI read, but patch repeats identical notes. Applying it leaves state unchanged and retains no fresh finding.
- [r5-split_json](r5-split_json.response.txt): Valid envelope and fresh CLI artifacts; second grep argv has no file operand, so it cannot search the intended source.
- [r9-split_json](r9-split_json.response.txt): Fresh CLI findings and a useful read; also invents .toas/scratch/ib_8f2a1c.txt without an observed source.
- [r12-split_json](r12-split_json.response.txt): Fresh locations retained, but attributes kwargs assignment at line 255 to _run_step, although the observation places it under run_step.

These inspections distinguish format adherence, actual state change, and factual/useful state maintenance. They do not establish successful tool execution or completion of the underlying preview-pretty task. Shell policy eligibility was not tested by executing proposed calls. See [inspection notes](inspection-notes.json).

## Interpretation and next work

Providing a real accepted state-diff exchange is worth pursuing. The evidence does not establish whether its advantage comes from the assistant-turn format demonstration, added historical facts, longer context, or their combination. Split JSON changes instruction role and pretty-printing together. The failed pilot example was appended inside a JSON instruction string; these results do not rule out a better placed example.

Next isolate a compact user/assistant state-diff demonstration from the full old exchange, then evaluate multiple held-out states and a short sequence of state updates. Measure retention of fresh observations and false artifact references alongside envelope compliance. Preserve a clear requirement for an explicit patch, support deliberately delimited prose before it, and provide bounded format-rejection feedback. No prompt-only condition here removes the need for runtime resilience.

## Scope and uncertainty

These are repetitions of one fixed state/context on one local model, with a 1,800-token response budget and thinking disabled. Sampling values and server template behavior were not controlled beyond the captured SDK settings. Wilson intervals assume independent trials with a constant probability; they describe uncertainty for this repeated-input experiment, not cross-task reliability. Even 20/20 gives only an 83.9% lower bound under that assumption. No repair retries or tool/state episodes were measured.

## Reproduction and evidence

See the [runner and condition definitions](../README.md), [manifest](manifest.json), [raw evaluation results](results.json), and [aggregate counts/intervals](summary.json). Each trial has complete SDK input and response files. Offline evaluator checks passed; all 44 saved responses were re-evaluated and matched their original scores. No production parser, prompt, recovery, or execution behavior changed.
