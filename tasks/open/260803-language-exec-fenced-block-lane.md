Filed as: 260803-language-exec-fenced-block-lane
FKA:
AKA: language plus exec; executable markdown fences; bash exec lane; prompted shell fence; toas-tool exec; structural activation; proxy-resilient callable fences
Legacy index:

keywords: tooling, decomp, inception, contract, markdown, exec, shell, projection

Related: `260412-json-callable-lane-parser-and-policy`; `260803-first-failure-plan-recovery`; `260803-seed-prompt-composition-study`; `260803-tool-intent-ingress-separation`; `299`

Implementation follow-ons: `260829-markdown-fence-scanner`; `260829-executable-fence-activation`

# Executable Fence Lanes And Activators

Define executable Markdown fence lanes with `<language> exec` as the clear
canonical surface while preserving structurally activated and configurable
fallback forms that survive proxies which strip, rewrite, or reject conspicuous
execution metadata.

This is a requirements parent. It should settle fence recognition, language
routing, authority, shell command boundaries, result projection, and partial
failure recovery before opening bounded parser/runner/rendering follow-ons.

## Core Surface

An executable block has this info-string shape:

````markdown
```bash exec
$ ls
$ ls tasks/open
$ cat tasks/open/fix-the-thing.md
```
````

The language selects a registered fence-lane handler: an interpreter runner,
a structured callable serializer, or another explicit execution capability.
The literal `exec` token is the clearest overt activator, but it is not the
definition of potency for every lane.

The same shape generalizes without introducing provider-native tool syntax:

````markdown
```python exec
print("hello")
```

```sql exec
select * from tasks;
```

```powershell exec
Get-ChildItem
```

```toas-tool exec
read_file(path="README.md", show_line_numbers=true)
```
````

These examples define syntax, not a promise that every language is available
in the first implementation. Executability depends on an explicit language
registry, capability availability, and effective authority policy.

## Why This Lane Is Compelling

- It preserves ordinary Markdown and adds only one execution token.
- Capable web LLMs can emit and round-trip it without activating or depending
  on provider-native tools.
- The language tag remains useful to renderers, editors, and humans.
- Shell transcripts can remain visually recognizable instead of being wrapped
  in action-object ceremony.
- Prompted shell blocks expose command boundaries that align naturally with
  first-failure recovery.
- The same envelope can carry interpreter source, YAML/JSON structured calls,
  or a compact TOAS call-expression grammar without confusing those body
  semantics.
- Structurally recognized callable bodies can remain usable when a proxy strips
  an unknown info-string token such as `exec`.

## Current Repo Evidence

TOAS already has most of the semantic pieces, but they are attached to narrower
surface grammars:

- `src/toas/graph.py::extract_plan_with_status` recognizes fenced `yaml` blocks
  using a YAML-specific regular expression and normalizes them into tool plans.
- `src/toas/shell_intent.py` recognizes user `$ ` command spans, including
  multiline quotes, continuations, and heredocs, and strips explicitly inert
  regions before intent extraction.
- `src/toas/shell_intent.py::strip_inert_regions` plus the `!inert`,
  `[[inert]]...[[/inert]]`, and fenced `inert` help contract already establish
  that explicit inert classification overrides otherwise executable-looking
  content.
- `src/toas/runtime/intent_arbitration_edges.py` collects YAML-plan and shell
  candidates with source positions and applies deterministic first/last/in-order
  arbitration.
- `src/toas/step.py` and `src/toas/tools_cluster/shell_ops.py` preserve the
  authority distinction between direct user shell intent and the bounded
  assistant-addressable shell capability.
- `src/toas/tools_cluster/rendering.py::render_fenced_output` already emits
  sized, metadata-rich `toas-output` fences with explicit inert potency.
- `src/toas/runtime/rendering_edges.py` already avoids interpreting `$ ` and
  slash-like text inside ordinary fences when checking result projection risk.
- `260803-first-failure-plan-recovery` already owns the general completed /
  standalone retry / remaining forward-plan split for ordered operations.

The missing owner is a reusable Markdown fence scanner plus an executable-fence
normalization/routing seam. The existing YAML lane already proves that body
parsing and plan normalization are separate: YAML deserializes a mapping/list,
then `normalize_tool_plan` owns callable aliases and validation. JSON can be a
close serialization corollary that enters the same normalizer. Extending the
outer-fence regex independently for every body grammar would still multiply
potency, arbitration, and fence-correctness rules.

## Fence Recognition And Potency Contract

Fence scanning identifies boundaries, info-string tokens, body text, nesting,
and source spans. A lane handler then decides whether that fence is active.
Potency must not be hard-wired to one info-string token.

