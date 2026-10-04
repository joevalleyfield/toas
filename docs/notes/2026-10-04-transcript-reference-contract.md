# Transcript Reference And Working-Context Naming Contract

Status: Proposed normative contract (2026-10-04)
Related Design Note: `docs/notes/2026-10-04-transcript-decorators.md`
Parent Task: `tasks/open/260825-visible-transcript-turn-ids.md`

The retained-reference and LCP proposals in section 4 distinguish confirmed
operator intent from proposed mechanics. Surface spelling, binding-record
layout, and inference-profile defaults remain open. No runtime implementation
is established by this document.

## 1. Contract in Brief

This document establishes the minimal normative contract for human-facing turn
names and in-transcript cross-turn references (`[[handle]]`).

The design distinguishes four representations:
1. **Durable Substrate (`events.jsonl`)**: Append-only graph of canonical event
   IDs (`evt_...`) and inert result block IDs (`ib_...`). History is immutable.
2. **Working Presentation Surface (`session.md`)**: Human-facing working
   transcript where turns carry memorable handles (`[[bravo]]`, `[[titan]]`) and
   prose can reference prior turns using wiki-link syntax (`[[alpha]]`).
3. **Reconciliation Comparison Form**: A source-preserving, reference-aware
   form used only to determine the common prefix. It is independent of model
   visibility, result expansion, and prompt-cache policy.
4. **Inference Packet Assembly (`llm-input`)**: The model-facing message packet.
   Resolved references identify included targets or cause omitted content to be
   re-included. Marker emission and cache tradeoffs belong to this projection.

```text
[Human Surface: session.md]
  "Reconsider [[bravo]] before patching."
       │
       ▼ (Working-Context Resolution)
  Canonical Target: evt_01j7b2
       │
       ▼ (Packet Assembly)
[Model Input: llm-input]
  "Reconsider [t:2] before patching." (or content re-inclusion)
```

---

## 2. Invariants

1. **Graph Immutability**: Assigning, changing, or re-theming human handles
   never mutates prior events in `events.jsonl`.
2. **LCP Primacy**: Longest Common Prefix (LCP) reconciliation between
   the working transcript's comparison form and durable history governs graph
   branching. Turn names do not dictate parentage. Reference resolution supplies
   comparison operands; it cannot skip a substantive divergence or choose a
   parent independently of the common prefix.
3. **Contextual Scope**: Human names belong to an active working context
   (session transcript). They are not required to be globally unique across all
   historical sessions in `events.jsonl`.
4. **Semantic Reference Truth**: Unlike decorative heading qualifiers (which may
   be omitted from model input), an explicit in-prose reference (`[[handle]]`)
   is a semantic speech act. The runtime must either translate it to a
   model-identifiable turn or re-include the referenced content into the
   inference packet.
5. **Projection Independence**: Model-facing marker projection is sometimes
   necessary, but its formatting and cleanup are not the LCP comparison form.
   Always-present IDs are a candidate profile for avoiding retroactive prompt
   changes. Their default, spelling, and allocation policy remain open.

---

## 3. Surface Grammar And Literal Boundaries

### A. Turn Definition Markers
Turn definition markers appear on the role heading line:

```markdown
## TOAS:<ROLE> [[handle]]
```
or with backward-compatible trailer/qualifier syntax:
```markdown
## TOAS:<ROLE>/<handle>
```

#### Heading Grammar Rules
1. `handle` is an ASCII identifier: `[a-zA-Z0-9_-]+`.
2. Whitespace is permitted between `## TOAS:<ROLE>` and `[[handle]]`.
3. If both a qualifier and a bracketed handle are present (e.g. `## TOAS:STATE/2 [[beta]]`),
   the bracketed handle takes precedence as the human reference name, while the
   qualifier is preserved as an auxiliary attribute.
4. If an optional attribute trailer is present, it follows the handle:
   `## TOAS:STATE [[bravo]] [key:true]`.

### B. In-Prose Turn References
In user prompts, assistant prose, or state documentation, a reference to an
earlier turn is written using double brackets:

```markdown
Reconsider [[alpha]] before continuing.
```

Optional display alias syntax matches standard wiki-link conventions:
```markdown
As established in [[bravo|the initial SQLite decision]], we require local storage.
```
- The target handle is the substring preceding the first pipe `|`.
- The display text following the pipe is retained for human reading but ignored
  during target resolution.

### C. Inert Result Block Handles
Tool execution results produce inert result blocks (`RESULT` blocks). These blocks
may define an optional human handle alongside their immutable `block_id`:

