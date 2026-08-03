Filed as: 260803-seed-prompt-composition-study
FKA:
AKA: assembled prompt decomposition; seed prompt recomposition; prompt manifest shape
Legacy index:

keywords: projection, decomp, inception, contract, prompts, entrainment, composition, defaults

Parent: `260803-seed-prompt-operator-stance`
Related: `315`; `347`; `355`; `471`; `474`; `475`; `260803-first-failure-plan-recovery`; `260803-language-exec-fenced-block-lane`; `260803-tool-intent-ingress-separation`

# Seed Prompt Recomposition Shape

Translate an operator-proven assembled prompt into the prompt-library shape
TOAS already uses, identifying the existing source for each concern, the gaps
that need new assets, and the smallest composition changes required to render
the intended default seed.

This is primarily a repo-evidence and target-shape task. Behavioral comparison
is a final validation step, not the organizing work.

## Reference Behavior To Preserve

The assembled baseline reportedly does two things together:

1. It removes the bias toward always producing a tool call, allowing the model
   to act as a useful thinking partner.
2. It still keeps the model in the TOAS-local action lane and lets it switch
   naturally back into execution when action is warranted.

Protocol correctness alone is not enough, but the first deliverable is a
checked repo map and recomposition manifest, not an ablation matrix.

## Current Repo Shape

### Default seed manifest

`src/toas/prompts/session-start/templates/pragmatic-default_v1.txt` is already a
first-class composed template. It uses `mode: mimic`, then composes these refs
in order:

1. `role/pragmatic-engineer_v1`
2. `session/blank-page_v1`
3. `protocol/action-lane_v1`
4. `protocol/procedure-bootstrap_v1`
5. `protocol/repo-local-first_v1`

It appends three constraints:

- `no-chatty`
- `no-provider-tools`
- `tools-guidance-repo-work`

The new assembled baseline therefore does not require inventing composition
from scratch. It is mostly a richer replacement or extension of existing
layers.

### Composer behavior

`src/toas/prompts.py` supplies the current composition semantics:

- template manifests are deterministic ordered `refs` plus `constraints`;
- composable ref categories are currently `role`, `session`, and `protocol`;
- `mode: mimic` injects `shared/social_contract_mimic` once, then a matching
  `mimic/<category>/<name>` layer before each direct/base layer when available;
- protocol refs may automatically acquire a matching
  `shared/schemas/<name>` layer;
- constraints are appended after all refs;
- dynamic capability refs exist, but `compose_template` does not currently
  accept them as ordinary manifest refs;
- the `tools-guidance-*` constraints work around that boundary by combining a
  file-backed prefix with `render_tools_guidance_compact()`.

This is enough to express most of the desired seed. The primary shape question
is whether the live capability layer should remain a special constraint or
become a normal typed manifest entry.

### Live tool guidance

`src/toas/tools_guidance.py` renders tool names and argument lists from the live
registry and supplies aliases and shell limits. The pragmatic default already
receives this renderer through `tools-guidance-repo-work`.

Two repo-evidenced gaps matter:

- `render_tools_guidance_compact()` is registry-wide and does not currently
  accept the capability profile or hidden-tool set used by dynamic capability
  prompts;
- it teaches aliases collectively but does not provide the assembled prompt's
  single, prominent schema block or per-tool use-oriented examples.

The target seed should reuse this live source rather than check in the copied
tool list, while closing profile/visibility drift if it is real on the
bootstrap path.

### Existing fragments relevant to the baseline

- `session-start/role-framing/pragmatic-engineer_v1.txt` already owns the terse
  senior-engineer stance.
- `shared/social_contract_mimic.txt` owns actionable next steps, transparent
  assumptions, and minimal ceremony.
- `session-start/protocol-entrainment/action-lane_v1.txt`,
  `mimic/protocol/action-lane_v1.txt`, and
  `shared/schemas/action-lane_v1.txt` own local-lane terminology, callable
  shape, optional intent, and compatibility aliases.
- `session-start/backend-deconfliction/no-provider-tools_v1.txt` and the shared
  `no-provider-tools` constraint own provider-lane resistance.
- `session-start/protocol-entrainment/repo-local-first_v1.txt` owns three
  local-first examples, but all three responses are actions; it supplies no
  synthesis example and therefore reinforces the bias the supplied baseline
  successfully removes.
- `shared/constraints/tools-guidance-repo-work.txt` owns the current
  discover-then-edit cadence, but only as a compact instruction.
- `shared/constraints/tools-guidance-first-edit-pass.txt` already teaches short,
  causally ordered discover -> edit -> test plans.
- `shared/constraints/tools-guidance-full.txt` already owns indent-safe
  `replace_block` guidance, including explicit indent parameters and YAML
  literal indent indicators, but the pragmatic default does not select it.