### Activator families

A lane may register one or more exact activation predicates:

1. **Envelope activation:** an overt info-string form such as `bash exec` or
   `toas-tool exec`.
2. **Structural activation:** the parsed body unambiguously satisfies a lane's
   callable schema. Today's fenced YAML lane uses this model: the combination
   of a YAML fence and recognized top-level callable keys makes it active.
3. **Body-marker activation:** an exact reserved top-level key, leading
   directive, comment/sentinel, or grammar production selects the lane even if
   the info string is generic or rewritten.
4. **Configured compatibility activation:** a backend/profile-specific alias or
   marker placement is selected because it survives a known proxy path.

Structured lanes may optionally recognize an unlabeled/generic fence when its
body has an exact, unambiguous callable shape. They must not scan arbitrary
prose for vaguely tool-like mappings.

### Potency precedence

Resolve potency in this order:

1. An explicitly inert enclosing region, quoted example, or `toas-output`
   record with non-active potency wins over every active predicate.
2. Malformed, conflicting, multiply claimed, or unterminated structure fails
   closed.
3. One exact registered activation predicate may claim the fence.
4. Unclaimed fences remain ordinary inert Markdown.

`exec`, structural recognition, or a strange compatibility marker is syntax,
not authority. A claimed fence must still pass origin-role, capability,
workspace, and policy checks.

### Canonical overt grammar

Prefer this deliberately small form when the transport preserves it:

```text
<opening fence><language> exec
<body>
<matching closing fence>
```

Requirements:

- opening fences use at least three backticks and closing fences match the
  opening fence length closely enough to preserve bodies containing backticks;
- leading indentation and CommonMark-compatible fence placement receive one
  explicit supported/unsupported decision;
- language matching is normalized through registered aliases, not by invoking
  the language token as an arbitrary executable name;
- unknown languages produce an inert/unsupported diagnostic, never host command
  lookup;
- quoted examples, `inert` fences, and `toas-output` fences whose potency is not
  active remain non-executable;
- malformed, unterminated, nested, or ambiguous fences fail closed;
- source spans are retained for intent arbitration and direct-manipulation
  projection.

Do not accept arbitrary free-form attributes or fuzzy marker discovery merely
because alternate activators are supported. Every fallback is a named,
testable predicate with deterministic precedence and provenance.

## Proxy-Survivable Activation

The surface must account for intermediaries that may:

- strip unknown info-string tokens but preserve the language;
- reduce an info string to its first token;
- replace an unknown language with a generic code fence;
- normalize whitespace, quoting, or fence length;
- reject conspicuous tool/function terminology;
- elide a fenced section entirely.

No syntax can recover content that a proxy removes wholesale. The design goal
is graceful survival when presentation metadata is stripped while the body is
preserved.

Maintain a transformation/specimen matrix for each activation profile:

- original source;
- transformed source received by TOAS;
- selected lane and activation predicate;
- active/inert/ambiguous outcome;
- recorded diagnostic/provenance.

The canonical prompt may teach `<language> exec` on transparent paths while a
backend-specific prompt composition teaches structural or alternate markers on
paths known to filter overt execution metadata. Runtime recognizers may support
multiple forms simultaneously, but prompt selection should advertise the
smallest form appropriate to the active transport.

Do not describe proxy resilience as permission to bypass TOAS authority. The
activator changes how intent survives transport; it never widens what the
selected lane may execute.

This fence family is one intent-ingress adapter under
`260803-tool-intent-ingress-separation`. It must normalize into the shared tool
intent/runtime path rather than becoming the semantic center merely because it
is the most flexible text surface.

## Fence-Lane Routing Contract

Introduce an explicit registry from normalized language aliases to fence-lane
handlers. Handler kinds include:

- structured callable serializers such as YAML and JSON;
- compact callable grammars such as `toas-tool` call expressions;
- interpreter/script runners such as Bash, Python, or PowerShell;
- future composite lanes that deliberately own nested executable content.

A registry entry should define at least:

- canonical language and accepted aliases;
- handler kind, parser, and runner/capability owner;
- whether the body has multiple surface operations or one atomic operation;
- supported authority contexts (user, assistant, or both);
- effective timeout/cancellation policy source;
- result projection strategy;
- recovery granularity;
- availability diagnostics.
- ordered activation predicates and their provenance labels;
- whether structural activation may apply to labeled fences only or also to
  generic/unlabeled fences;
- the explicit inert forms that override those predicates.

