Filed as: 261030-post-generation-yaml-canonicalization
FKA:
AKA: post-generation yaml canonicalization; heal at birth; yaml snap to grid; assistant yaml normalization
Legacy index:

keywords: runtime, step, yaml, canonicalization, healing, vim, undojoin, session

Parent:
Depends on: 261030-yaml-replace-block-indent-healing, 261030-vim-streaming-undojoin-collapse
Blocks:
Blocked by:
Related: 261030-yaml-replace-block-indent-healing, 261030-vim-streaming-undojoin-collapse

# Post-Generation YAML Canonicalization at Generation Boundary

Canonicalize assistant YAML completion blocks at birth before placing them into the working
transcript (`session.md`), while preserving raw generation output in durable history (`events.jsonl`)
and allowing a single Vim undo (`u`) to revert back to raw streamed output.

## Current Reality

1. When an LLM completes an assistant generation with malformed or sloppy YAML (e.g. broken
   `replace_block` indents, sibling lines, unindented scalar lines), the raw malformed text is
   streamed and finalized directly into `session.md`.
2. Although `frontier_resolution.py` now recovers callable candidates using `heal_candidate_yaml()`,
   the transcript in `session.md` remains syntactically malformed unless the operator manually edits it.
   Future model turns that read `session.md` observe the sloppy prior YAML rather than clean syntax.
3. Durable history (`events.jsonl`) records `llm_call` records with `response_content`, and
   message events with `content`.
4. In Vim, streaming updates are collapsed into a single undo block via `undojoin`, but terminal
   finalization does not yet explicitly distinguish raw streamed output from post-processed
   canonicalized text in the undo tree.

## Desired Reality

1. A completion helper `heal_assistant_completion(content: str) -> str` scans assistant content
   for ````yaml ... ```` code blocks. If any block fails strict parsing or can be healed to valid
   canonical YAML via `heal_candidate_yaml()`, the fence content in the assistant completion is
   replaced with the canonical YAML.
2. In `step_generation_runtime.py`, the assistant message node `content` written to session/transcript
   receives the canonicalized text, while `model_call["response_content"]` continues to record the
   raw unadulterated model response in `events.jsonl` for forensic truth.
3. When streamed in Vim or via RPC/daemon, the terminal finalization step swaps the run region with
   the canonicalized text. If the canonical text differs from the streamed text, Vim creates a new
   undo step so that pressing `u` once reverts to the raw streamed model output, and pressing `u` a
   second time reverts back to the pre-run state.
4. All unit tests and suite checks pass with 100% statement coverage.

## Acceptance Criteria

1. `heal_assistant_completion(content: str) -> str` in `src/toas/runtime/yaml_healing.py`:
   - Safely parses and ignores non-YAML text and valid YAML blocks.
   - Detects malformed YAML blocks within ````yaml ... ```` and ````yaml staged ... ```` fences.
   - Replaces malformed blocks with healed canonical YAML when `heal_candidate_yaml()` succeeds.
2. `step_generation_runtime.py`:
   - Applies `heal_assistant_completion()` to assistant node content.
   - Preserves raw `result.content` in `model_call["response_content"]`.
   - Completion payloads emitted to listeners reflect the canonicalized completion text.
3. Vim integration:
   - When finalized text differs from streamed text, creates an undo barrier so `u` reverts to
     the raw streamed state.
4. Targeted and full suite coverage passes at 100.00%.
