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
- Python suite: 2,857 passed; 20 environment-blocked failures while binding
  Unix/TCP sockets or writing Vim state files in the sandbox.