- no current prompt asset owns Gather/Synthesize/Execute as a working stance,
  a synthesis/trade-off few-shot, or an intention tail.

## Baseline-To-Repo Disposition

| Baseline section | Repo evidence | Target disposition |
| --- | --- | --- |
| Pragmatic role and stance | pragmatic role + mimic social contract | Revise the role leaf only for missing “thinking partner” and mode-choice language; keep shared cadence deduplicated. |
| Tool-ingress profile | action-lane refs/schema + no-provider-tools | Reuse for blocked-channel text profiles; omit or replace for reliable native-tool and no-tool profiles. Remove wording that implies a YAML action is required every turn. |
| Complete tool definitions | tools registry renderer via repo-work constraint | Render dynamically; do not preserve the static copied inventory. Thread profile/hidden-tool inputs if the bootstrap output can drift. |
| Callable schema and aliases | `shared/schemas/action-lane_v1.txt` | Reuse and settle one taught canonical spelling. Current repo examples overwhelmingly use `arguments`; retain aliases as compatibility only. |
| Gather/Synthesize/Execute | no direct owner; partial discover/edit cadence | Add one new working-stance protocol leaf. Define these as available modes, not mandatory headings or a forced linear cycle. |
| Multi-tool batching | first-edit/full guidance + runtime list support | Consolidate into the working-stance or action-lane layer: single call by default, short causally ordered list when useful, per-item intent when it adds recovery value. |
| Indent-safe replacement | full tool-guidance constraint | Keep as selectable edit guidance or capability detail; do not make the entire default seed pay for tool-specific mechanics unless dogfood shows it is essential. |
| Gather example | repo-local-first has action-only examples | Replace or revise the few-shot pack with a bounded multi-read/search example. |
| Synthesis example | absent | Add as the explicit counterexample proving that a good TOAS response may contain no callable action. |
| Execute/edit/test example | partial in first-edit guidance | Add or revise one example, aligned with first-failure semantics and canonical arguments. |
| Intention tail | absent from prompts/runtime projection | Keep outside the default recomposition initially. Treat as a separate continuity/output-shape question because “every turn” changes all response contracts. |

## Concrete Target Composition

The first implementation candidate should fit the current manifest model before
expanding composition machinery:

```yaml
template:
  mode: mimic
  refs:
    - role/pragmatic-engineer_v2
    - session/blank-page_v1
    - protocol/conversation-synthesis-execution_v1
    - protocol/action-lane_v1
    - protocol/procedure-bootstrap_v1
    - protocol/repo-local-first_v2
  constraints:
    - no-chatty
    - no-provider-tools  # selected only for text-lane/blocked-native profiles
    - tools-guidance-repo-work
```

### New or revised leaf responsibilities

`role/pragmatic-engineer_v2`:

- preserve rigor, directness, trade-offs, and execution orientation;
- explicitly act as a thinking partner when the turn calls for analysis;
- do not own callable syntax, live capabilities, or phase mechanics.

`protocol/conversation-synthesis-execution_v1`:

- define conversation, synthesis, and execution as three legitimate response
  modes;
- teach selection based on the state of the work rather than requiring phase
  labels in every response;
- allow a concise technical synthesis with no tool call;
- teach short multi-operation plans when operations are causally coherent;
- keep prose outside YAML when a response mixes explanation and actions;
- point execution policy and exact capability truth to the live tool layer.

`protocol/repo-local-first_v2`:

- retain one bounded Gather example;
- add one no-tool Synthesize/trade-off example;
- add one approved Execute/edit/test example;
- use `arguments` consistently and include per-operation `intent` where the
  example is a multi-operation plan;
- omit the universal intention tail from these examples.

`tools-guidance-repo-work`:

- continue to provide registry-derived tool names, required/optional arguments,
  aliases, and effective limits;
- become profile/hidden-tool correct if repo tracing confirms bootstrap can
  receive a restricted capability set;
- avoid duplicating the working-stance prose and few-shots.

The stable role/stance manifest should be separable from a lane-specific tail:

- native-tool profile: provider-native schema advertisement, without
  `no-provider-tools` or forced text-call few-shots;
- text-lane profile: selected TOAS callable protocol plus
  `no-provider-tools` where the backend channel collides;
- no-tool profile: conversation/synthesis stance with no callable protocol.

If the current static template manifest cannot select that tail from effective
backend/ingress policy, record it as one narrow composer/profile gap rather than
duplicating the complete seed.

### Material deliberately not in the first default

- the verbatim static tool inventory;
- mandatory `[Gather]`, `[Synthesize]`, or `[Execute]` output headings;
- full indent-safe edit instructions on every new session;
- an intention tail after every turn;
- broad prompt-profile or composer redesign before the manifest above proves
  insufficient.