````markdown
```python block_id=ib_9a4f handle=cobalt
src/toas/cli.py
    436: def main():
```
````

In later turns or state observation blocks, this result may be referenced as:
```yaml
observations:
  - cli_symbol_table: "[[cobalt]]"
```
or inside inline text: `(ref: [[cobalt]])`.

### D. Literal Boundaries And Escaping
To prevent accidental reference resolution:
1. **Backslash Escaping**: `\[\[not-a-turn\]\]` is parsed as literal characters
   `[[not-a-turn]]` and excluded from reference resolution.
2. **Code Spans and Fenced Blocks**: References in ordinary inline code and
   fenced source/result bodies are literal. A typed state envelope needs an
   explicit exception for declared reference-bearing fields, whether its YAML
   is fenced or unfenced. Those field rules remain open; do not activate all
   strings in a state or every YAML fence. The result block's header can define
   a handle while its body remains literal. Quoting a YAML reference is needed
   to preserve its string type, but quoting alone does not activate it.
3. **No Bare Word Interception**: Ordinary prose words (e.g. "bravo", "delta")
   are never treated as turn references. Only explicit `[[...]]` forms are
   resolved.

---

## 4. Working-Context Resolution And LCP

### A. Confirmed Intent And Current Implementation

Human names remain dependable within the working context; canonical IDs retain
historical identity. Editing a named turn can leave its human name unchanged.
A retained reference can remain useful after its definition leaves the visible
transcript. Branching still follows LCP, including when an older named turn is
edited and its unchanged child refers to that turn.

Currently, `transcript._eq` compares role and stripped body text, ignoring the
role marker. The generic parser preserves the original marker separately.
Consequently, heading-only relabeling already leaves this comparison unchanged,
but changing body text from `[[bravo]]` to `[[helium]]` does not. CLI prefix-head
selection, ordinary runtime reconciliation, and state-lineage selection all
use `_lcp`; a future change must keep those consumers consistent.

Model-input cleanup cannot solve that body-reference problem: reconciliation
happens independently of model visibility and inference profile selection.

### B. Retained Binding Behavior — Proposed Contract

There are two distinct inputs to contextual name resolution:

- **Current definitions**: names on preceding turns and result-block headers
  in the working transcript. A turn initially resolves to a local turn position;
  its canonical ID becomes available as the prefix matches or the new suffix
  materializes. A block resolves to its canonical `block_id`.
- **Retained bindings**: a canonical target carried with a still-used reference
  when its defining turn/block is absent. The target includes its kind and
  enough source identity to locate it in the applicable history; journal-local
  IDs must not be treated as globally unique.

For a name-only reference, a current applicable definition resolves against the
current working content. Retained evidence is a fallback when that definition
is absent; it must not silently pin a child to an abandoned revision of a
visible edited turn. A deliberately authored canonical target is a different,
explicit historical reference and retains that target.

The draft's nearest-preceding rule for duplicate current definitions remains
a proposed policy. Retained bindings must not introduce a second silent
shadowing rule: conflicting retained targets require an ambiguity outcome.

Before a projection drops a definition but keeps a use, it must carry the
resolved canonical target into the surviving context. A state operation that
retains or creates such a use must carry its binding too. A manual fragment
containing only `[[cobalt]]`, without its definition or binding, cannot promise
resolution. Do not recover a missing binding by searching the entire journal
for the most recent object once called "cobalt".

Working-context bindings must survive saving, reopening, reconstruction, and
transport to another editor. An editor-local dictionary alone is insufficient.
Two surface alternatives remain open:

1. Keep `[[cobalt]]` and carry a compact binding with the working transcript.
2. Carry the canonical target in the retained reference itself, for example
   `[[ib_...|cobalt]]`, with the familiar name as display text.

These alternatives are not automatically interchangeable for live turn names:
an explicit canonical target pins a revision, while a current name resolves
against the visible turn. Exact surface syntax and how an automatic projection
distinguishes retained evidence from an authored pin need a separate decision.

Historical naming assignments ("was displayed as cobalt") are optional
recognition evidence. They are not the binding of a particular reference use.
Reconstruction should obtain reference targets from durable resolution facts,
not infer them from whichever name happened to be displayed in an old view.

Target resolution and payload availability are separate outcomes. A known
`ib_...` whose body is unavailable is not an unknown name, and a visible body
should remain usable without being replaced by stale archival content.

