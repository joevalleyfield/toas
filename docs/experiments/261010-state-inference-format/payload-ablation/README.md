# Payload content and representation ablation

The operator wants to identify the drift trigger before adopting prior turns or
heavier instructions. These comparisons keep the original instructions, response
schema, tool definitions, one-user-message layout, model settings, and output
budget fixed. They add no examples or prior exchanges. The unwanted control result
is excluded throughout. Three interleaved trials per condition are exploratory
evidence, not a reliability benchmark.

| Condition | Change from clean baseline |
| --- | --- |
| `json_clean` | None; fresh matched baseline |
| `pretty_packet` | Pretty-print the entire JSON packet, leaving string contents unchanged |
| `unfenced_outputs` | Remove only the triple-backtick tokens from tool output strings; retain their metadata and source text |
| `structured_stdout` | Expand output status and stream metadata into objects; retain identical stdout text |
| `structured_matches` | Same output objects, with numbered grep text expanded into line-number/text records |
| `state_plaintext` | Remove only inline backticks inside state strings |
| `state_empty_plan` | Empty `state.next_steps`; all other state fields and observations retained |
| `no_tool_observations` | Empty tool outcomes; state and user input retained |

The first five compare representations of the same supplied information.
`state_plaintext` removes inline formatting, without removing the enclosed words.
The last two remove information to help locate a content trigger; their success
would not establish a production-ready representation.

Inspection of the four recorded failed packets found no leaf strings that decode
to JSON objects or arrays. The latest two contain Markdown-fenced grep outputs
under `observation`; their `state` is already structured. The first two failures
had no tool outcomes at all. Thus fences are not a necessary condition for the
historical failure, although they could influence later inference.

The JSON string containing a message in an SDK request is another serialization
layer. A decoded Chat Completions message is text; its enclosing HTTP JSON escaping
is removed by the server when parsing the request. Escaped newlines and quotes
*within the packet's text fields* remain in the serialized packet given to the
model. No genuinely nested JSON object strings were found to expand in this input;
the structural conditions instead expand the projected output representation.
This description concerns SDK serialization, not a captured server-rendered prompt.

`make_variants.py` builds the conditions and asserts exact reconstruction of both
original outputs from the structured forms. It preserves stream kind, source,
inert potency, outcome, and source-line whitespace. It introduces no guessed file
path or facts. The shared runner captures SDK inputs and complete responses and
never executes generated calls or writes proposals into dogfood history.

`inputs/NAME.json` contains the exact message text for each condition, without an
additional SDK/HTTP JSON wrapper. Use these files to distinguish actual packet
escaping from escaping introduced when displaying a JSON-string message in a
larger JSON request.

From this workspace, build with:

```sh
python docs/experiments/261010-state-inference-format/payload-ablation/make_variants.py
```

From the dogfood workspace, run against its configured loopback endpoint:

```sh
uv run --no-sync python /absolute/path/to/toas/docs/experiments/261010-state-inference-format/run.py --rounds 3 --variant-file /absolute/path/to/toas/docs/experiments/261010-state-inference-format/payload-ablation/variants.json --output-dir /absolute/path/to/toas/docs/experiments/261010-state-inference-format/payload-ablation
```

Inspect strict format adherence separately from recoverable terminal JSON, XML
syntax, actual state changes, and useful fresh-finding retention. Do not treat a
three-trial difference as proof of a causal trigger. If a representation is
promising, confirm it on additional states without adding a prior-turn example.
