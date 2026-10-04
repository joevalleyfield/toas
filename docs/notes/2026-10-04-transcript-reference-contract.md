# Transcript Reference And Working-Context Naming Contract

Status: Proposed normative contract (2026-10-04)
Related Design Note: `docs/notes/2026-10-04-transcript-decorators.md`
Parent Task: `tasks/open/260825-visible-transcript-turn-ids.md`

## 1. Contract in Brief

This document establishes the minimal normative contract for human-facing turn
names and in-transcript cross-turn references (`[[handle]]`).

The core architecture rests on three distinct layers:
1. **Durable Substrate (`events.jsonl`)**: Append-only graph of canonical event
   IDs (`evt_...`) and inert result block IDs (`ib_...`). History is immutable.
2. **Working Presentation Surface (`session.md`)**: Human-facing working
   transcript where turns carry memorable handles (`[[bravo]]`, `[[titan]]`) and
   prose can reference prior turns using wiki-link syntax (`[[alpha]]`).
3. **Inference Packet Assembly (`llm-input`)**: The model-facing message horizonal
   packet. References are translated to stable model-facing turn IDs or re-include
   omitted content, preserving prefix-cache stability.

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
   `session.md` and durable history alone governs graph branching. Turn names
   and reference labels follow the working text; they do not dictate graph
   parentage or override LCP diffs.
3. **Contextual Scope**: Human names belong to an active working context
   (session transcript). They are not required to be globally unique across all
   historical sessions in `events.jsonl`.
4. **Semantic Reference Truth**: Unlike decorative heading qualifiers (which may
   be omitted from model input), an explicit in-prose reference (`[[handle]]`)
   is a semantic speech act. The runtime must either translate it to a
   model-identifiable turn or re-include the referenced content into the
   inference packet.
5. **Prompt-Cache Stability**: Model-facing turn identification must not
   retroactively mutate earlier prompt headings upon reference, which would
   invalidate backend KV-caches. Model packets default to stable, always-present
   turn indexing (`[t:1]`, `[t:2]`).

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
  - cli_symbol_table: [[cobalt]]
```
or inside inline text: `(ref: [[cobalt]])`.

### D. Literal Boundaries And Escaping
To prevent accidental reference resolution:
1. **Backslash Escaping**: `\[\[not-a-turn\]\]` is parsed as literal characters
   `[[not-a-turn]]` and excluded from reference resolution.
2. **Code Spans and Fenced Blocks**: Any `[[...]]` occurring inside inline code
   spans (`` `[[foo]]` ``) or fenced code blocks (``` `...` ```) is strictly
   inert and never parsed as a reference.
3. **No Bare Word Interception**: Ordinary prose words (e.g. "bravo", "delta")
   are never treated as turn references. Only explicit `[[...]]` forms are
   resolved.

---

## 4. Working-Context Resolution And LCP

### A. Resolution Table Construction
When `session.md` is parsed:
1. The parser walks turns in document order.
2. For each turn definition (`## TOAS:<ROLE> [[handle]]`), the runtime binds
   `handle` to that turn's position and, once reconciled, to its canonical event
   ID (`evt_id`).
3. For each inert block (`handle=name`), `name` is bound to the `block_id`.
4. If duplicate handles appear within the same transcript (e.g. from copy-pasting
   a block), the runtime binds references to the **nearest preceding definition**
   in document order, and emits a diagnostic warning.

### B. LCP Reconciliation Under Editing
When an operator edits a named turn in `session.md`:
1. The transcript parser compares the modified text against durable history.
2. The Longest Common Prefix (LCP) determines the fork point.
3. The edited turn is committed as a **new event** branching from the LCP parent.
4. The edited turn retains its handle `[[handle]]` in the active buffer.
5. The historical event that previously held that position remains in
   `events.jsonl` under its immutable event ID.

---

## 5. Inference Packet Assembly Rules

When constructing `llm-input` for model execution, references are handled
according to the active inference profile:

### Profile 1: Full Transcript Packet (Conversational & Multi-Turn)
In a full transcript packet where earlier turns are present in the context:
1. **Turn Headings**: Every turn heading receives a monotonic, stable model index:
   `## TOAS:USER [t:2]` or `## TOAS:USER [evt_01j7b2]`.
2. **Reference Translation**: In-prose references `[[alpha]]` are translated to
   their corresponding model identifier:
   `"Reconsider [[alpha]]"` $\to$ `"Reconsider [t:1]"`.
3. **Cache Invariant**: Because every turn receives `[t:N]` from its inception,
   referencing `[t:1]` in turn 4 does not alter the heading or body of turn 1,
   preserving prompt-cache / KV-cache prefixes.

### Profile 2: Condensed State Packet (Horizon-Bounded)
In a compressed state step where older conversational turns or tool results have
scrolled out of the context window:
1. **Target Inspection**: The packet builder checks whether the resolved target
   event or inert block is included in the current packet.
2. **Content Re-Inclusion**:
   - If the target is omitted from the horizon, the runtime fetches its content
     from durable history (`events.jsonl` or inert block store) and injects it
     directly into the packet's reference context:
     ```markdown
     observations:
       - cli_symbol_table:
     ```python block_id=ib_9a4f
     src/toas/cli.py
         436: def main():
     ```
     ```
3. **No Dangling Pointers**: The runtime never emits a bare reference ID to the
   model without either ensuring the turn is in the context or re-including its
   substantive content.

---

## 6. Error Handling And Diagnostics

| Condition | Runtime Behavior | Operator Feedback |
| :--- | :--- | :--- |
| **Unresolved Reference** (`[[unknown]]`) | Retains literal `[[unknown]]` in model input. Does not halt execution. | Warning emitted in CLI/daemon status: `warning: unresolved reference '[[unknown]]' in turn delta`. |
| **Duplicate Definition** (two turns named `[[bravo]]`) | Nearest preceding definition wins. | Warning emitted: `warning: duplicate turn handle '[[bravo]]'; resolving to nearest preceding turn`. |
| **Malformed Handle** (`[[has spaces]]` or `[[special#char]]`) | If it contains a pipe `|`, parses `target|display`. Otherwise treated as literal text, not a reference. | No error; treated as standard markdown prose. |
| **Circular State Reference** | Detected during packet expansion. Deep expansion halts at depth 1. | Diagnostic logged; circular reference emitted by ID without infinite recursion. |

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