The registry must not duplicate tool policy or turn language strings directly
into subprocess commands. Structured and call-expression handlers normalize
into the same canonical tool plan used by the YAML lane. Interpreter handlers
route into existing or deliberately added execution capabilities.

## Structured Callable Siblings

YAML and JSON should be close siblings, not unrelated execution systems.

The shared pipeline is:

```text
fence scan
  -> lane-specific body deserialization
  -> normalize_tool_plan
  -> origin/authority selection
  -> ordinary tool plan execution
  -> ordinary tool results
```

The YAML lane already supplies the latter four stages. A JSON follow-on should
principally add JSON body recognition/deserialization plus coexistence tests;
it should not create parallel tool validation, policy, or result semantics.

Activation syntax is separable from body grammar. The requirements decision
must settle whether:

- plain fenced `yaml` remains an active compatibility form while new siblings
  require `exec`;
- `yaml exec` and `json exec` become the preferred explicit forms;
- plain `json` is accepted as the exact YAML compatibility corollary;
- configuration gates any compatibility form that lacks the explicit potency
  marker.
- JSON/YAML structural recognition may claim generic or unlabeled fences when
  the top-level callable contract is exact.

Whichever transition is chosen, ordinary illustrative JSON/YAML fences need a
clear inert escape and mixed-fence arbitration must remain deterministic.
Current markerless fenced YAML callability is valuable transport resilience,
not merely accidental legacy behavior.

## Compact TOAS Tool-Call Fence

The shared fence envelope can also carry a compact purpose-built callable
grammar:

````markdown
```toas-tool exec
read_file(path="README.md", show_line_numbers=true)
```
````

This lane is neither JSON nor an interpreter. Its body parser should produce
the same canonical tool-plan input as YAML/JSON.

Requirements:

- parse with a dedicated grammar/AST; never use Python `eval`, shell parsing,
  or dynamic invocation;
- resolve the callable name and argument names against the live TOAS registry;
- define a bounded literal grammar for strings, booleans, null, numbers, lists,
  mappings, and multiline values only as demonstrated needs require;
- decide whether multiple expressions form an ordered plan, and how multiline
  calls are delimited;
- preserve source spans and per-call boundaries for diagnostics and
  first-failure recovery;
- normalize into the same `tool_name` / `args` / optional intention contract
  rather than adding a new execution object model;
- keep user-versus-assistant authority identical to equivalent YAML/JSON calls.

This may be a more natural compact model-facing tool lane than JSON while still
making JSON cheap to add as a serialization sibling.

### First implementation bias

Land the general scanner/router seam first. JSON is then a cheap structured-
handler proof because it can reuse the YAML normalizer; shell-like fences are
the first richer end-to-end execution proof because TOAS already has shell
authority separation, command parsing, and result rendering. `toas-tool` can
follow once the canonical call-expression grammar is settled. Python,
PowerShell, SQL, and other interpreter languages should remain small runner
follow-ons whose capability and context are explicit.

SQL particularly requires a named connection/data-source authority; `sql exec`
must not imply an ambient database.

## Shell-Like Fence Modes

Shell-like languages have two distinct meanings based on the block body.

### Prompted command-sequence form

````markdown
```bash exec
$ ls
$ ls tasks/open
```
````

- Each leading `$ ` prompt introduces one independently visible command.
- Existing shell-span logic should be reused for quotes, continuations, and
  heredocs rather than treating every physical line as a command.
- Commands execute in source order.
- Results project beneath the corresponding prompt in an interactive-transcript
  shape where stream separation and failure state remain unambiguous.
- The mode exposes operation boundaries for staging, first-failure splitting,
  retry, and forward-plan continuation.
- Non-prompt lines must have a defined meaning: continuation/input belonging to
  the current command, prior projected output in a round-tripped transcript, or
  invalid source. They must never silently become commands.

Representative successful projection:

````markdown
```bash exec
$ ls
README.md  tasks
$ ls tasks/open
fix-the-thing.md
```
````

The renderer may need compact annotations for stderr, exit status, or omitted
bulk; the pretty transcript must not erase those facts.

### Promptless script form

````markdown
```bash exec
ls
ls tasks/open
```
````

- The complete body is one script operation.
- Normal shell-script semantics are preserved; TOAS does not split physical
  lines into separate commands.
- Execution yields one terminal status plus combined operation-level stdout and
  stderr projections.
- Recovery granularity is the whole script unless the selected runner provides
  an explicit tracing/sub-operation contract.

Representative projection:

````markdown
```bash exec
ls
ls tasks/open
```

```text
README.md
tasks

fix-the-thing.md
```
````

