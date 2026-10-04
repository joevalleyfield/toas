# Transcript Decorators: Human Names, Canonical References, And Inference Projections

Status: EXPLORATORY DRAFT
Normative Scope: design exploration; no runtime implementation or adopted grammar
Related Tasks: `260825-visible-transcript-turn-ids`, `260927-state-step-history-projections`, `260929-state-sequence-inference-affordance`
Normative Contract: `docs/notes/2026-10-04-transcript-reference-contract.md`

The follow-up discussion in sections 8–10 refines the earlier exploration:
human names belong to a working context, canonical IDs retain historical
identity, and model-facing identification depends on the inference packet.
The normative contract formalizing grammar, resolution, and packet assembly
lives in `docs/notes/2026-10-04-transcript-reference-contract.md`.
Theme families and syntax examples below remain possibilities, not adopted
requirements.

## 1. Problem Context: Beyond Ordinal Slugs

When `STATE/1`, `STATE/2`, and `--infer-from STATE/1` were introduced, the `/n`
suffix functioned as a minimal ordinal qualifier to distinguish sequential state
snapshots in a multi-state transcript.

However, treating `/n` as the only canonical decorator would artificially
narrow what a decorator can be. In TOAS, the core design split is:
- `session.md` is the user-controlled, editor-facing working surface;
- `events.jsonl` is the append-only, durable graph history;
- Model inference runs over an assembled, horizonal message packet (`llm-input`).

A **transcript decorator** is a presentation lens that surfaces graph facts
and useful human handles on the working transcript. Human decoration can be
excluded from model input. An explicit reference carries meaning, however,
and may require canonical identification or re-inclusion of referenced content
in the inference packet; zero token overhead is not a universal invariant.

## 2. Cognitive Ergonomics: Auditory Loops And Naming

Hexadecimal identifiers (`e_7ed5e9f2`, `8f3a`, `d4c1`) are technically compact,
unique, and machine-friendly. But in human cognition, they fail severely in the
**phonological / auditory loop**:
- A person subvocalizing "seven-e-d-five-e-nine-f-two" fills working memory with
  meaningless phonetic fragments.
- Hex strings are difficult to speak out loud, painful to transcribe across
  terminals, and nearly impossible to hold in mind while reading surrounding prose.

To make decorators truly usable as human-facing cognitive handles, we need
names that easily survive the auditory loop.

### Two Naming Modes

#### Mode A: Ordinal World Sequences (For Monotonic Step Progressions)
When turns or states progress through sequential transitions, natural-world
ordered sequences give instant relative position and immediate verbal ease:
- **NATO Phonetic Alphabet**: `alpha`, `bravo`, `charlie`, `delta`, `echo`,
  `foxtrot`... (Immediate verbal clarity; familiar progression).
- **Periodic Table of Elements**: `hydrogen`, `helium`, `lithium`, `beryllium`,
  `boron`, `carbon`... (Extensive, fixed order, universally recognizable).
- **Astronomical / Solar Bodies**: `mercury`, `venus`, `earth`, `mars`,
  `jupiter`, `saturn`... or planetary moons (`io`, `europa`, `ganymede`,
  `callisto`).
- **Alphabetical Botanical Sequences**: `alder`, `birch`, `cedar`, `dogwood`,
  `elm`, `fir`, `ginkgo`, `hazel`...
- **Geological Strata / Epochs**: `cambrian`, `ordovician`, `silurian`,
  `devonian`... (Evocative sense of temporal layers and history).

*Passive Learning as a Side-Effect of Usage*:
Configurable sequence domains create an unexpected cognitive affordance: by selecting
a domain (e.g. Greek alphabet, chemical elements, planetary moons, geological strata,
Japanese numbers, cranial nerves, taxonomic ranks), the operator passively internalizes
the sequence simply by working with TOAS day-to-day. The tool operates as an ambient,
frictionless memory reinforcer.

#### Mode B: Deterministic Mnemonic Names (For Arbitrary Graph Entities)
For arbitrary, non-sequential graph entities (like durable event hashes,
fork points, or patch deltas), Docker-style or Antigravity-style adjective-noun
pairings (`clever-curie`, `bold-bohr`, `calm-cedar`, `brisk-fox`) could provide
candidate handles derived deterministically from the underlying ID.
- Hashing `evt_7ed5e9...` into a 2-word phrase from a small curated dictionary
  (e.g., 256 adjectives x 256 nouns = 65,536 combinations) produces names that:
  1. are deterministic and stable across sessions;
  2. roll off the tongue effortlessly;
  3. are memorable in conversation or notes, with collisions still possible.