### C. Comparison Form — Proposed Contract

Parse references into spans while retaining the authored text. The comparison
form contains the role and an ordered sequence of literal text and typed
reference atoms:

```text
Reconsider [[bravo]] before patching.
  -> text("Reconsider ")
     reference(kind=turn, target=<canonical target>)
     text(" before patching.")
```

On each side of the comparison:

- Ordinary text keeps the current exact comparison behavior, including the
  existing outer `.strip()` treatment. No fuzzy matching, whitespace collapse,
  general comment removal, or YAML parse/reserialization equivalence is added.
- Recognized human heading labels and registered machine-generated binding
  decorations are presentation fields. Their name spelling is not an operand.
  This is not permission to delete arbitrary comments or interpret every
  heading attribute as decorative; operational fields keep their own contract.
- A resolved reference compares by target kind and canonical locator, not its
  human label or model-facing `[t:N]` slot. Distinct targets are distinct even
  when their payload text happens to be equal.
- An explicitly authored display description, such as "the initial SQLite
  decision" in `[[bravo|the initial SQLite decision]]`, is retained as authored
  information. Renaming a generated handle and editing a description must not
  be conflated. Its exact surface classification remains part of grammar work.
- Literal/escaped reference-looking text and unresolved spans retain their
  authored spelling. Deleting all `[[...]]` text or replacing every reference
  with one placeholder would conceal real edits and is not valid cleanup.

The form does not contain re-included payloads, model-only headings, reasoning
visibility filtering, CONTROL omission, merged adjacent USER messages, or
profile-specific turn numbers. A profile switch cannot change the LCP result.

### D. Resolve A Prefix Without Assuming The New Branch

The proposed comparison walks each candidate lineage left to right:

1. Parse working definitions and reference spans without assigning speculative
   historical IDs to new turns. Parse retained bindings independently of model
   packet construction.
2. At each position, compare literal text and resolved reference atoms. A live
   reference to an earlier working turn can use the canonical ID established
   by that already-matched prefix. Blocks and explicit retained targets already
   have canonical locators.
3. Stop at the first substantive difference or at a reference whose binding
   cannot be established. An unresolved outcome must not be treated as a match
   merely because the old event has a plausible resolution receipt.
4. Derive the branch parent from that boundary under the existing rewrite laws.
   Materialize the suffix in order, resolving its live references to prefix or
   newly materialized earlier turns. Record final reference targets only after
   those identities are known.

This avoids using future event IDs to calculate the prefix that determines
their parent. A visible edited `bravo` diverges at `bravo`; its later child is
then recreated and resolves its name against the new `bravo`. Retained fallback
evidence cannot pull that child back onto the old branch.

Removing or reordering semantic turns still affects ordinary LCP. Keeping a
reference meaningful does not authorize skipping those turns during comparison.
State-history view changes and explicit bind/anchor semantics retain their own
task boundaries.

### E. Durable Evidence And Reconstruction — Proposed Shape

Keep authored content available. At materialization, store reference-resolution
facts linked to their source turn, identifying each recognized occurrence and
its typed canonical target. A source digest plus spans or typed state-field
locations can prevent a receipt from being applied to unrelated edited text.
Metadata on a new entry or a linked append-only record are possible storage
shapes; record names, schema, and source-locator format remain open. These facts
must not consume message-event numbering or mutate existing records.

The durable comparison form can be reconstructed from authored content and
its verified resolution facts. Re-rendering may change human labels while
carrying the same reference atoms. A resolution receipt describes the recorded
use; it is not a universal name-to-ID table or a parent-selection command.

Legacy entries without declared reference semantics keep the existing literal
comparison. Do not retroactively turn historical wiki-link-like prose into
typed references through a regex sweep. Any legacy adoption needs an explicit,
bounded migration or import rule rather than inferred history mutation.

### F. Required Specimens Before Implementation

| Change or lifecycle case | Expected comparison/resolution result |
| --- | --- |
| Rename heading only | Same comparison form. |
| Re-theme a definition and its uses, preserving targets | Same reference atoms and common prefix. |
| Change only the inference profile or model marker spelling | Same LCP result; model packet may differ. |
| Edit prose around a reference | Divergence at the edited turn. |
| Change a reference to another target with identical content | Divergence at the reference-bearing turn. |
| Edit literal code containing `[[bravo]]` | Ordinary content divergence, not reference reinterpretation. |
| Edit visible `bravo` while its child keeps `[[bravo]]` | Diverge at `bravo`; recreate the child against the new visible turn. |
| Omit a definition but retain the bound use in a selected context | Resolve from carried binding; fetch content only if the packet needs it. Omission itself follows existing reconciliation rules. |
| Reopen a retained-reference transcript | Same target without an editor-local cache. |
| Copy only a name-only use without its definition/binding | Explicit unresolved outcome; no journal-wide alias guessing. |
| Known target, unavailable payload | Report content unavailability separately from name resolution. |

