# State-Transition Step Architecture and History Projections

Status: DURABLE ARCHITECTURE & OPERATOR SPECIFICATION
Normative Scope: State-step operator model, turn grammar, and projection geometry
Related Documents:
- Runtime Direction: `docs/runtime-direction.md`
- Runtime Ownership: `docs/runtime-ownership.md`
- Design Notes: `docs/notes/2026-10-04-state-history-projection-geometry.md`
- Requirements: `tasks/open/260926-state-step-requirements.md`

---

## 1. Overview and Purpose

TOAS provides a **state-transition step** (`toas step` over state transcripts)
that enables operator-controlled, structured state progression across repeated
model inference and tool consequence layers.

Unlike conversational chat loops, state-step centers on an evolving, explicit
structured state object (e.g. goals, progress, blockers, structured notes)
surrounded by strict durability, projection, and repair semantics.

### Three-Layer Architecture

1. **User Working Transcript (`session.md`)**:
   Authoritative for the human operator. The operator edits states, toggles
   milestone tags, and guides actions directly in their text editor.
2. **Append-Only Durable Log (`events.jsonl`)**:
   Immutable history recording `state_snapshot`, `state_diff`, `state_observation`,
   `state_tool_request`, `state_projection_selection`, and `state_key_designation`
   events. Prior history is never overwritten or mutated.
3. **Model Inference Packets**:
   Strictly decoupled from human-facing history. The model receives a
   compact, state-only packet containing:
   - Effective system instructions and schema definitions.
   - The current horizon state snapshot.
   - The latest compound observation (including batch tool outcomes).
   Prior history turns and alternative projections are not fed to the model,
   keeping token usage bounded and predictable.

---

## 2. Turn Grammar and Vector Spelling

State transcripts distinguish static **nodes** ($V$) from directed transition
**vectors / edges** ($E$).

### A. State Nodes ($V$)

A state turn represents a static point in state space:

```markdown
## TOAS:STATE [[alpha]]

state:
  goal: "Implement SQLite indexing"
  progress: "Migration applied"
  blockers: []
```

- **Node Handles**: `[[alpha]]`, `[[bravo]]`, etc. identify state snapshots.
  Numeric identifiers (`STATE/1`, `STATE/2`) remain supported for backward
  compatibility.
- **Milestone Trailers**: Operators designate key milestones using attribute
  trailers:
  ```markdown
  ## TOAS:STATE [[bravo]] [key:true]
  ```

### B. Single-Step Transition Vectors ($E$)

A state diff turn represents an individual directed transition from a source
state to a target state:

```markdown
## TOAS:STATE-DIFF [[alpha->bravo]]

state_patch:
  progress: "Migration applied"
```

- **Vector Syntax**: `[[alpha->bravo]]` explicitly identifies `alpha` as the
  source state and `bravo` as the target state.
- Unambiguous syntax prevents confusion between state nodes and diff edges.

### C. Cumulative Transition Vectors ($E_{\text{cumul}}$)

When multiple intermediate steps are summarized between key milestones, the
vector syntax expresses the full span:

```markdown
## TOAS:STATE-DIFF [[alpha->delta]]

state_patch:
  progress: "Migration applied, indices built, verified green"
```

- Clearly denotes a multi-step delta spanning from `alpha` to `delta`.

---

## 3. The 3x3 Cartesian Projection Matrix

Projections are parameterized across two orthogonal axes, fully grounded in an
initial genesis state anchor ($S_0$, `## TOAS:STATE [[alpha]]`):

1. **Snapshot Frequency (`--snapshots`)**:
   - `all`: Every state turn is rendered as a full snapshot.
   - `key`: Only designated milestone anchors (and genesis $S_0$) are rendered in full.
   - `anchor`: Only the initial genesis state ($S_0$) is rendered in full.
2. **Diff Granularity (`--diffs`)**:
   - `none`: No transition diffs are rendered.
   - `step`: Single-step directed vectors (`[[alpha->bravo]]`) are rendered.
   - `cumulative`: Multi-step cumulative vectors (`[[alpha->delta]]`) are rendered.

### The Matrix

