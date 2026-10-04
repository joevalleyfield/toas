# State-History Projection Geometry And Vector Spelling

Status: Proposed design specification (2026-10-04)
Related Documents:
- Design Note: `docs/notes/2026-10-04-transcript-decorators.md`
- Normative Contract: `docs/notes/2026-10-04-transcript-reference-contract.md`
Parent Task: `tasks/open/260927-state-step-history-projections.md`

## 1. Problem Context

In state-step execution, TOAS maintains an evolving structured state across
repeated inference and tool consequence layers.

Earlier proposals described five ad-hoc user-facing state projections:
1. Full state plus every diff
2. States only
3. Diffs only
4. Key states plus diffs
5. Key states plus cumulative diffs

However, examining their concrete spelling revealed two key design flaws:
- **Ungrounded Diffs**: A pure "diffs only" view without an initial base state
  ($S_0$) presents floating patches that neither human nor machine can evaluate.
  Once grounded with $S_0$, it collapses into View 1.
- **Node vs. Edge Ambiguity**: If diffs and states share identical destination
  labels (e.g. `STATE [[bravo]]` vs `STATE-DIFF [[bravo]]`), human references
  confuse the *state snapshot* with the *transition patch*.

By separating states into **nodes** ($V$) and diffs into **vectors / edges** ($E$),
and parameterizing projections across two orthogonal axes, the ad-hoc list
resolves into a clean 3x3 Cartesian product.

---

## 2. Vector Spelling: Nodes vs. Edges

In the working transcript (`session.md`), state entities follow a clear
topological distinction:

### A. State Nodes ($V$)
A state snapshot represents a static point in state space:
```markdown
## TOAS:STATE [[bravo]]
```
Optional milestone markers use attribute trailers:
```markdown
## TOAS:STATE [[alpha]] [key:true]
```

### B. Single-Step Transition Vectors ($E$)
A state diff represents a directed transition from a source state to a target state:
```markdown
## TOAS:STATE-DIFF [[alpha->bravo]]
```
- Source state: `alpha`
- Destination state: `bravo`
- `->` is standard ASCII, easy to type, and unambiguous.

### C. Cumulative Transition Vectors ($E_{\text{cumul}}$)
When a diff summarizes changes across multiple intermediate steps (e.g. spanning
from milestone `alpha` to milestone `delta`), the vector syntax expresses the
exact span without auxiliary flags:
```markdown
## TOAS:STATE-DIFF [[alpha->delta]]
```

### D. Expressive Power in Prose and Navigation
This distinction eliminates ambiguity in human writing and editor jumps:
- Citing a state: *"In [[bravo]], the SQLite foreign keys were enabled."*
- Citing a transition: *"The regression was introduced in [[alpha->bravo]]."*
- Editor Search: Searching `/->bravo` locates the incoming diff; searching
  `/bravo->` locates any outgoing branch.
- Vimwiki: Pressing `<CR>` on `[[alpha->bravo]]` jumps directly to the diff turn.

---

## 3. The 3x3 Cartesian Projection Space

Every valid state projection is fully parameterized by two independent choices:
1. **Snapshot Frequency**: Which states are rendered as full snapshots?
   - `all`: Every state turn is rendered in full.
   - `key`: Only designated milestones (and genesis $S_0$) are rendered in full.
   - `anchor`: Only the initial genesis state ($S_0$) is rendered in full.
2. **Diff Granularity**: How are transitions between states displayed?
   - `none`: No diffs are shown.
   - `step`: Individual step-by-step diffs (`[[a->b]]`) are shown.
   - `cumulative`: Multi-step cumulative diffs (`[[a->c]]`) between key states are shown.

### The Projection Matrix

```text
               Diffs: none            Diffs: step [[a->b]]       Diffs: cumulative [[a->c]]
          ┌─────────────────────────┬──────────────────────────┬─────────────────────────────┐
all       │ Pure Snapshots          │ Full Redundancy          │ (Redundant)                 │
          │ S0, S1, S2              │ S0, D0->1, S1, D1->2, S2 │                             │
          ├─────────────────────────┼──────────────────────────┼─────────────────────────────┤
key       │ Key Milestones Only     │ Key States + Step Diffs  │ Key States + Cumul Diffs    │
          │ S0, S(key)              │ S0, D0->1, D1->2, S2(key)│ S0, D0->2, S2(key)          │
          ├─────────────────────────┼──────────────────────────┼─────────────────────────────┤
anchor    │ Genesis Anchor          │ Anchor + All Diffs       │ Total Run Delta             │
          │ S0                      │ S0, D0->1, D1->2         │ S0, D0->N                   │
          └─────────────────────────┴──────────────────────────┴─────────────────────────────┘
```

### Archetypal Projections

1. **Pure Snapshots (`all`, `none`)**:
   Standard forward progression. Best for conversational reading where each turn
   reflects current total knowledge.
2. **Full Alternating Redundancy (`all`, `step`)**:
   $S_0 \to D_{0\to 1} \to S_1 \to D_{1\to 2} \to S_2$.
   The ultimate **audit and debugging surface**. The operator sees the proposed
   patch (`alpha->bravo`) and immediately below it, the resulting state (`bravo`),
   making drift or application bugs immediately visible without mental arithmetic.
3. **Anchor + All Diffs (`anchor`, `step`)**:
   $S_0 \to D_{0\to 1} \to D_{1\to 2} \to D_{2\to 3}$.
   A lightweight, low-token patch stream anchored at the session start.
4. **Key States + Step Diffs (`key`, `step`)**:
   Shows key milestones in full while tracing intermediate steps as diffs.
5. **Key States + Cumulative Diffs (`key`, `cumulative`)**:
   $S_0 \to D_{0\to 2} \to S_2(\text{key})$.
   High-level executive summary: major architectural milestones connected by
   net delta summaries.
6. **Total Run Delta (`anchor`, `cumulative`)**:
   $S_0 \to D_{0\to N}$.
   Shows initial baseline and the net consequence of the entire session.

---

## 4. CLI And Configuration Interface

Instead of memorizing five arbitrary view names, the CLI and session configuration
expose orthogonal controls alongside intuitive aliases:

### Orthogonal Flags
```bash
toas transcript --snapshots=[all|key|anchor] --diffs=[none|step|cumulative]
```

### Ergonomic Aliases
- `snapshots`  $\implies$ `--snapshots=all --diffs=none`
- `redundant`  $\implies$ `--snapshots=all --diffs=step`
- `diffs`      $\implies$ `--snapshots=anchor --diffs=step`
- `milestones` $\implies$ `--snapshots=key --diffs=cumulative`
- `delta`      $\implies$ `--snapshots=anchor --diffs=cumulative`

---

## 5. Invariants & Guarantees

1. **Mathematical Grounding**: Every projection starts with a grounded state
   anchor ($S_0$). No projection emits floating unanchored diffs.
2. **Reference Stability Across Views**: Changing projection modes changes what
   turns are displayed, but does not alter turn identities. A reference to
   `[[bravo]]` or `[[alpha->bravo]]` points to the exact same historical fact
   regardless of the active projection filter.
3. **Model Request Decoupling**: The model inference packet continues to receive
   only the current state and latest compound observation, entirely independent
   of the operator's chosen transcript projection.
