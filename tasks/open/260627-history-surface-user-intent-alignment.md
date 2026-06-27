Filed as: 260627-history-surface-user-intent-alignment
FKA:
AKA: history subcommand expectation audit; naive-user history affordances; history surface UX contract
Legacy index:

keywords: surface, investigation, inception, usability, history, projection, graph, transcript

Parent: `260614-architecture-follow-through-coordination`
Related: `260627-history-surface-corruption-semantics`; `260627-fail-closed-history-query-hardening`; `260627-history-recovery-tooling`; `260627-history-affordances-semantic-restaging`; `260627-split-storage-rebuild-and-projection-parity`; `260628-history-root-to-head-lineage-contract`; `260628-graph-selected-history-topology-framing`

# History Surface User Intent Alignment

## Current Reality

TOAS exposes several history-facing subcommands:

- `heads`
- `history`
- `transcript`
- `llm-input`
- `rebuild`
- `graph`

They are all mechanically meaningful, but they do not yet read as one coherent
operator-facing product surface.

A naive-user audit across docs, CLI routing, runtime code, and current
workspace behavior suggests several kinds of mismatch:

- some commands are named more broadly than the user intent they actually serve
  (`history` reads closer to "recent durable event summary" than "conversation
  history")
- some commands are much sharper or more mutating than their surface wording
  suggests (`rebuild`)
- some commands expose substrate truth in a form that is faithful but not
  obviously useful to a human operator (`graph`)
- some commands are comparatively well-shaped but underspecified in docs about
  what transformation they apply (`llm-input`)
- the commands do not yet tell one stable story about what "history" means to
  a user versus what it means to the substrate

The new `fsck` / fail-closed behavior improves integrity semantics, but it does
not by itself answer the more basic affordance question:

```text
if history is healthy, do these commands do what users actually want?
```

And, after refusal:

```text
if history is unhealthy, do the commands fail in a way that still matches user intent?
```

## Desired Reality

Each history-facing surface should have a crisp operator-facing job:

- what user question it answers
- what level of projection or normalization it applies
- whether it is observational, analytical, or mutating
- how it behaves on invalid targets
- how it behaves when `fsck` refuses the underlying history

The goal is not just consistency under corruption. The goal is that the set of
history commands feels intentional and legible to a user who is not reasoning
from implementation seams.

The next pass should treat this as a requirements problem, not just a naming
audit:

- each current surface needs its own operator-facing requirements
- the set of surfaces should be checked for missing user jobs, not only for
  defects in the current six
- the surfaces should stay conceptually aligned enough that learning one
  teaches the operator something about the others, even when their projections
  differ
- implementation sharing is desirable only insofar as it preserves a coherent
  user contract rather than leaking substrate seams into the surface

## Audit Findings To Preserve

The initial exploration surfaced these concrete pressures:

- `transcript` is close to "show me the conversation as TOAS can reconstruct
  it" and is one of the clearest surfaces
- `llm-input` is close to "show me what the model sees", but its projection
  rules (drop control, strip reasoning, coalesce adjacent user messages) should
  be explicit
- `history` currently mixes head listing with recent raw event summaries and
  therefore does not cleanly answer one user question
- `heads` is useful but terse; it may need either stronger framing or richer
  affordances for disambiguation
- `graph` is truthful substrate rendering, but it is not obvious that this is
  what a naive user wants when they ask to inspect history
- `rebuild` is the most dangerous mismatch because its name sounds inspectable
  but its effect is mutating and stateful
- invalid `head_id` handling and refusal output are part of the affordance
  contract, not just error handling trivia

## Focus

- write down operator-facing requirements for each of the six surfaces
- distinguish "history as user-facing material" from "history as durable event
  substrate"
- identify user questions that are not well served by the current six surfaces
- identify naming, output-shape, or help-text mismatches that make the current
  commands harder to use than they need to be
- define cross-surface consistency rules so the commands feel learnable as a
  family rather than as isolated utilities
- specify how `fsck` refusal should preserve affordance clarity rather than
  merely stopping execution
- decide whether some current commands need narrower framing, renamed
  semantics, or companion surfaces

## Exit Evidence

- a surface-by-surface requirements matrix for `heads`, `history`,
  `transcript`, `llm-input`, `rebuild`, and `graph`
- an explicit list of user-facing jobs that appear to need new or companion
  surfaces
- a cross-surface consistency rubric covering naming, targeting, projection
  framing, refusal text, and help/discoverability
- explicit notes on where current command names overclaim, underclaim, or hide
  mutation
- examples of healthy-history and corrupt-history behavior that still read as
  coherent operator affordances
- at least one bounded follow-on implementation or docs slice justified by the
  audit

## Requirements Shape

This task should now split its audit output into three requirement classes.

### 1. Per-Surface Requirements

For each of `heads`, `history`, `transcript`, `llm-input`, `rebuild`, and
`graph`, specify:

- primary user question answered
- secondary user questions it may answer incidentally
- target model: current/default lineage, explicit `head_id`, whole history, or
  other scope
- projection level: raw substrate, summarized durable history, transcript
  projection, model-input projection, or mutating reconstruction
- output contract: what shape the operator should expect on success
- invalid-target contract: what happens for unknown or ambiguous targets
- corruption/refusal contract: what it should say when normal use is refused
- discoverability contract: what the operator should be able to learn from
  `toas help`, local usage, and first successful output

### 2. Missing-Surface Requirements

The audit should also ask whether the current six omit operator jobs that are
important enough to deserve their own surface. Candidate user questions include:

- "show me recent durable events without mixing in branch-selection metadata"
- "show me which branch/head is current and why"
- "compare two heads"
- "show me what changed between transcript projection and model-input
  projection"
- "show me a safe summary when full graph rendering is too much"
- "show me what to do next when history is corrupt"

Not every missing job needs a new command. Some may be served by narrowing an
existing surface, adding a mode, or improving refusal/help text. The task
should still name the missing jobs explicitly.

### 3. Cross-Surface Consistency Requirements

Learning one history surface should help the operator learn the others. At
minimum, the family should align on:

- scope targeting: whether zero-arg means current/default lineage, whole
  durable history, or another well-signaled scope
- target syntax: how `head_id` or other selectors are spelled and explained
- framing language: "history", "transcript", "model input", "graph", and
  "rebuild" should each describe a distinct level of projection
- refusal behavior: corruption, unknown targets, and oversize outputs should
  fail in language that preserves the command's job
- help behavior: global help plus command-local usage/help should teach the
  operator what question the surface answers
- relation to mutation: observational versus mutating surfaces should be
  obvious before execution, not only after output appears

These requirements should stay user-first even when the implementation shares
reader/query/projection machinery underneath.

## Intent Matrix Draft

This draft focuses on two audit axes:

- discoverability: can an operator learn the command from global help, local
  usage behavior, or output framing?
- name space-claim: does the command's current wording fairly describe the job
  the command actually performs?

The current workspace is under fatal durable-history refusal, so the "current
observable behavior" column reflects both live CLI behavior now and healthy-log
 behavior inferred from the operator API.

| Surface | Operator question implied by name | Current observable behavior | Discoverability now | Name space-claim assessment | Notes / likely follow-on |
| --- | --- | --- | --- | --- | --- |
| `heads` | "What conversation branches or frontiers exist?" | On healthy history, shows one row per head with id, role, first-line preview, lineage depth, turn count, and provenance summary. On corrupt history, refuses with shared fatal-history text. | Present in top-level `toas help`. No subcommand-specific help text. Zero-arg invocation is safe and legible. Output shape is fairly self-explanatory once seen. | Mostly honest, but terse. "heads" is substrate-fluent more than naive-user fluent. | Likely needs framing/help-text rather than semantic redesign. Candidate question-driven gloss: "list branch tips". |
| `history` | "Show me history" or "show me recent conversation/history state" | On healthy history, mixes selected-head status, bind index, a head list, and recent raw event summaries in one surface. On corrupt history, refuses with shared fatal-history text. | Present in top-level help as `toas history [limit]`. No local help or framing for what kind of "history" appears. Output shape is not obvious from the name alone. | Overclaims. The name suggests a canonical answer to "history" while the implementation is really a mixed summary view. | Strongest candidate for follow-on work: either narrow the surface job, rename, or split head summary from recent-event audit. |
| `transcript` | "Show me the conversation transcript" | On healthy history, renders projected transcript text for a selected head or current default lineage. On corrupt history, refuses with shared fatal-history text. | Present in top-level help as `toas transcript [head_id]`. No subcommand-local explanation of projection rules or what `head_id` means. Zero-arg invocation is safe and intuitive. | Honest. This is one of the clearest name-to-job alignments. | Main gap is explanation: reconstructed transcript, selected lineage, and any projection omissions should be stated more explicitly. |
| `llm-input` | "Show me what is fed to the model" | On healthy history, renders projected model-input messages for a selected head or current default lineage. On corrupt history, refuses with shared fatal-history text. | Present in top-level help as `toas llm-input [head_id]`. No local help explaining projection transforms. The hyphenated name helps precision but is not self-explanatory to every operator. | Mostly honest, with some underexplained transformation hidden behind a precise name. | Needs explicit contract text: drop control records, strip reasoning, coalesce adjacent user messages, and otherwise clarify "model sees this, not raw history." |
| `graph` | "Show me the graph/history topology" | On healthy history, renders temporal or consequence graph projections, with a full-render refusal above node-count limits. On corrupt history, refuses with shared fatal-history text. | Present in top-level help with `--projection` usage. This is the only one of the six with a dedicated parse-level usage string. Still little explanation of why a user would choose it. | Honest for substrate-oriented users, but broad and underspecified for naive-user discoverability. | Likely needs framing rather than renaming: "render message graph" or better help/examples explaining temporal vs consequence views. |
| `rebuild` | "Rebuild what?" possibly inspect, regenerate, repair, or recover | On healthy history, rewrites `session.md` (or bound session file) from projected transcript for a selected head/default lineage and may write anchor state. On corrupt history, refuses with shared fatal-history text before mutation. | Present in top-level help as `toas rebuild [head_id]`. No subcommand-local warning that it mutates working transcript state. Zero-arg invocation is operationally easy but semantically under-signaled. | Underclaims mutation and overclaims safety/inspectability. This is the sharpest affordance mismatch. | Strong follow-on candidate: rename, add confirmation/preflight framing, or at minimum strengthen help/output text so the write effect is obvious before use. |

## Discoverability Findings

- The global `toas help` surface lists all six commands, so basic existence
  discoverability is decent.
- Subcommand-local discoverability is weak. Among these six, only `graph`
  currently has a dedicated parse-level usage string (`usage: toas graph
  [--projection temporal|consequence]`).
- `transcript`, `llm-input`, `history`, `heads`, and `rebuild` accept their
  common zero-arg shape without surfacing any contract text about what they are
  about to show or mutate.
- Shared fatal-history refusal currently dominates the live UX in this
  workspace. That consistency is good, but it also means refusal text is now a
  major discoverability surface for "what this command would normally do" and
  "what to try next."

## Fresh Pressure From Live Dogfooding

- `history` still exposes selected-head / bind-index status lines even though
  binding is no longer supposed to carry operator meaning on this surface. That
  makes the command feel more implementation-legacy than operator-intentful.
- The new fail-closed history contract surfaced a direct storage/integrity
  contradiction during fresh-log dogfooding: brand-new restepped history wrote
  first authored content as `n1` parented to virtual root sentinel `n0`, while
  `fsck` initially treated that same shape as fatal `missing_parent`
  corruption. The integrity gate needs to preserve the fresh-log storage
  contract rather than flagging the reserved sentinel shape as damage.

## Interim Judgment

- Best aligned today: `transcript`
- Good but terse: `heads`
- Precise but underexplained: `llm-input`
- Truthful but substrate-oriented: `graph`
- Overbroad / mixed-purpose: `history`
- Most dangerous affordance mismatch: `rebuild`

## Anchor Pair Requirements Draft

The strongest current framing candidate is:

- `graph` as the selected history graph
- `history` as one root-to-head lineage through that graph, analogous to
  `git log`
- `heads` as the leaf set of that graph
- `graph` as the topology-explicit view over that same history domain,
  analogous to `git log --graph`

That does not mean TOAS should mechanically imitate Git output. It means the
pair should share one operator story:

- same history domain
- same default scope assumptions unless explicitly overridden
- same target-selection model
- same corruption/refusal style
- different rendering emphasis

### `history` Requirements

#### Primary Job

Answer the operator question:

```text
what is the lineage from root to this head?
```

This is the root-to-head lineage view over the selected history graph. It is
not the topology-first surface and not the transcript-projection surface.

#### Scope Requirements

- zero-arg invocation should have one stable implicit anchor and explain it
  consistently in help text
- outside transcript context, that implicit anchor should be the last head and
  its ancestors
- inside transcript context, that implicit anchor should be whatever lineage
  the current transcript's LCP resolution identifies
- if broader history beyond that implicit slice is shown, that should be clear
  rather than implied accidentally by implementation detail
- any explicit targeting or alternate-scope modes should feel like extensions
  of the default readable history job, not like unrelated debug knobs

#### Projection Requirements

- show one lineage from root to a head in a human-readable summarized form
- prefer semantically meaningful rows over raw event dumps
- avoid mixing unrelated concerns in the default view
- do not surface stale bind-era or substrate-only metadata unless it directly
  answers the lineage question
- if branch/frontier context is included, it should support reading recent
  progression rather than becoming a second command hidden inside the first

#### Output Contract

On healthy history, the operator should be able to infer:

- what slice of history they are looking at
- whether that slice came from transcript/LCP context or from the last-head
  fallback
- which head closes the lineage they are reading
- why the listed rows are in that order
- whether the surface is showing one lineage, many heads, or a mixed summary
- what next command to use if they need transcript text, model-input
  projection, or topology

The output should read as one path, skimmable first and detailed second.

#### Discoverability Requirements

- `toas help` should teach that `history` is a root-to-head lineage view
- `toas help` or command-local help should also teach the implicit-anchor rule
  in user terms
- local usage/help should explain scope and what kind of rows appear
- first successful output should be self-framing enough that a user can tell
  whether they are looking at a lineage summary, full transcript, or raw event
  inventory

#### Failure / Refusal Requirements

- unknown or invalid targets should fail in terms of history selection, not
  internal graph machinery
- fatal corruption refusal should preserve the readable-history framing:
  "history cannot be shown because durable history is corrupt" is better than a
  substrate-only error without surface context
- refusal output should suggest the next best diagnostic or recovery lane

#### Non-Goals

- full transcript reconstruction
- exact model-input projection
- full topology rendering
- silent mutation or repair

### `graph` Requirements

#### Primary Job

Answer the operator question:

```text
how is this history branched or connected?
```

This is the topology-explicit sibling to `history`, not a separate history
universe.

#### Relationship To `history`

- `graph` should share the same underlying target/scope story as `history`
- a user who understands `history` should be able to predict that `graph`
  shows the same domain with branch structure made explicit
- differences should come from rendering emphasis, not from surprising changes
  in what counts as history

#### Scope Requirements

- zero-arg invocation should default to the same implicit anchor rule as
  `history`
- outside transcript context, that means last head and its ancestors
- inside transcript context, that means the lineage identified by the current
  transcript's LCP resolution
- if `graph` broadens beyond that implicit slice to show topology usefully,
  that broadening should be explicit in help/output framing
- projection modes such as temporal vs consequence should be presented as graph
  rendering variants, not as separate semantic surfaces

#### Projection Requirements

- expose branch/parentage/topology information clearly
- preserve truthful graph shape without requiring the operator to already think
  in storage internals
- support both compact understanding and deeper inspection
- when full rendering is too large, degrade in a way that still answers the
  topology question at a smaller scale or points clearly to the next surface

#### Output Contract

On healthy history, the operator should be able to infer:

- what nodes/edges are being represented
- whether the view stays inside the implicit anchor slice or includes
  surrounding topology for context
- what kind of topology view they are seeing
- how this view relates to the readable `history` surface
- when to switch to `heads`, `transcript`, or another surface for a different
  question

#### Discoverability Requirements

- `toas help` should teach that `graph` is the topology-oriented history view
- `toas help` or command-local help should teach the same implicit-anchor rule
  used by sibling surfaces
- local usage/help should explain projection modes in user terms
- successful output should not require prior knowledge of TOAS internals to be
  interpreted at a basic level

#### Failure / Refusal Requirements

- oversize-output refusal should still preserve the topology job, ideally by
  pointing to a smaller topology/disambiguation surface rather than only
  refusing
- fatal corruption refusal should parallel `history` in tone and clarity while
  remaining specific to topology rendering
- invalid projection-mode or target errors should stay surface-oriented and
  actionable

#### Non-Goals

- default narrative summary of recent progression
- transcript reconstruction
- model-input projection
- mutation or repair

### `history` / `graph` Consistency Rules

- Same family, different emphasis: `history` answers "what happened",
  `graph` answers "how is it connected".
- Shared target model: selecting a head or default scope should work the same
  way unless the output explicitly says otherwise.
- Shared refusal posture: corruption should read as one family contract, not as
  unrelated command-specific accidents.
- Distinct rendering contract: `history` optimizes for readable progression,
  `graph` optimizes for topology.
- Predictable next-hop story: each should make it easier to discover when the
  user really wants `transcript`, `llm-input`, `heads`, or recovery tooling.

### Deferred Shared Ref-Selection Constraint

`history`, `graph`, and `heads` should eventually share an explicit
ref-selection capability. That work is deferred. Until then, they should share
one implicit anchor rule rather than inventing a separate "current selected
lineage" authority.

The fallback anchor should be:

- outside transcript context: the last head and its ancestors
- inside transcript context: whatever lineage the current transcript's LCP
  resolution identifies

This is an important design guardrail:

- transcript/LCP truth stays primary when a transcript is in play
- no competing ambient lineage-selection state should be allowed to grow into a
  second authority
- the history-surface family should borrow one implicit slice-selection rule,
  not create a new durable or semi-durable selection concept

### Shared Object Model

These surfaces should be treated as convenience projections over the same
selected history graph, not as unrelated semantic products:

- `graph`: the selected history graph itself
- `history`: one root-to-head lineage through that graph
- `heads`: the leaf set of that graph

This wording is preferable to terms like "flattened history" because the
intended behavior is not to linearize all branches. It is to project one
lineage, the whole graph, or the graph's leaves depending on the surface.

## `history` Gap Analysis Against Requirements

Current implementation shape in `operator_api.history_lines(...)`:

- reads logical history
- emits `selected_head=...`
- emits `bind_index=...`
- emits a `heads:` section with terse head rows
- emits a `recent:` section with summarized recent events

That gives one command at least three partially independent jobs:

- current-selection status surface
- head/topology summary surface
- recent durable-event summary surface

### Requirement Mismatches

#### 1. Primary Job Mismatch

Requirement:

- `history` should answer a default readable progression question analogous to
  `git log`, namely one root-to-head lineage through the selected history graph

Current reality:

- it does not present one root-to-head lineage through history
- it presents status lines plus a head list plus recent event summaries
- the operator cannot tell which of those is the command's real center of
  gravity

Assessment:

- this is the largest mismatch
- the command currently reads like a composite debug/status surface rather than
  the default history view

#### 2. Scope Framing Mismatch

Requirement:

- zero-arg invocation should have one stable, explainable default scope

Current reality:

- `history` does not clearly signal whether it is about current lineage, all
  heads, recent journal tail, or a mixture
- because it always shows `heads:` and `recent:`, the effective scope is mixed
  even though the name suggests one coherent view

Assessment:

- the scope contract is not learnable from the name or output
- it does not expose the intended implicit-anchor rule at all
- this weakens the proposed sibling relationship with `graph`

#### 3. Projection-Level Mismatch

Requirement:

- `history` should show durable history in a human-readable summarized form
  without mixing unrelated concerns

Current reality:

- head rows are topology-adjacent
- recent rows are event-summary-adjacent
- selected-head and bind-index rows are control-state-adjacent

Assessment:

- the surface currently mixes at least three projection levels
- bind-era control material is especially hard to justify from a user-facing
  history contract

#### 4. Discoverability Mismatch

Requirement:

- help and first output should tell the operator what kind of history they are
  seeing

Current reality:

- top-level help exposes only `toas history [limit]`
- no command-local help explains what the rows mean
- first successful output relies on section labels (`heads:`, `recent:`) that
  reveal composition but not operator intent

Assessment:

- the output is not self-framing enough to teach the command's job
- a user can learn the pieces shown, but not why those pieces belong together

#### 5. Family-Consistency Mismatch With `graph`

Requirement:

- `history` and `graph` should feel like sibling views over the same history
  domain, with different rendering emphasis

Current reality:

- `graph` already reads as one thing: a topology rendering
- `history` does not yet read as the progression-oriented sibling; it reads as
  a miscellaneous summary

Assessment:

- until `history` becomes more singular, the `git log` / `git log --graph`
  analogy will not hold well enough to guide users

### Provisional Recommendation

The best next move appears to be **narrow first, split only if needed**.

That likely means:

- redefine `history` around one root-to-head lineage over the shared implicit
  slice as its primary and possibly only core job
- remove selected-head and bind-index rows from the default surface unless they
  can be defended as directly serving that job
- decide whether head listing belongs in `history` at all, or whether it should
  live in `heads` / `graph` and only be referenced as a next hop
- keep recent durable-event summarization only if it can be shaped into a true
  readable progression view rather than a raw tail dump

### Concrete Follow-On Questions

- Should zero-arg `history` mean "one root-to-head lineage in the implicit
  anchor slice" or something even narrower?
- Should `history` ever show multiple heads directly, or should that always be
  delegated to `heads` / `graph`?
- Is the right fix to change output shape only, or does `history` also need a
  different target model / CLI contract?
- Does a separate surface need to exist for "recent durable event audit" if
  that job is still valuable after `history` is narrowed?

## `graph` Gap Analysis Against Requirements

Current implementation shape in `operator_api.graph_text(...)`:

- reads graph-shaped history from `events.jsonl`
- renders one of two graph projections: `temporal` or `consequence`
- refuses full render above a node-count limit
- points oversize users to `toas heads` for compact branch summary

Compared with `history`, `graph` is much more singular. It already reads like
one command with one main job. The remaining pressure is mostly around user
framing and family coherence rather than core semantic sprawl.

### Requirement Mismatches

#### 1. User-Framing Mismatch

Requirement:

- `graph` should answer the operator question "how is this history branched or
  connected?" in terms a user can approach without already thinking in
  internals

Current reality:

- the command name points in the right direction
- the output is truthful topology rendering
- but help/usage do not explain what sort of graph is being shown or why a user
  would choose temporal vs consequence projection

Assessment:

- the main gap is not semantic dishonesty
- the main gap is underexplained purpose

#### 2. Family-Consistency Mismatch With `history`

Requirement:

- `graph` should feel like the topology-oriented sibling of `history`

Current reality:

- `graph` already feels topology-oriented
- but `history` does not yet feel like the readable progression sibling
- as a result, the family resemblance is weak even though `graph` itself is not
  especially confused

Assessment:

- this is partly a `history` problem, but it still matters here because `graph`
  currently has no framing that says "this is the branch-structure view of the
  same history"

#### 3. Scope-Clarity Mismatch

Requirement:

- scope and targeting should be predictable across the history-surface family,
  with the shared implicit-anchor rule as the zero-arg baseline

Current reality:

- `graph` takes no explicit head or scope selector today; it just renders the
  graph as a whole using the requested projection mode
- the absence of a target selector is not itself wrong, but it makes the family
  contract with `history` and `transcript` less obvious

Assessment:

- either `graph` needs explicit framing that it starts from the same implicit
  anchor rule as sibling surfaces, or it needs explicit explanation for any
  necessary broadening beyond that slice
- the current implementation does not reveal the intended implicit-anchor rule
  at all

#### 4. Oversize-Refusal Mismatch

Requirement:

- when full rendering is too large, refusal should still preserve the topology
  job or clearly hand the user to the next best topology/disambiguation view

Current reality:

- oversize refusal says to use `toas heads` for a compact branch summary
- that is useful, but it routes users out of the proposed `history` / `graph`
  sibling pair and into a third surface

Assessment:

- this may be correct pragmatically
- but it suggests a missing compact-topology mode or a better-framed
  relationship between `graph` and `heads`

#### 5. Discoverability Mismatch

Requirement:

- `toas help` and command-local usage should teach the job of the surface

Current reality:

- `graph` is the only one of the six with dedicated parse-level usage
- but the usage only documents projection flags, not the operator question the
  command answers

Assessment:

- `graph` is better than its siblings on syntax discoverability
- it is still weak on conceptual discoverability

### Where `graph` Already Fits Well

- It has one clear primary job.
- It is observational rather than mutating.
- Its name is broadly honest about its level of abstraction.
- Its projection-mode split (`temporal` / `consequence`) is at least explicit.
- Its fail-closed corruption behavior now aligns with the rest of the history
  surface family.

### Provisional Recommendation

For `graph`, the best next move appears to be **reframe first, redesign only if
needed**.

That likely means:

- keep `graph` as the topology-explicit history view
- improve help/output framing so users know why and when to choose it
- define its relationship to `history` and `heads` more clearly
- make the implicit-anchor rule visible, including any intentional topology
  broadening beyond the anchor slice
- decide whether oversize-topology inspection needs a compact graph mode,
  better `heads` integration, or simply better next-hop wording

### Concrete Follow-On Questions

- Should zero-arg `graph` show only the implicit anchor slice, or should it
  show the anchor slice plus adjacent branch context needed to make topology
  intelligible?
- Are `temporal` and `consequence` the right user-facing terms, or are they
  implementation-facing names that need explanation or relabeling?
- Is `heads` the right compact fallback for oversized graphs, or does that
  reveal a missing "compact graph history" surface/mode?
- How much of the `graph` problem disappears automatically once `history`
  becomes a clearer readable sibling?

## Initial Gap-Closing Follow-Ons

The first bounded follow-ons opened from this parent are:

- `260628-history-root-to-head-lineage-contract`
- `260628-graph-selected-history-topology-framing`

Those tasks should carry the first code/docs/test slices that close the most
concrete gaps, while this parent remains the design/source-of-truth task for
the shared history-surface model.