| Snapshots \ Diffs | `none` | `step` (`[[a->b]]`) | `cumulative` (`[[a->c]]`) |
| :--- | :--- | :--- | :--- |
| **`all`** | **Pure Snapshots**<br>$S_0, S_1, S_2$ | **Full Redundancy**<br>$S_0 \to D_{0\to 1} \to S_1 \to D_{1\to 2} \to S_2$ | *(Redundant with step)* |
| **`key`** | **Key Milestones Only**<br>$S_0, S_2(\text{key})$ | **Key States + Step Diffs**<br>$S_0 \to D_{0\to 1} \to D_{1\to 2} \to S_2(\text{key})$ | **Key States + Cumul Diffs**<br>$S_0 \to D_{0\to 2} \to S_2(\text{key})$ |
| **`anchor`** | **Genesis Anchor**<br>$S_0$ | **Anchor + All Diffs**<br>$S_0 \to D_{0\to 1} \to D_{1\to 2}$ | **Total Run Delta**<br>$S_0 \to D_{0\to N}$ |

### Ergonomic Projection Aliases

For day-to-day CLI and transcript usage, standard aliases map to canonical coordinate pairs:

| Alias | Canonical Coordinates | Purpose |
| :--- | :--- | :--- |
| `snapshots` | `snapshots=all, diffs=none` | Sequential state history without patch noise. |
| `redundant` | `snapshots=all, diffs=step` | Primary audit & verification surface: alternating states and patches. |
| `diffs` | `snapshots=anchor, diffs=step` | Grounded patch stream: base state plus sequential step diffs. |
| `milestones` | `snapshots=key, diffs=step` | Milestone narrative: step diffs between major checkpoints. |
| `delta` | `snapshots=anchor, diffs=cumulative` | Net change summary: genesis anchor plus total cumulative delta. |

---

## 4. Operator Workflow and In-Place Switching

### Inspecting Projections

Use `toas transcript` to view the session projected through any lens:

```bash
toas transcript --projection=milestones
toas transcript --snapshots=key --diffs=cumulative
```

### In-Place Switching via Shell Redirection

In keeping with TOAS's Unix-first architecture, `session.md` is updated by
redirecting the projection back to the working transcript:

```bash
toas transcript --projection=milestones > .toas/session.md
toas transcript --projection=redundant > .toas/session.md
```

### Persisting Projection Preferences

To durably remember the preferred projection for subsequent steps or exports:

```bash
toas transcript --projection=milestones --record
```

This appends a `state_projection_selection` record to `events.jsonl`.

---

## 5. Milestone Designation and Zero-Inference `/sync`

### Marking Milestones in the Editor

The operator marks milestones by adding `[key:true]` to state headers in `session.md`:

```markdown
## TOAS:STATE [[alpha]]

## TOAS:STATE [[bravo]] [key:true]

## TOAS:STATE [[charlie]]
```

- **LCP Invariance**: Presentation annotations and attribute trailers on headings
  are not operands of Longest Common Prefix (LCP) content matching. Toggling
  `[key:true]` on earlier headings does not cause history divergence or branch
  forking.

### The `/sync` Control Directive

Because a state frontier without trailing user turns will default to advancing
the state via model inference, the operator uses `/sync` at the frontier to
update metadata without token burn:

```markdown
## TOAS:STATE [[delta]]

## USER
/sync
```

When `toas step` executes:
1. Detects `/sync` at the frontier.
2. Scans all state headers in the transcript and persists updated milestone
   tags to `events.jsonl` via `state_key_designation` records.
3. Strips `/sync` from the transcript.
4. Exits with `[OK] synchronized transcript state` with **zero model inference**.

---

## 6. Execution Lifecycle and Invariants

1. **Patch First**: When the model proposes a state transition, the state patch
   is applied and recorded immediately. Proposed tool requests (`pending_tools`)
   are recorded as pending.
2. **Explicit Tool Stepping**: Pending tool calls do not execute automatically.
   The operator inspects them and runs `toas step` to execute the batch through
   TOAS's standard capability and permission engine.
3. **Compound Observations**: Tool results are formatted as inert output blocks
   and incorporated into the next compound observation.
4. **Authoritative Transcript**: If the operator manually edits the current state
   in `session.md`, that edited state is authoritative for the next step. Durable
   records are historical evidence, not an override over human edits.