## Remaining Repo Checks Before Implementation

- Trace `session.bootstrap_prompt_ref` through bootstrap rendering to confirm
  whether capability profile and hidden tools reach the pragmatic template's
  tools-guidance constraint.
- Confirm the extractor/projection contract for prose plus a fenced YAML list,
  including whether an intention-like markdown tail can become executable or
  interfere with frontier selection.
- Confirm the canonical callable spelling in current docs/tests and record why
  `arguments` or `params` wins as the taught form.
- Check whether `protocol/repo-local-first_v1` is referenced outside the
  pragmatic default and whether a v2 can land without compatibility changes.
- Compare the assembled tool list with the live registry to identify concrete
  omissions or stale signatures rather than assuming drift abstractly.
- Link first-failure recovery expectations into the Execute example so the
  seed does not promise safe edit/test batching before runtime behavior exists.

## Small Validation Pass

After repo tracing and recomposition, validate only the decisions that remain
behavior-sensitive:

- one technical conversation with no useful tool action;
- one design synthesis/trade-off turn;
- one bounded Gather plan;
- one approved Execute/edit/test plan;
- one strict YAML-only request;
- one provider-native-tool temptation case.

Compare the current pragmatic default, the supplied assembled baseline, and
the concrete recomposition above. Record mode choice, TOAS-lane adherence,
callable correctness, and obvious verbosity regressions. Broader ablation work
should be opened only if these results fail to identify a usable manifest.

## Exit Criteria

- [ ] Bootstrap rendering and capability-profile flow are traced to named repo
  seams with any live-guidance mismatch recorded.
- [ ] Every baseline section has a reuse/revise/add/defer disposition grounded
  in an existing asset or an explicit repo gap.
- [ ] The concrete target manifest is confirmed expressible by the current
  composer, or one narrowly described composer gap is identified.
- [ ] Responsibilities and non-responsibilities are fixed for each new/revised
  leaf so implementation does not recreate a monolithic prompt.
- [ ] Static tool definitions are replaced by effective registry-derived
  guidance.
- [ ] `arguments` versus `params`, prose-plus-YAML behavior, and first-failure
  example semantics are settled from repo contracts.
- [ ] The intention tail has an explicit deferred or separate-task disposition.
- [ ] The small validation pass shows the recomposed manifest retains both
  thinking-partner behavior and TOAS-local execution discipline.
- [ ] The parent task is updated with the final manifest and any bounded
  implementation follow-ons.

## Non-Goals

- Rewriting runtime execution policy through prompt text.
- Freezing the supplied copied tool inventory as permanent source truth.
- Implementing first-failure recovery inside this prompt study.
- Building a general prompt experimentation harness.
- Performing broad ablation or model benchmarking without a repo-shape blocker.
- Assuming one model's preferred wording must be universal.

## Allowed Write Surfaces

- this task file and its parent task for repo tracing, dispositions, and final
  manifest shape
- mechanically generated `tasks/WORKBOARD.md` sections

## Required Completion Evidence

- bootstrap-to-composer trace with file/function references;
- current manifest and rendered-layer inventory;
- baseline-to-repo disposition table;
- final proposed manifest with leaf responsibilities;
- small validation outputs for the six named scenarios;
- bounded follow-on task links where implementation seams differ.

## Operator Reference Prompt: 2026-08-03

The following prompt is preserved verbatim from the operator-provided artifact
as the known-good qualitative baseline.

````md
## TOAS:USER

## TOAS ROLE & WORKING STANCE

You are collaborating as a Pragmatic Senior Engineer in a direct, turn-by-turn workspace loop with the user (who executes local tools).
- Stance: Technically rigorous, direct, and execution-oriented. Prefer concrete trade-offs over generic reassurance.
- Cadence: Optimize for actionable next steps, transparent assumptions, and minimal ceremony.
- Tool Usage: Issue TOAS-local YAML action blocks exclusively. Do not emit provider-native tool calls.

---

## TOAS TOOL DEFINITIONS

When invoking workspace actions, use only the following tool signatures:

```yaml
tools:
- apply_patch (args: patch)
- capability_help (args: none, optional: topic)
- capture_task_thread (args: title, kind, optional: evidence, blocks_progress, active_task_id, scope_hint, capture_id)
- code_survey (args: none, optional: path, top_n)
- echo (args: text)
- echo_block (args: block)
- get_structure (args: path)
- procedure (args: name, optional: arguments, dry_run)
- read_file (args: path, optional: start_line, end_line, number_lines)
- replace_block (args: path, search_block, replacement_block)
- replace_range (args: path, start_line, end_line, replacement_block)
- search (args: query, optional: path, limit, regex)
- shell (args: argv, optional: cwd, timeout_s, env)
- shell_script (args: script, optional: cwd, timeout_s, env)
- write_file (args: path, content)
```

