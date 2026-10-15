# Payload drift investigation — 2026-10-10

The strongest smaller intervention was moving the **unchanged `instructions` field to the end of the JSON packet**. It produced valid state diffs in 3/3 discovery calls and 4/4 independent confirmation calls; the matched original ordering produced 0/3 and 0/4. No examples, prior turns, system messages, stronger wording, output expansion, or state changes were added.

This points toward instruction placement/recency as a useful hypothesis. It does **not** identify a particular state string as the cause or establish the model’s attention mechanism. Markdown output and escaped string contents were retained in the successful reordered requests.

Task: [state inference response resilience](../../../../tasks/open/261010-state-inference-response-resilience.md).

## What was actually embedded

The four failed recorded packets contain no leaf strings that decode into JSON objects or arrays. The current state is already an object. The latest two packets include Markdown-fenced grep outputs under `observation`; the first two failures have no tool outcomes. Thus fences are not necessary for the historical XML failure.

The SDK/HTTP JSON wrapper adds another serialization layer around the message text. That outer escaping is decoded when the server parses its request. Within the actual JSON packet text, instructions and projected outputs are strings with escaped newlines/quotes. The structural conditions expand the projected output into data fields; there was no nested JSON object string to recursively decode. Server-rendered prompts were not captured. See [inventory](inventory.json), [exact message inputs](inputs/json_clean.json), and [structured matches input](inputs/structured_matches.json).

## Representation screen

Three interleaved calls per condition; instruction words, message roles, schema, tools, and settings held fixed. The first five preserve supplied information; backtick removal changes only formatting. Empty-plan/no-output conditions remove information.

| Condition | Strict valid diff | Recoverable terminal proposal | XML text |
| --- | --- | --- | --- |
| Clean compact JSON baseline | 0/3 | 1/3 | 2/3 |
| Pretty-print entire packet | 1/3 | 1/3 | 2/3 |
| Remove output fence tokens | 0/3 | 0/3 | 3/3 |
| Output status/stream objects + original text | 1/3 | 2/3 | 1/3 |
| Structured numbered source matches | 0/3 | 0/3 | 3/3 |
| Remove state inline backticks | 0/3 | 1/3 | 2/3 |
| Empty state next_steps | 1/3 | 1/3 | 2/3 |
| Remove tool outcomes | 2/3 | 2/3 | 1/3 |

Both structured output forms reconstruct the original outputs exactly, including outcome, source, inert potency, stream identity, and source-line whitespace. No path or fact was inferred. Fence removal and structural expansion did not consistently cure the drift. Small samples do not prove they have no effect.

The no-output condition’s first format success was a no-op (`state_patch: {}`, no calls); the other requested a relevant source read, but claimed exploration had started without a new tool observation. The empty-plan condition’s one strict success transcribed raw output into notes and requested `toas/cli.py` instead of `src/toas/cli.py`. Those are not clean task successes.

## Goal and instruction placement screen

| Condition | Strict valid diff | Recoverable terminal proposal | XML text |
| --- | --- | --- | --- |
| Same compact baseline | 0/3 | 0/3 | 3/3 |
| Empty goal; retain original plan | 0/3 | 1/3 | 1/3 |
| Move existing instructions member last | 3/3 | 3/3 | 0/3 |
| Exact instructions before compact data JSON, same user message | 1/3 | 2/3 | 1/3 |

Emptying the goal changed the failure pattern: two responses avoided XML. One attempted a prose-prefixed JSON patch but used a Python-style single-quoted value; another emitted a complete JSON patch with `report: null`. The latter is rejected by this strict advertised-schema score but accepted by current runtime envelope checks. The third included a valid terminal proposal after an unclosed XML opener. Thus the goal remains a possible contributor, despite no strict-schema successes. Removing only its inline formatting did not reliably solve the problem.

## Independent instruction-order confirmation

Four further calls per condition, after both screens completed:

| Condition | Strict valid diff | Recoverable terminal proposal | XML text |
| --- | --- | --- | --- |
| Original ordering | 0/4 | 2/4 | 3/4 |
| Instructions last | 4/4 | 4/4 | 0/4 |

Combined placement results are **7/7 versus 0/7**. Under independent constant-probability trials, the 95% Wilson interval for 7/7 is **64.6–100%**; independent confirmation alone (4/4) is **51.0–100%**. These repetitions of one state/context are not cross-task reliability. The original-order recoveries include one ordinary prose-prefixed JSON proposal and one preceded by an unclosed `<tool_call>` tag. XML execution was never attempted.

The sole input difference in this comparison is member order:

```text
Original: instructions, schema, tools, state, observation
Reordered: schema, tools, state, observation, instructions
```

Decoded packets are exactly equal, and message character lengths are equal (8,108). Existing Markdown and escaping remain. Every reordered success has a nonempty patch that changes the supplied state, retains fresh CLI findings or locations, and requests relevant source inspection. One discovery response synthesized code outlines into notes from grep excerpts, so the result does not guarantee factual accuracy or adherence to the reference-preservation instruction. Generated tools were not executed.

The original packet places task-like goal/plan text and tool output after the response instructions. Moving those exact instructions to the end may reinforce the state-update contract after that material. That is an inference from the controlled comparison, not direct evidence of an internal model mechanism or proof that the goal alone caused the drift.

## Evidence quality and limits

All 44 calls returned the same local model, `/Users/tim/Applications/text-generation-webui/user_data/models/Qwen3.8-27B-Q8_0.gguf`, and ended with `finish_reason=stop`. No truncation or network error was recorded. SDK inputs are identical within each condition; each uses one user message, thinking disabled, a 1,800-token output budget, no examples/prior exchanges, and no repair retries. No generated tools or state patches were applied to dogfood history. Server sampler/template behavior remains partly uncontrolled. The placement screen began while the final two representation calls were finishing; the independent confirmation ran after both screens completed.

Strict scoring requires explicit state_patch/tool_calls and the advertised field/tool argument shapes, beyond merely decoding JSON. It is stricter than current runtime acceptance of missing patch fields or report:null. Terminal extraction is a diagnostic and accepts some JSON preceded by an XML opener; it is not a production parser decision. A diagnostic scan bug counted a single JSON object twice after a blank line. It was fixed and one plain-instructions recovery rescored; strict rates, prior reliability results, and the first representation screen were unaffected. See [evaluation correction](instruction-placement/evaluation-correction.json).

## Next investigation

The cross-context and field-placement follow-up is complete; see the
[captured-packet results](instruction-placement/cross-context/README.md).
Both original ordering and instructions-last scored 9/9 across the three held-out
packets. On the larger state-seed packet, moving the goal, plan, or schema each
scored 3/3, and role-separated instructions/data scored 3/3. These conditions
did not distinguish themselves on strict proposal validity, although the strong
single-context instruction-order contrast remains evidence for testing a
configurable choice rather than a universal default.

Next compare task and state-maintenance quality across additional captured
contexts, not just response shape. Keep role layout and instructions-last as
configurable experimental choices while evidence remains context-specific. Only
test structural expansion for JSON-encoded strings if a captured packet
actually contains them. No production behavior was changed.

See [condition definitions](README.md), [placement runbook](instruction-placement/README.md), [aggregate metrics](summary.json), [screen results](results.json), [placement results](instruction-placement/results.json), and [confirmation results](instruction-placement/confirmation/results.json). Every trial has an SDK request and raw response. Offline checks and re-evaluation of all 44 responses passed.
