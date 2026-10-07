# State Observation Ephemerality And Bounded Persistence

Filed as: 261006-state-observation-ephemerality-and-bounded-persistence
FKA:
AKA: observation persistence; bounded slice references; intentional paging threshold; observation ephemerality
Legacy index:
Parent: `260926-state-step-requirements`
Related: `260930-paged-inert-tool-spillover`; `261004-state-observation-reference-addressing`; `261006-state-step-transcript-protocol-reference-and-overlay`

## Context

In state-step execution, model inference operates over a compact packet consisting of the current state snapshot and the latest compound observation. Unlike conversation transcripts where prior tool outputs remain visible indefinitely across the context window, state observations are strictly single-round-trip ephemeral: once the model steps, the previous observation disappears from model view.

Because foundation models carry a strong training prior from chat transcripts, they frequently fail to recognize that unpersisted observation details vanish. When attempting to retain context, two affordance and policy gaps emerge:
1. **Paging Collision on Intentional Reads**: Unbounded outputs properly spill to scratch files at a strict threshold (~40 lines). However, intentional bounded requests (e.g., `read_file` explicitly asking for 120 lines) collide with the same strict threshold, truncating deliberately requested slices down to 30-line previews.
2. **Slice Bounding on References**: Citing an entire block via `(ref: ib_...)` in state either pulls in a full multi-page block or re-expands only the preview. The model lacks a compact, uniform syntax to curate a specific slice (e.g. `ib_abc:23-85` or `path:start-end`) directly into state artifacts and notes.
3. **Undeclared Ephemerality in Instructions**: `STATE_INSTRUCTIONS` does not currently inform the model that observations are ephemeral, nor does it provide guidance on how to persist facts, curate bounded slices, or query persistent scratch files.

## Objectives

1. **Policy Tuning for Intentional Reads**: Distinguish unbounded exploratory outputs (strict ~40-line spill threshold) from explicit bounded requests (e.g. `read_file` with explicit line bounds), allowing intentional reads a generous ceiling (~500 lines) before triggering spillover, protected by a hard safety brake (~1,000 lines).
2. **Compact Bounded Slice References**: Support `<target>:<start>-<end>` slice addressing across blocks and files alike (e.g., `ib_8f2a1c:23-85`, `src/toas/cli.py:100-145`) during state expansion, cleanly extracting only the curated line range into model input.
3. **Ensure Universal Scratch Addressability**: Verify all tool outputs have an addressable `.toas/scratch/<block_id>.txt` representation so subsequent queries via `read_file` or `grep` operate reliably without missing-file errors.
4. **Instruction Alignment**: Update state instructions to explicitly declare observation ephemerality and guide the model on persistence strategies (summarizing into `state.notes`, pinning bounded slices into `state.artifacts`, and querying scratch files).
5. **Coverage & Validation**: Maintain 100.00% statement test coverage across all test suites.
