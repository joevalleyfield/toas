# Transcript Decorators: Human Ergonomics, Visible Graph Truths, And LLM-Inert Projections

Status: EXPLORATORY DRAFT
Normative Scope: design exploration; no code changes or commits
Related Tasks: `260825-visible-transcript-turn-ids`, `260927-state-step-history-projections`, `260929-state-sequence-inference-affordance`

## 1. Problem Context: Beyond Ordinal Slugs

When `STATE/1`, `STATE/2`, and `--infer-from STATE/1` were introduced, the `/n`
suffix functioned as a minimal ordinal qualifier to distinguish sequential state
snapshots in a multi-state transcript.

However, treating `/n` as the only canonical decorator would artificially
narrow what a decorator can be. In TOAS, the core design split is:
- `session.md` is the user-controlled, editor-facing working surface;
- `events.jsonl` is the append-only, durable graph history;
- Model inference runs over an assembled, horizonal message packet (`llm-input`).

A **transcript decorator** is a zero-token-overhead lens that surfaces durable
graph facts directly on the working transcript. It makes underlying graph
truths visible and addressable for human operators and editor tooling (like Vim)
without leaking metadata tokens into model inference or distorting prompt
context.

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
pairings (`clever-curie`, `bold-bohr`, `calm-cedar`, `brisk-fox`) provide
collision-resistant handles derived deterministically from the underlying hash.
- Hashing `evt_7ed5e9...` into a 2-word phrase from a small curated dictionary
  (e.g., 256 adjectives x 256 nouns = 65,536 combinations) produces names that:
  1. are deterministic and stable across sessions;
  2. roll off the tongue effortlessly;
  3. are distinct and memorable in conversation or notes.

#### Hybrid Syntax
Where technical precision and human memory meet, a hybrid decorator can pair
the mnemonic handle with an abbreviated hash:
```markdown
## TOAS:STATE/bravo [e:8f3a]
## TOAS:ASSISTANT [bold-bohr e:9c12]
```
The operator talks about and addresses `bravo` or `bold-bohr`, while tools and
scripts can still resolve the exact `8f3a` commit hash.

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
- **Disjoint Namespaces Without Punctuation Clutter**: Because each branch owns
  an entire cohesive sibling sequence, steps on Branch A (`titan`, `enceladus`)
  can never collide with steps on Branch B (`fluorine`, `chlorine`), without
  requiring ugly path separators like `branch_1/step_2`.
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
| **Tool Results (`RESULT` blocks)** | ````python block_id=ib_calm_cedar```` | **High Clash Prevention & Concrete Fact**. Empirical external observations. | Deterministic adjective-noun pairs (`calm-cedar`) or gem/mineral nouns (`jade`, `cobalt`), paired with replay-safe block hashes. |

### Where Order Is Useful vs. Where Clash Prevention Dominates

- **Where Order Dominates**:
  In `STATE` milestones and conversational turns, the human mind cares deeply about
  *before* and *after*. Using sequential systems (NATO, Elements) directly serves
  reasoning about causality and state history.
- **Where Clash Prevention Dominates**:
  In `RESULT` blocks and external tool outputs, multiple independent artifacts
  are emitted concurrently. Strict linear order is less meaningful than absolute
  unambiguous reference. Here, high-entropy adjective-noun pairings or distinct
  category nouns (e.g., minerals: `amber`, `cobalt`, `quartz`) prevent clashes
  when referencing blocks across distant turns (`(ref: quartz)`).
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
| **Identity & Handle** | Sequence name (`bravo`), hash alias (`bold-bohr`), or short hash (`id:8f3a`) | Unique identity for targeting via `--infer-from` or `/jump`. |
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
This naturally supports:
```markdown
## TOAS:STATE/bravo [id:8f3a t:09:14:22 key:true]
## TOAS:ASSISTANT [bold-bohr dur:1.8s]
## TOAS:STATE-DIFF/charlie-hydrogen [parent:bravo delta:d_02]
```
- **Pros**: Zero vertical whitespace overhead; stays on the single `## TOAS:...` header line;
  trivially parsed into `role`, `qualifier` (`bravo`), and structured attribute map.
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

### 1. Emission (Write-Time)
When `toas step` executes a turn or emits consequence blocks to `stdout` (or streams
into Vim via `on_projection_delta`), it formats the header using the active decoration
level, embedding the sequence handle and durable event link.

### 2. User Editing And Reconciliation (Read-Time)
What happens when the operator edits a decorated turn?
- If the operator edits the body of `## TOAS:STATE/bravo [id:8f3a]`, the runtime
  detects that the body has changed relative to event `8f3a`.
- The decorator `[id:8f3a]` acts as the explicit **provenance anchor**: it tells the
  runtime exactly which durable snapshot the user started modifying, turning an
  in-place edit into an unambiguous branch from `8f3a`.
- The next step produces a new turn (e.g. `STATE/bravo-hydrogen` or `STATE/charlie`)
  without overwriting or corrupting `bravo`.

### 3. Operational Addressing
Mnemonic decorators become first-class CLI and slash-command arguments:
- `toas step --infer-from bravo`
- `toas step --infer-from charlie-helium`
- `toas diff alpha bravo`
- `/jump bold-bohr`
Because `bravo` and `charlie-helium` roll off the tongue and fit the auditory loop,
the operator can type them without copying and pasting hex strings.

### 4. The Strict LLM-Inert Invariant
At prompt construction time (`llm-input` or `_run_state_step` request assembly):
- The parser extracts the pure role and content.
- All decorator qualifiers, attributes, and brackets are stripped.
- The model receives only clean message semantics.
- Exposing deep graph provenance to the human operator has **zero token cost**
  and **zero prompt drift risk**.

## 9. Open Exploration Questions

1. **User Configuration Mechanics**:
   - Should `sequence_domain` be configured under `/config set transcript.sequence_domain elements`?
   - Should custom user sequences be allowed (e.g. passing a custom list in `.toas/config.yaml`)?
2. **Lane Graduation Threshold**:
   - Under what condition does `charlie-lithium` drop the `charlie-` prefix?
     Is it after a fixed number of branch turns (e.g. 2 steps), when explicitly
     promoted via an operator gesture (e.g. `/focus`), or configurable?
3. **Namespace Separation for Types**:
   - Should different entity types have hard-coded vocabulary domains (e.g. `STATE`
     always uses Elements/NATO, `RESULT` always uses Minerals/Adjective-Noun) to
     prevent cross-type collisions automatically?
4. **Relationship to Open Tasks**:
   - `260825-visible-transcript-turn-ids`: Generalizes from bare turn IDs to this rich
     decorator system.
   - `260927-state-step-history-projections`: Stage 2 "Key states" can designate key
     anchors via decorators (`key:true` or dedicated milestone names).

