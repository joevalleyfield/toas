Filed as: 260930-paged-inert-tool-spillover
FKA:
AKA: inert block pagination; tool output spillover; sip tool results
Legacy index:

keywords: runtime, tooling, projection, inert, pagination, affordance

Parent: `260926-state-step-requirements`
Depends on: `260930-strip-payload-from-state-packet`
Related: `260930-state-step-transcript-supremacy`

# Paged Inert Tool Result Spillover And Sipping Affordances

Bound oversized tool outputs in transcripts and state observations using durable inert blocks with pagination affordances so models and operators can sip results rather than swallowing firehoses.

## Context
When models invoke broad tools (e.g. `get_structure`, `code_survey`, recursive searches, or shell commands), they often request more data than can fit comfortably in context. Currently, large outputs are either dumped completely into the transcript/prompt or manually truncated by the operator.
TOAS already possesses the concept of inert blocks with stable `block_id`s (`(ref: ib_...)`), but does not have an innate threshold mechanism to spill large outputs to durable blocks while presenting a bounded preview and pagination/inspection affordances.

## Desired Reality
1. **Render-Time Spillover**:
   When a tool produces output exceeding a threshold (e.g. >40 lines or >4 KB), the transcript receives a compact outcome line, a bounded preview (e.g. lines 1..40), and an explicit handle with remaining line/item counts:
   ```text
   ## RESULT

   [OK] tool_name: summary
   ```text toas-output kind=result block_id=ib_xxx lines=1..40 of 1856
   ... 40 lines ...
   --- [1816 lines remaining in block ib_xxx] ---
   ```
   ```
2. **Durable Indexing**:
   The full content remains durably preserved in `events.jsonl` under `block_id`.
3. **Sipping Affordance**:
   Provide a tool or inspection affordance (e.g. `read_block` or `read_file` with block references) allowing models or operators to retrieve subsequent slices or search within spilled blocks without reloading the entire dump.
4. **Controlled Observation Expansion**:
   State-step packet generation does not unconditionally unroll oversized blocks back into the model prompt when condensed references or previews are present.

## Sub-problems & Design Questions
- Determine optimal threshold boundaries (line count vs. byte size).
- Design the tool affordance for querying spilled blocks (`read_block` vs. virtual URI in `read_file`).
- Ensure operator editing in `session.md` remains authoritative over spilled block previews.
