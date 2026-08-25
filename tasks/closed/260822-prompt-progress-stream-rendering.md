Filed as: 260822-prompt-progress-stream-rendering
FKA:
AKA: prompt progress streaming; early stream policy header; Vim progress lane
Legacy index:

keywords: surface, implementation, active, correctness, stream, async, watch

# Prompt Progress Stream Rendering

## Objective

Keep prompt-progress events visible while the model is still processing the
prompt, including the stream-policy header that explains whether thinking and
prompt progress are enabled.

## Acceptance Criteria

- A prompt-progress-only watch update promotes the run to the LLM display kind.
- The stream-policy header and current prompt-progress line render before an
  answer or reasoning event arrives.
- Prompt progress remains suppressed when its stream policy is disabled.
- The focused Vim regression fixture continues to cover prompt progress before
  terminal completion; the run-kind classification is covered at the owning
  event-processing seam.

## Completion Evidence

- Focused Vim fixture passes: `streaming_prompt_progress_midrun_visibility.vader`.
- Full Python suite passes: `2877 passed, 9 deselected` with 100% coverage.

## Resolution

Prompt-progress events were metadata-only, so the Vim event projector did not
promote the run from the generic `run` display kind to `llm` until answer or
reasoning text arrived. The projector now promotes the kind as soon as it sees
the `llm_prompt_progress` lane, allowing the existing header and progress
rendering to update during prompt processing.