This specifies comparison behavior, not a selected serialization or implemented
cleanup pass. Physical binding form, occurrence schema, literal boundaries in
typed state, legacy adoption, and failure disposition remain open.

---

## 5. Inference Packet Assembly Rules

When constructing `llm-input` for model execution, references are handled
according to the active inference profile:

### Candidate Profile 1: Full Transcript Packet With Always-Present IDs
In a full transcript packet where earlier turns are present in the context:
1. **Turn Headings**: Under this candidate policy, every included turn receives
   stable model-facing identification:
   `## TOAS:USER [t:2]` or `## TOAS:USER [evt_01j7b2]`.
   Index allocation and preservation across projections remain open; these are
   model-facing spellings, not the canonical operands used for LCP.
2. **Reference Translation**: In-prose references `[[alpha]]` are translated to
   their corresponding model identifier:
   `"Reconsider [[alpha]]"` $\to$ `"Reconsider [t:1]"`.
3. **Cache Goal**: With identification present from the turn's first inclusion,
   a later citation need not change that earlier heading. This avoids one cause
   of prefix changes, not all changes or backend cache limitations. An on-demand
   identification policy remains an alternative; no global default is adopted.

### Profile 2: Condensed State Packet (Horizon-Bounded)
In a compressed state step where older conversational turns or tool results have
scrolled out of the context window:
1. **Target Inspection**: The packet builder checks whether the resolved target
   event or inert block is included in the current packet.
2. **Content Re-Inclusion**:
   - Once section 4 resolves the target, if its content is omitted from the
     packet, the runtime obtains the applicable working or historical content
     and includes it in reference context. Retained bindings locate absent
     sources; archival content must not override visible current edits.
     Illustrative packet rendering, not a selected state schema:
     ````markdown
     observations:
       - cli_symbol_table:
     ```python block_id=ib_9a4f
     src/toas/cli.py
         436: def main():
     ```
     ````
3. **No Dangling Pointers**: The runtime never emits a bare reference ID to the
   model without either ensuring the turn is in the context or re-including its
   substantive content.

---

## 6. Error Handling And Diagnostics

| Condition | Runtime Behavior | Operator Feedback |
| :--- | :--- | :--- |
| **Unresolved Reference** (`[[unknown]]`) | Explicit unresolved outcome; no target or comparison equivalence is invented. Whether inference proceeds with visibly unresolved prose or stops remains open. | Diagnostic identifies the source use and missing definition/binding. |
| **Duplicate Definition** (two turns named `[[bravo]]`) | Nearest preceding definition wins. | Warning emitted: `warning: duplicate turn handle '[[bravo]]'; resolving to nearest preceding turn`. |
| **Malformed Handle** (`[[has spaces]]` or `[[special#char]]`) | If it contains a pipe `|`, parses `target|display`. Otherwise treated as literal text, not a reference. | No error; treated as standard markdown prose. |
| **Unavailable Retained Target Content** | Binding resolves, but requested re-inclusion cannot obtain payload. Do not report this as an unknown human name or successful expansion. | Diagnostic names the canonical target and unavailable source. |
| **Conflicting Retained Bindings** | Explicit ambiguity outcome; no journal-wide or editor-cache fallback. | Diagnostic identifies the conflicting bindings. |
| **Circular State Reference** | Explicit expansion outcome without infinite recursion. Depth limits and whether references inside included content expand remain open; no bare ID is claimed to supply missing content. | Diagnostic identifies the cycle or expansion boundary. |

---

## 7. Editor And Tooling Affordances (Informative)

While the reference contract is editor-neutral, it enables powerful optional
integrations:
- **Vimwiki**: Pressing `<CR>` on `[[bravo]]` navigates directly to `## TOAS:... [[bravo]]`.
  Pressing `<C-o>` returns.
- **Omnicompletion**: In insert mode, typing `[[` triggers buffer-local completion
  against known turn handles.
- **CLI Jump**: `toas jump bravo` or `toas diff alpha bravo` resolves human handles
  directly via the active working context table.