Prompt presence therefore selects command-boundary and projection semantics,
not merely presentation style.

## Authority And Origin

Executable fences must retain TOAS's existing direct-user-intent versus
model-addressable-capability split:

- A user-authored shell fence follows the direct user-intent lane, with the
  same explicit scope and lifecycle semantics as user shell shorthand.
- An assistant-authored shell fence follows assistant shell capability policy,
  including effective command, workspace, environment, and timeout authority.
- Adoption or restaging changes the active origin explicitly; it must not
  silently launder assistant text into user authority.
- Unsupported authority stages a visible, directly manipulable fence or
  diagnostic rather than rewriting it into a historical replay reference.
- Execution records remain `tool_request` / `tool_result` facts using the
  relevant capability shape; the Markdown fence itself remains transcript
  surface syntax, not a new message-event type.

## Result Projection And Round Trip

- The original executable block remains ordinary transcript content and is
  reconciled like other message text.
- Execution appends consequences; it does not mutate an earlier durable message
  to insert output.
- Fresh projection may render a combined command/result view for ergonomics,
  but durable request/result facts remain separately inspectable.
- Projected output must be inert to intent extraction. Reprojecting or copying
  a completed transcript must not execute embedded results or completed
  commands again without an explicit new active frontier.
- stdout, stderr, exit status, timeout/cancel state, and truncation must remain
  recoverable even when the visible interactive shape is compact.
- Fence sizing must preserve bodies/results containing backticks.
- Markdown rendered by ordinary clients should remain readable even when the
  client ignores the `exec` token.

## First-Failure Recovery

Prompted command sequences are ordered plans for recovery purposes.

Given:

````markdown
```bash exec
$ call-1
$ call-2
$ call-3
```
````

if `call-2` fails:

1. `call-1` remains completed and receives its ordinary result.
2. `call-2` becomes one standalone, editable retry in the same language-plus-
   exec surface.
3. `call-3` remains staged and unexecuted as the forward plan.
4. Already completed commands are not replayed.

This task defines how the Markdown surface represents that split. The shared
runtime stop-on-first-failure behavior remains owned by
`260803-first-failure-plan-recovery`.

A promptless script remains one operation, so failure does not imply safe
line-level recovery.

## Intent Arbitration And Mixed Content

- Executable fences become explicit intent candidates with source spans and
  participate in the existing arbitration policy.
- A frontier containing YAML calls, user `$ ` shorthand, slash commands, and
  executable fences must have deterministic textual ordering and conflict
  behavior.
- `$ ` lines inside a recognized executable fence belong to that fence and must
  not also surface as duplicate free-standing shell candidates.
- YAML, JSON, or call-expression text inside another lane's executable body is
  payload by default, not a second callable lane.
- Ordinary fenced examples must remain inert even when surrounded by active
  prose or other executable candidates.

## Nested Lane Capability

Markdown fence sizing can preserve inner fences inside a larger outer fence.
The scanner should not destroy that structure, but execution is opaque by
default:

- each handler receives its body as payload;
- the general scanner does not recursively execute inner fences;
- an outer lane must explicitly declare composite/nested semantics before inner
  executable fences can become child operations;
- any future composite lane must define recursion depth, authority inheritance,
  operation ordering, first-failure behavior, result placement, and whether
  inner source is still visible/manipulable;
- nested active content fails closed if more than one owner could claim it.

This preserves the devious compositional possibility without inventing a
recursive execution model before a concrete use case exists.

## Relationship To The JSON Callable Lane

`260412-json-callable-lane-parser-and-policy` is the JSON serialization sibling
to the YAML lane and a natural consumer of the general fence scanner. Its
distinct work should be narrow:

- JSON fence activation/compatibility syntax;
- JSON deserialization and diagnostics;
- mixed YAML/JSON candidate arbitration;
- proof that both serializers enter the same plan normalizer, authority path,
  executor, and renderer.

It does not need an independent tool-policy arc unless repo evidence finds a
real semantic difference after normalization.

## Relationship To Seed Prompt Recomposition

The seed recomposition should describe conversation, synthesis, and execution
independently of any one callable syntax. Once implemented, language-plus-exec
can become a selectable action-lane prompt asset:

- use executable language fences for code/interpreter-oriented action;
- retain structured YAML calls for non-code tools and arguments that are clearer
  as named fields;
- optionally teach `toas-tool exec` as the compact call-expression form for
  ordinary tool use;
- teach ordinary language fences as examples and `<language> exec` as the
  explicit potency transition;
- derive advertised languages and limits from the live execution registry.
- select overt or proxy-resilient activation examples from the active backend /
  transport prompt profile without changing the underlying authority contract.