Schema Format:
```yaml
operation: <operation_name>
params:
  key: value
intent: <why_this_action_is_being_taken>
```

Acceptable Aliases: `tool_name` for `operation`, `args`/`arguments` for `params`, `intention` for `intent`.

---

## TOAS OPERATIONAL PHASES & TOOL PROTOCOL

Operate explicitly across three tactical phases:
1. [Gather]: Issue bounded tool operations (`rg`, `read_file`, `search`) to collect context. Keep wrappers minimal.
2. [Synthesize]: Analyze collected artifacts, outline technical trade-offs, and recommend design choices. Concise technical commentary is required before proposing actions.
3. [Execute]: Issue deterministic YAML operations to enact agreed-upon changes.

### Multi-Tool Batching Protocol
When executing sequential actions in a single turn, emit a top-level YAML list (2–4 operations max). Operations execute top-to-bottom. Each item must include its own `intent`.

```yaml
- operation: read_file
  params:
    path: src/toas/config.py
  intent: Inspect current configuration parsing rules
- operation: read_file
  params:
    path: src/toas/runner.py
    start_line: 40
    end_line: 75
  intent: Check execution hook implementation
```

### Indented Code Modification Protocol (CRITICAL)

When editing indented code blocks (e.g., Python class methods) using `replace_block`, YAML multiline parsing (`|`) automatically strips all common leading whitespace by default, causing string match failures (`tool replace_block found no matches`).

To preserve leading whitespace, use one of these two mechanisms:

* **Option A (Explicit Parameter - RECOMMENDED):** Pass `search_indent: <num_spaces>` in the parameters block. The tool will automatically prepend `<num_spaces>` to every line of `search_block` and `replacement_block`.
* **Option B (YAML Indentation Header):** Set the block scalar indicator to match the parent key's indentation level (e.g., `|2` when `search_block:` is indented by 2 spaces). Indent the code content by `(parent_indent + desired_indent)` spaces so YAML strips only the parent indentation.

--

## TOAS FEW-SHOT EXAMPLES

### Example 1: Bounded Multi-Tool Discovery [Gather]
User: Check how configuration and command args are handled in the runner.

Assistant:
```yaml
- operation: search
  params:
    query: "def parse_args"
    path: src/
  intent: Locate argument parsing definitions
- operation: read_file
  params:
    path: src/toas/cli.py
    start_line: 1
    end_line: 35
  intent: Inspect entrypoint CLI argument handling
```

- Implement CLI runner update
  - Gather CLI argument parsing implementation
    - Locate parse_args definition
    - Read initial CLI configuration setup

---

### Example 2: Synthesis & Trade-Off Alignment [Synthesize]
User: Should we update the parser to use pydantic or stay with argparse?

Assistant:
### Technical Analysis & Trade-Offs

1. **Option A: Pydantic Settings**
   - **Pros:** Strong validation, automatic environment variable mapping, cleaner nested configs.
   - **Cons:** Adds a heavy third-party dependency to a lightweight runner script.

2. **Option B: Standard `argparse` + Dataclass (Recommended)**
   - **Pros:** Zero new dependencies, native TOAS execution alignment, straightforward schema serialization.
   - **Cons:** Manual coercion for complex nested structures.

**Recommendation:** Proceed with **Option B** to keep TOAS dependencies minimal and execution fast.

Shall we refactor `src/toas/config.py` using `dataclasses`?

- Refactor configuration parser
  - Select parser architecture
    - Evaluate argparse + dataclasses vs Pydantic
    - Await user approval on zero-dependency approach

---

### Example 3: Multi-Tool Batch Execution & Test [Execute]
User: Proceed with Option B and run the tests.

Assistant:
```yaml
- operation: replace_block
  params:
    path: src/toas/config.py
    search_block: |
      def load_config():
          return {}
    replacement_block: |
      from dataclasses import dataclass

      @dataclass
      class Config:
          verbose: bool = False
  intent: Refactor config loader to use dataclass
- operation: shell
  params:
    argv: ["pytest", "tests/test_config.py"]
  intent: Verify config refactor against test suite
```

- Refactor configuration parser
  - Apply dataclass refactor to src/toas/config.py
    - Update load_config implementation
    - Run pytest suite for verification

---

## TOAS INTENTION TAIL

At the end of every turn, append a compact Intention Tail showing active purpose hierarchy:

```md
- <root intention>
  - <active intention>
    - <supporting prerequisite, constraint, or sub-intention>
```
````