This is one possible naming scheme. A finite vocabulary does not guarantee
uniqueness, and the later discussion does not require a human name to be a
permanent global alias for its canonical target.

#### Hybrid Syntax
Where technical precision and human memory meet, a hybrid decorator can pair
the mnemonic handle with an abbreviated hash:
```markdown
## TOAS:STATE/bravo [e:8f3a]
## TOAS:ASSISTANT [bold-bohr e:9c12]
```
The operator talks about and addresses `bravo` or `bold-bohr`, while tools and
scripts can resolve the underlying event identity. The displayed short
fingerprint is illustrative, not a guaranteed unique event locator.

## 3. Branching Topology: Sequences Of Sequences And Collections Of Sibling Lanes

When a history branches, how should naming behave? A pure linear sequence
collapses on a fork, while raw hierarchical paths (`bravo/branch1/child3`)
quickly become visually noisy and phonetically clumsy.

There are two powerful structural ways to handle branching and multi-level
needs:

### Model 1: The Sequence Of Sequences (Ordered Meta-Generations)

In this model, sequences are ordered hierarchically across generations:
- **Trunk (Generation 1)** uses the primary sequence: `alpha` -> `bravo` -> `charlie`.
- **First-generation branches (Generation 2)** advance to the next configured sequence
  family:
  - Branching from `bravo` seeds the fork by pairing the parent with the first
    token of Generation 2: `charlie-hydrogen`.
  - Continuation advances in Generation 2: `charlie-hydrogen` -> `charlie-helium` -> `charlie-lithium`.
  - Once established as the working focus, the parent prefix can fade or drop:
    `charlie-lithium` -> `lithium` -> `beryllium`.
- **Sub-branches (Generation 3)** draw from the third sequence family (e.g. Botanical:
  `lithium-cedar` -> `lithium-dogwood`).

### Model 2: Unordered Collections Of Related Sequences (Constellations Of Sibling Lanes)

Rather than forcing an arbitrary hierarchy between unrelated domains (like NATO
to Elements), a domain can be structured as an **unordered collection of related
sibling sequences**.

In this model, the parent domain contains multiple cohesive sequence families.
When a branch occurs, it is allocated a fresh sibling sequence from the same
thematic collection:

#### Exemplar Sibling Collections:
1. **Astronomy (Planetary Moon Systems)**:
   - Primary trunk uses Jovian moons: `io` -> `europa` -> `ganymede` -> `callisto`.
   - Branch A forks and claims the Saturnian lane: `titan` -> `enceladus` -> `rhea` -> `dione`.
   - Branch B forks and claims the Uranian lane: `ariel` -> `umbriel` -> `miranda` -> `titania`.
2. **Chemistry (Periodic Families / Groups)**:
   - Primary trunk uses Noble Gases: `helium` -> `neon` -> `argon` -> `krypton`.
   - Branch A forks and claims Alkali Metals: `lithium` -> `sodium` -> `potassium`.
   - Branch B forks and claims Halogens: `fluorine` -> `chlorine` -> `bromine`.
3. **Forestry (Tree Genera)**:
   - Trunk uses Oaks (*Quercus*): `white-oak` -> `red-oak` -> `live-oak` -> `pin-oak`.
   - Branch A uses Pines (*Pinus*): `white-pine` -> `ponderosa` -> `lodgepole`.
   - Branch B uses Maples (*Acer*): `sugar-maple` -> `red-maple` -> `silver-maple`.
4. **Geology (Eras, Periods, And Epochs)**:
   - Paleozoic lane: `cambrian` -> `ordovician` -> `silurian` -> `devonian` -> `permian`.
   - Mesozoic lane: `triassic` -> `jurassic` -> `cretaceous`.
   - Cenozoic lane: `paleocene` -> `eocene` -> `oligocene` -> `miocene`.

#### Cognitive & Architectural Advantages:
- **Distinct Vocabularies Without Punctuation Clutter**: Allocating disjoint
  sibling sequences could distinguish concurrently presented branches without
  path separators like `branch_1/step_2`. Exhaustion, custom dictionaries, and
  copied fragments still need local ambiguity handling; this is not a global
  uniqueness guarantee.
- **Semantic Affinity**: The operator instantly understands that `titan`,
  `enceladus`, and `rhea` belong to the same exploration thread because they share
  a single thematic lane.