No active prompt should teach this lane before extraction, authority, and
projection behavior exist.

## Acceptance Criteria

- [ ] A reusable fence scanner recognizes supported CommonMark fence boundaries,
  parsed info strings, exact source spans, and inert/output potency without
  relying on one regex per language.
- [ ] Lane potency is resolved through named envelope, structural, body-marker,
  or configured compatibility predicates with deterministic precedence and
  recorded provenance.
- [ ] Explicit inert, quoted, and non-active output forms override structurally
  callable content; malformed, multiply claimed, and ambiguous blocks fail
  closed.
- [ ] The canonical `<registered-language> exec` form and at least one
  structural/metadata-stripped fallback survive their declared proxy
  transformation specimens without changing authority.
- [ ] User- and assistant-authored executable fences route through their
  respective authority contexts without privilege laundering.
- [ ] Shell prompted form produces an ordered command sequence using existing
  multiline/heredoc-aware command-span semantics.
- [ ] Shell promptless form executes as one script operation with normal script
  semantics.
- [ ] Prompted and promptless result projections preserve their distinct command
  boundaries, stdout/stderr, status, and cancellation/timeout facts.
- [ ] Executable-fence candidates integrate with current textual intent
  arbitration without duplicating `$ ` candidates from inside the fence.
- [ ] A prompted sequence stops on first failure and exposes completed result,
  standalone editable retry, and unattempted forward plan without replaying
  completed commands.
- [ ] Reconciliation, transcript projection, history projection, and copying a
  completed rendered block do not cause accidental re-execution.
- [ ] A fence-lane registry routes only to explicit handlers/capabilities and reports
  unsupported languages or missing context safely.
- [ ] YAML and JSON serializers demonstrably share `normalize_tool_plan`,
  authority, execution, and result semantics after body deserialization.
- [ ] `toas-tool exec` has a non-evaluating, registry-validated call-expression
  grammar that normalizes into the canonical tool plan.
- [ ] Inner fences remain structurally round-trippable but opaque to execution
  unless one explicit composite handler owns bounded nested semantics.
- [ ] Shell-like fence behavior is proven end to end before additional language
  runners are treated as supported.
- [ ] Prompt/help assets advertise the lane only after the runtime contract is
  implemented, derive supported languages/activators from live registry truth,
  and may select a transport-appropriate activation profile.

## Non-Goals

- Treating every syntax-highlighted fence as executable.
- Inferring executability from language alone or fuzzy body resemblance.
- Turning arbitrary language tags into host executable names.
- Parsing promptless shell scripts into line-level transactions.
- Implementing every example language in the first slice.
- Replacing YAML calls for structured non-code tools.
- Using Python evaluation or arbitrary dynamic invocation for `toas-tool`.
- Implementing recursive nested execution without a concrete composite-lane use
  case.
- Mutating prior history to insert command output.

## Likely Ownership And Follow-On Split

Requirements parent ownership spans these future slices:

1. Markdown fence scanner and active/inert classification.
2. Potency resolver, proxy-transformation fixtures, lane registry, and intent
   arbitration.
3. JSON serializer corollary over the shared tool-plan normalizer.
4. `toas-tool` call-expression grammar and normalization.
5. Shell prompted/promptless runner adaptation and authority routing.
6. Interactive versus script result projection.
7. Prompted-sequence first-failure restaging, dependent on
   `260803-first-failure-plan-recovery`.
8. Prompt/help recomposition and live lane advertisement.
9. Additional language runners with explicit context and policy.

Open each implementation child only when its owner seam, state contract, and
test story are narrow enough to execute independently.

## Allowed Write Surfaces

- this task file and mechanically generated `tasks/WORKBOARD.md` sections
- follow-on task artifacts opened from the requirements decisions

## Required Completion Evidence

- fence grammar and fail-closed specimen matrix;
- activation precedence and proxy-transformation matrix;
- fence-lane registry and authority-context contract;
- shared YAML/JSON deserialization-to-plan contract;
- `toas-tool` call-expression grammar specimens;
- prompted versus promptless shell state/projection matrix;
- mixed-intent arbitration examples;
- completed/failed/retry/remainder projection examples;
- opaque-default nested-fence contract;
- bounded follow-on task graph with allowed write surfaces and tests.

## Operator Input Welcome

Useful additions include preferred interactive output shapes, shell transcript
examples with stderr or multiline commands, desired first non-shell runner,
CommonMark round-trip artifacts from web LLMs/editors, and opinions on whether
`exec` should remain the only initial info-string attribute.