- **Thematic Integrity**: The working surface avoids jarring cognitive dissonance.
  Instead of mixing arbitrary phonetic words with chemical elements and tree names,
  the session stays anchored in a single rich metaphorical space (e.g. exploring
  the Solar System's moons).
- **Graceful Multi-Level Forking**: Sub-branches either draw another sibling
  sequence from the pool, or use the composite seed (`titan-chlorine`) before
  stabilizing.

## 4. Entity-Type Variations: Matching Naming To Semantic Role

Different semantic objects in TOAS have very different cognitive needs. Forcing
one naming convention across all entity types creates either collision risks or
unnecessary auditory overhead.

| Entity Type | Example Surface | Primary Cognitive Need | Recommended Naming Variation |
| :--- | :--- | :--- | :--- |
| **State Snapshots (`STATE`)** | `## TOAS:STATE/bravo` | **Strict Order & Weight**. Needs clear temporal sequence and macro milestone weight. | Primary ordinal sequence (e.g. NATO, Elements, Greek letters). |
| **State Diffs (`STATE-DIFF`)** | `## TOAS:STATE-DIFF [delta:b->c]` | **Relational Vector**. Needs to express transition from $S_A$ to $S_B$. | Transition markers (`alpha->bravo`, `Δ-charlie`) or patch deltas. |
| **Conversational Turns (`USER`, `ASSISTANT`, `CONTROL`)** | `## TOAS:ASSISTANT [turn:4]` | **Pacing & Attribution**. Needs light turn indexing without heavy semantic baggage. | Simple turn ordinals (`t:4`) or light conversational identifiers. |
| **Tool Plans (`pending_tools`)** | `pending_tools: [p:read_1, p:shell_2]` | **Intent & Batch Membership**. Tentative proposals before execution. | Batch-indexed action slugs (`plan:read-a`, `plan:test-b`). |
| **Tool Results (`RESULT` blocks)** | Human handle `calm-cedar` over canonical `block_id=ib_...` | **Concrete Fact & Reuse**. Empirical external observations. | Deterministic adjective-noun pairs (`calm-cedar`) or gem/mineral nouns (`jade`, `cobalt`), with canonical block IDs preserved underneath. |

### Where Order Is Useful vs. Where Clash Prevention Dominates

- **Where Order Dominates**:
  In `STATE` milestones and conversational turns, the human mind cares deeply about
  *before* and *after*. Using sequential systems (NATO, Elements) directly serves
  reasoning about causality and state history.
- **Where Clash Prevention Dominates**:
  In `RESULT` blocks and external tool outputs, multiple independent artifacts
  are emitted concurrently. Strict linear order is less meaningful than absolute
  unambiguous reference. Here, high-entropy adjective-noun pairings or distinct
  category nouns (e.g., minerals: `amber`, `cobalt`, `quartz`) can make references
  across distant turns easier to use (`(ref: quartz)`). Canonical block IDs
  retain identity; names must resolve unambiguously within their working context.
- **Crossing Boundaries**:
  When a forward `STATE` observation references an earlier `RESULT` block:
  ```markdown
  ## TOAS:STATE/charlie
  state: ...
  observations:
    - tool_output: (ref: cobalt)
  ```
  The operator immediately recognizes `charlie` as a state milestone and `cobalt`
  as an inert tool result without confusing the two namespaces.

## 5. Resonant Derivation And The Principle Of Pluralistic Variety

The linguistic, metaphorical, and cognitive possibilities in this space are
almost boundless. Rather than hard-coding a handful of "optimal" sequences, TOAS
should treat decorator generation as an open, pluralistic affordance engine.

### Resonant Namespace Derivation

Tool calls, plans, and results do not need to exist in sterile, isolated
namespaces. Instead, their handles can **resonate** with the active turn sequence,
inheriting a loose semantic flavor from their parent turn:

- **Celestial / Moon Turn (`STATE/europa`)**:
  - Tool calls adopt exploration probes or surface vectors: `call:galileo`, `call:voyager`.
  - Result blocks adopt surface features or ice geology: `ib_linea`, `ib_chaos_terrain`.
  - The operator immediately senses that `ib_chaos_terrain` was an empirical outcome
    harvested during the `europa` state, without needing a rigid hierarchical path.
- **Arboreal / Tree Turn (`STATE/cedar`)**:
  - Tool calls adopt botanical actions: `call:canopy_sweep`, `call:core_sample`.
  - Result blocks adopt anatomical features: `ib_heartwood`, `ib_burl`, `ib_amber`.
- **Elemental Turn (`STATE/helium`)**:
  - Tool calls adopt spectroscopic or physical concepts: `call:cryo_scan`, `call:spectral_line`.
  - Result blocks adopt phenomena: `ib_glow`, `ib_superfluid`.

The relationship is **poetic and associative rather than strictly taxonomic**.
It provides immediate ambient context in human auditory memory without imposing
brittle ontology rules.

### The Principle Of Pluralistic Variety (The Anti-Monoculture Rule)

No single sequence or theme fits every operator, task, or mood. While periodic
elements and NATO words are great baselines, confining the system to "the few
sequences that test best" misses the joy and cognitive diversity of human
language:

1. **Theme Packs And Semantic Flavors**:
   - **Austere / Minimalist**: Short ordinals (`s1`, `s2`), Greek letters (`α`, `β`), or hex tags (`e:8f3a`). Ideal for rapid scripting or low-noise workflows.
   - **Academic / Physical**: Periodic Table, Geological Epochs, Taxonomic Ranks, Cranial Nerves. Ideal for passive learning and scientific work.
   - **Navigational / Maritime**: NATO phonetics, Compass Points, Wind Scales (Beaufort), Nautical Knots.
   - **Literary / Celestial**: Constellations, Major Stars, Mythological Pantheons, Scale Modes (`dorian`, `phrygian`).
   - **Playful / Tactile**: Culinary herbs (`thyme`, `rosemary`), Minerals & Pigments (`cobalt`, `ochre`, `lapis`), Fauna (`fox`, `heron`, `otter`).
2. **Loose Binding Over Rigid Schemas**:
   - The engine should allow loose, fuzzy, or whimsical relations between entities:
     an operator might want strict Elements for States, but totally free-form
     playful pairs for tool results.
   - Custom user dictionaries: dropping a simple list or YAML theme pack into
     `.toas/themes/` or `~/.config/toas/themes/` lets users customize their working
     environment just as they customize syntax themes in Vim.

### Primitive Composition Over Complex Policy (The OMZ Pattern)

In shell environments like Oh My Zsh, users often employ a bifurcated theme
setup: selecting from a curated rotation of 3–4 trusted favorites most of the
time, while occasionally sampling from the broader wild universe.

Rather than building complex, opinionated theme-selection logic directly into
TOAS, the architecture should provide **simple, composable primitives** that
allow operators to construct their own selection models:

1. **Primitive A: Uniform Theme Identifiers (Built-Ins + Bring-Your-Own)**:
   - Built-in names: `ordinals` (`s1`, `s2`), `greek` (`α`, `β`), `hashes` (`8f3a`),
     `nato`, `elements`, `constellations`, `forestry`.
   - User-defined paths: pointing to local files or directories
     (`~/.config/toas/themes/my-vocab.yaml`).
   - In-line arrays: defining a quick list directly in configuration.
2. **Primitive B: Candidate Pools And Evaluated Expressions**:
   - Support candidate lists in config:
     `theme: [elements, celestial, forestry]`
     which TOAS can resolve deterministically per session (e.g., hashed against the
     session name or first commit ID) or rotate across new lineages.
   - Shell/environment pass-through: `theme: "${TOAS_THEME}"` allows external
     scripts (or a user's zsh setup) to drive the active theme dynamically.
3. **Primitive C: Graceful Overflow And Exhaustion Invariants**:
   - What happens when a sequence is exhausted? (e.g. NATO runs out at 26, or a
     custom sequence has only 5 items).
   - Primitives should guarantee safe overflow:
     - *Tick notation*: `alpha` -> ... -> `zulu` -> `alpha'` -> `bravo'`.
     - *Index suffix*: `alpha.2`.
     - *Fail-safe spillover*: falling back cleanly to short hashes or ordinals
       rather than erroring out or stalling step execution.
4. **Primitive D: Clean Precedence Hierarchy**:
   - User global (`~/.config/toas/config.yaml`) ->
   - Workspace local (`.toas/config.yaml`) ->
   - Step invocation override (`toas step --theme ...` or `/config set transcript.theme ...`).

## 6. The Decorator Domain: What Facts Belong in the Lens?

Decorators can reveal distinct facets of durable history without cluttering
turn content:

| Facet | Potential Decorators | What It Tells the Operator |
| :--- | :--- | :--- |
| **Identity & Handle** | Sequence name (`bravo`), mnemonic alias (`bold-bohr`), or short fingerprint (`id:8f3a`) | A human handle for contextual selection, backed by canonical identity. |
| **Lineage & Forking** | `parent:alpha`, `^8f39`, `branch:charlie-helium` | Explicit topology; reveals when a turn forks rather than continues. |
| **State & Delta Role** | `delta:d_01`, `key:true`, `anchor` | Distinguishes whether a state turn is an anchor snapshot, intermediate delta, or key milestone. |
| **Chronology & Performance** | `t:09:14:22`, `dur:1.2s`, `seq:4` | Wallclock execution time and latency without searching through daemon logs. |
| **Execution Outcome** | `exit:0`, `status:ok`, `tools:2` | Compact outcome preview for tool execution and consequence layers. |

## 7. Syntactic Formats On The Working Surface

How does this live in `session.md` while preserving clean Markdown reading and
editor ergonomics?

### Option 1: Role Header Trailer (Grammar-Aligned)
`src/toas/transcript.py` already includes regex support for qualifiers and trailers:
```python
_TRANSCRIPT_ROLE_MARKER_RE = re.compile(
    r"^## TOAS:(SYSTEM|USER|ASSISTANT|CONTROL|STATE|STATE-DIFF)(?:/([^ \t]+))?(?:[ \t]+(.*))?$"
)
```
The generic transcript parser accepts and preserves headings such as:
```markdown
## TOAS:STATE/bravo [id:8f3a t:09:14:22 key:true]
## TOAS:ASSISTANT [bold-bohr dur:1.8s]
## TOAS:STATE-DIFF/charlie-hydrogen [parent:bravo delta:d_02]
```
- **Pros**: Zero vertical whitespace overhead; stays on the single `## TOAS:...`
  header line. Structured decorator parsing would be a new contract: the current
  parser preserves the marker rather than producing an attribute map, and state
  selectors currently recognize numeric qualifiers.
- **Cons**: Can grow wide if too many attributes are enabled at once.

### Option 2: Metadata Attribute Line / Block
A metadata comment immediately following the header:
```markdown
## TOAS:STATE/bravo
<!-- toas: id=8f3a parent=alpha t=09:14:22 key=true -->
```
- **Pros**: Clean header line; easy to collapse or visually deemphasize with Vim folding
  or conceal syntax.
- **Cons**: Adds an extra line per turn.

### Option 3: Configurable Projection Lenses
Like `git log --oneline` vs `git log --decorate`, the operator can choose how much
metadata the transcript projects:
- `toas transcript --decorate=none` -> `## TOAS:STATE` (pure prose)
- `toas transcript --decorate=short` -> `## TOAS:STATE/bravo` (mnemonic handle only)
- `toas transcript --decorate=full` -> `## TOAS:STATE/bravo [id:8f3a t:09:14:22]` (full metadata)

## 8. Lifecycle And Affordances

### Working context and durable identity — confirmed direction

The event log is almost entirely write-only in ordinary use. Reconstructing,
reading, and branch-continuing an ancient transcript remain important, but
human names need not be permanent global identifiers across those histories.
Canonical event and result-block IDs retain their existing identity semantics.

Names should stay dependable while their objects or references remain in the
user's working context. Editing a turn need not immediately change its human
name. Ordinary appends provide an order for assigning later names. A projection
that temporarily hides a turn is not necessarily the end of that context;
similarly, a state reference can keep an older result relevant after its source
turn leaves the visible transcript.

The selected transcript and LCP reconciliation supply branch context:

```text
original bravo -> child referring to bravo
edited bravo   -> child referring to bravo
```

Each child refers to the turn in its own transcript. A decorator does not
override LCP, turn changed content into an old event, or select historical
parentage independently. The previous proposal that an ID trailer itself
causes a branch from the identified event is superseded.

A freshly reconstructed context may receive new names, provided its retained
references remain coherent. Exact assignment, retirement, and reconstruction
mechanics are open. Copy/paste is a concrete source of duplicate definitions;
names need local ambiguity handling, not global uniqueness.

### Optional historical naming evidence — tentative

History might retain that an object was once displayed under a particular name
and thematic sequence. Such evidence would aid recognition, not establish a
must-be-unique alias or override current contextual resolution. Whether to
record assignments, uses, or both, and whether this belongs in entry metadata
or a separate append-only record, remain open. This is not a prerequisite for
the first human naming affordance.

### Text search and editor navigation — explored

Alphabetic progression could map naturally to editor-local marks. However,
searchable definitions and references already provide editor-neutral navigation:

```markdown
## TOAS:USER #bravo [87fd...]

Reconsider @alpha before continuing.
```

Alternative heading spelling: `## TOAS:USER [bravo 87fd...]`. Using `#bravo`
for references too would let search walk definitions and uses together; using
`#bravo` for definitions and `@bravo` for references separates those searches.
These are syntax candidates, not an adopted grammar. Vim marks, completion,
highlighting, and go-to-reference behavior can remain optional conveniences.

## 9. References And Inference Packets — 2026-10-04 Refinement

### Explicit references — confirmed direction, grammar open

The strongest turn-name use-case is talking about earlier transcript turns.
Explicit prose syntax should distinguish a reference from an ordinary word;
every occurrence of "bravo" must not become a candidate for reinterpretation.
Literal examples and inert source/result bodies also need a non-reference
interpretation. Exact syntax and escape/literal rules remain open.

Human references resolve within the selected working context to canonical
targets. Model-facing references use canonical IDs rather than overloaded
thematic words. A reverse projection back to human names is a useful tentative
extension when model responses refer to those IDs.

For result deduplication, user-facing `(ref: cobalt)` could resolve to the
existing `ib_...` block ID. The current state path already condenses inert
blocks into canonical references and expands available bodies when building
model input. Human names would layer over that mechanism; they would not
replace canonical block IDs.

### Inclusion and identification — confirmed distinction

What a reference requests depends on the inference packet:

| Packet style | Reference consequence |
| --- | --- |
| Ordinary state packet | Re-include referenced material absent from the current state/observation packet. |
| Transcript packet with identification on demand | When the target is already included, add its model-facing turn ID and translate the reference. |
| Transcript packet with identification always present | Translate the reference; included turns already carry their model-facing IDs. |

Identity alone does not supply content. If a selected transcript packet omits
the target, its inclusion rule still needs to be explicit. The placement and
lifetime of re-included material in state packets remain open; reference
expansion does not by itself mean permanently copying material into state.

"Inference profile" is tentative vocabulary for packet-building choices.
Content inclusion and identity decoration are separate dimensions. Selecting a
human state-history view should not implicitly select an inference profile.
The existing explicit multi-state `/infer-from` path is another packet shape
to account for, rather than assuming all state inference is state-only.

Always-present model IDs may be useful for preserving KV-cache prefixes.
Adding an ID retroactively to an earlier heading changes the token prefix at
that point. Always emitting stable canonical IDs costs tokens but avoids that
particular rewrite; it does not guarantee backend cache availability. See
[llama.cpp server prompt-cache behavior](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).
Human theme changes need not change the canonical IDs serialized to the model.
Neither decoration policy nor its default has been selected.

The earlier universal LLM-inert claim is superseded: decorative names can be
excluded, but meaningful references require translation, identification, or
content inclusion. This is design direction, not an implemented invariant.
In particular, the current multi-state packet builder forwards state headings.

## 10. Decision Order And Existing Task Boundaries

Proposed next design milestone: a small reference contract. Earlier theme
exploration remains available without becoming a prerequisite.

| Decide sooner | Reason |
| --- | --- |
| Definition/reference grammar and literal boundaries | Recognize intentional references without rewriting ordinary prose. |
| Working-context assignment and retention | Preserve familiar names through edits, appends, retained references, and view changes. |
| Resolution relative to LCP reconciliation | Avoid treating mere redecoration or equivalent reference spelling as substantive edits; preserve real branching. |
| Packet inclusion and identification rules | Make state re-inclusion and transcript ID decoration explicit, including cache tradeoffs. |
| Missing or ambiguous target behavior | Handle copied fragments and unresolved references without guessing. |

Tentatively defer thematic dictionaries, sibling-sequence allocation, prefix graduation,
exhaustion spelling, rich metadata trailers, editor integrations, and a general
inference-profile configuration framework. Historical naming storage remains
open. Key-state designation is a separate projection choice: having a name
does not itself make a state a milestone.

Proposed task routing, not task promotions or new implementation commitments:

- [Visible transcript turn IDs](../../tasks/open/260825-visible-transcript-turn-ids.md)
  is the existing design home for human names, contextual canonical reference
  resolution, and model-facing identification. Its earlier hidden-ID wording
  needs the profile-dependent refinement above. Bounded implementation children
  can follow once the contract is concrete.
- [State-step history projections](../../tasks/open/260927-state-step-history-projections.md)
  retains ownership of the five views, key-state designation, and projection
  selection. Display-only changes should preserve model semantics; explicit
  reference inclusion and multi-state inference are distinct packet choices.
  It need not wait for elaborate themes.
- [Projection discoverability](../../tasks/open/260823-projection-discoverability.md)
  can teach the concrete surfaces after their contract exists.
- [Transcript highlighting](../../tasks/open/260813-transcript-highlighting-design.md)
  can consume the eventual grammar. Search already supplies basic navigation;
  a separate marks task is unnecessary at this stage.

The specimens in section 11 ground these boundaries across a past-turn
reference, a result reference carried into state, an edit to a named turn,
and reconstruction with fresh labels. No new task or runtime implementation
is opened by this note update.

## 11. Concrete Transcript Specimens

The specimens below ground the reference and identification design in four
concrete scenarios: past-turn prose references, result-block references carried
into state, in-place edits reconciled via LCP, and reconstruction with fresh
labels.

### Specimen 1: Past-Turn Prose Reference (`[[bravo]]`)

#### Human Working Surface (`session.md`)
The operator defines turns with labels and writes a reference in a later prompt:

```markdown
## TOAS:SYSTEM [[alpha]]
You are a software engineering assistant working on TOAS.

## TOAS:USER [[bravo]]
We should evaluate using SQLite instead of PostgreSQL for session storage.
Keep it local and embeddable.

## TOAS:ASSISTANT [[charlie]]
Agreed. SQLite gives us zero daemon overhead and fast local queries.

## TOAS:USER [[delta]]
Reconsider [[bravo]] before we write the migration script.
Does an embedded database meet our multi-process daemon requirements?
```

#### Canonical Resolution Table (Working Context to Graph)
The runtime resolves working handles within the active transcript to durable
append-only event IDs in `events.jsonl`:

| Handle | Role | Canonical Event ID | Reference Target in Turn |
| :--- | :--- | :--- | :--- |
| `alpha` | `SYSTEM` | `evt_01j7a1...` | — |
| `bravo` | `USER` | `evt_01j7b2...` | — |
| `charlie` | `ASSISTANT` | `evt_01j7c3...` | — |
| `delta` | `USER` | `evt_01j7d4...` | `[[bravo]]` -> `evt_01j7b2...` |

#### Model Inference Packet (`llm-input`) Comparison

##### Option A: On-Demand Turn ID Injection (Dynamic)
IDs are injected only into turns that are actively cited. Other turns stay bare:

```markdown
## TOAS:SYSTEM
You are a software engineering assistant working on TOAS.

## TOAS:USER [turn:evt_01j7b2]
We should evaluate using SQLite instead of PostgreSQL for session storage.
Keep it local and embeddable.

## TOAS:ASSISTANT
Agreed. SQLite gives us zero daemon overhead and fast local queries.

## TOAS:USER
Reconsider [turn:evt_01j7b2] before we write the migration script.
Does an embedded database meet our multi-process daemon requirements?
```

*Cache Tradeoff*: Injected IDs alter the token stream of earlier turns,
invalidating the prompt/KV-cache prefix from that point forward.

##### Option B: Always-Present Stable Turn IDs (Cache-Stable)
Every turn carries a compact, monotonic index or hash prefix from the start:

```markdown
## TOAS:SYSTEM [t:1]
You are a software engineering assistant working on TOAS.

## TOAS:USER [t:2]
We should evaluate using SQLite instead of PostgreSQL for session storage.
Keep it local and embeddable.

## TOAS:ASSISTANT [t:3]
Agreed. SQLite gives us zero daemon overhead and fast local queries.

## TOAS:USER [t:4]
Reconsider [t:2] before we write the migration script.
Does an embedded database meet our multi-process daemon requirements?
```

*Cache Tradeoff*: Adds token overhead per turn, but avoids retroactive heading
changes caused by later references. Other packet changes and backend behavior
can still affect prefix reuse. Index allocation and the default policy remain
open.

---

### Specimen 2: Result Block Reference Carried into State (`[[cobalt]]`)

#### Human Working Surface (`session.md`)
An assistant turn executes a search tool. The inert result block carries both
its canonical block ID and a human handle `cobalt`. Later, a `STATE` turn records
an observation referencing it:

````markdown
## TOAS:ASSISTANT [[charlie]]
```python block_id=ib_9a4f handle=cobalt
src/toas/cli.py
    436: def main():
```

## TOAS:STATE [[delta]]
state:
  active_focus: cli entrypoint
  observations:
    - cli_symbol_table: "[[cobalt]]"
````

#### Canonical Resolution
- `cobalt` resolves to inert block `ib_9a4f` in durable storage.
- Authored state remains available. A proposed source-linked resolution fact
  records that this use of `cobalt` targets `ib_9a4f`; storage layout remains
  open. This specimen does not require rewriting authored state into bare IDs.

#### Model Inference Packet (`llm-input`)
If `charlie` has scrolled out of the active context window (for example, in a
condensed state packet), the runtime sees the reference and re-includes the
content:

````markdown
## TOAS:STATE
state:
  active_focus: cli entrypoint
  observations:
    - cli_symbol_table:
```python block_id=ib_9a4f
src/toas/cli.py
    436: def main():
```
````

Identity alone does not supply content; the reference contract re-hydrates
`ib_9a4f` directly into the packet.

---

### Specimen 3: In-Place Edit to a Named Turn (LCP Reconciliation)

#### Original Working Surface
```markdown
## TOAS:USER [[bravo]]
Run pytest on tests/test_cli.py.

## TOAS:ASSISTANT [[charlie]]
Tests failed: 1 failure in test_main_help.
```

#### User Action: In-Place Edit
The operator edits turn `bravo` in place to add `--verbose`, and runs `toas step`:
```markdown
## TOAS:USER [[bravo]]
Run pytest on tests/test_cli.py with -vv and -s.
```

#### LCP Reconciliation & Identity Mechanics
1. **LCP Match**: The parser compares `session.md` against the durable graph.
   The longest common prefix ends at `alpha` (prior to `bravo`).
2. **Branch Creation**: The runtime does not overwrite `evt_01j7b2`. It appends
   a new event `evt_01j7e5` with parent `alpha`.
3. **Handle Retention**: In the active working context, the active turn remains
   labeled `[[bravo]]` (or graduates to a branch label if multiple branches are
   projected). The superseded historical event `evt_01j7b2` remains in
   `events.jsonl`.
4. **LCP Primacy**: Text changes fork the graph through prefix reconciliation;
   the human handle remains bound to the physical text in the working copy.

---

### Specimen 4: Reconstruction with Fresh Labels

#### Scenario
An operator switches their configured theme from NATO phonetics (`alpha`, `bravo`)
to Periodic Elements (`hydrogen`, `helium`) and runs `toas transcript`.

#### Re-Projected Working Surface
```markdown
## TOAS:SYSTEM [[hydrogen]]
You are a software engineering assistant working on TOAS.

## TOAS:USER [[helium]]
We should evaluate using SQLite instead of PostgreSQL for session storage.
Keep it local and embeddable.

## TOAS:ASSISTANT [[lithium]]
Agreed. SQLite gives us zero daemon overhead and fast local queries.

## TOAS:USER [[beryllium]]
Reconsider [[helium]] before we write the migration script.
Does an embedded database meet our multi-process daemon requirements?
```

#### Mechanics
- Canonical graph IDs `evt_01j7a1...` through `evt_01j7d4...` are unchanged.
- The projection renderer assigns `helium` to `evt_01j7b2`.
- When rendering `beryllium`, the reference that canonically points to
  `evt_01j7b2` is dynamically re-rendered as `[[helium]]`.
- The human experience is seamless and coherent, while the durable record
  remains immutable.

Reconciliation must also compare the resolved reference targets; otherwise
the literal body change from `[[bravo]]` to `[[helium]]` creates a branch in
the current implementation. This is an intended specimen, not current runtime
behavior. See the comparison proposal below.

## 12. Retained References And LCP Comparison Follow-Up

The [reference contract](2026-10-04-transcript-reference-contract.md) now
distinguishes authored text, canonical reference-resolution evidence, the LCP
comparison form, and model-facing packets. Model marker projection is sometimes
needed; its syntax, visibility filtering, and result expansion do not define
transcript cleanup for reconciliation.

Proposed retained bindings travel with a working context when a definition
leaves the visible transcript. A current name still resolves against a visible
edited turn; historical evidence must not silently pin that use to an abandoned
revision. Explicit canonical references can deliberately name historical
targets. Physical binding syntax and record schema remain open.

The proposed comparison preserves exact literal text and substitutes typed
canonical target atoms only for recognized references. Re-theming a reference
without changing its target can preserve the prefix; editing prose, a literal
example, or the target itself remains a substantive change. Prefix matching
establishes earlier turn identities before new suffix references are recorded.
This preserves LCP parent selection without using speculative new event IDs.

The contract includes a required lifecycle/comparison specimen matrix. It is
design work, not a runtime implementation or a general normalization pass.
