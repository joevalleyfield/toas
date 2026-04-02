## Goal

Add dynamic, user-insertable prompt assets that truthfully advertise the capabilities available in the current TOAS runtime.

## Scope

- generate prompt text from live runtime introspection rather than static files alone
- make those prompts explicitly selectable by the user
- advertise actual capabilities and limits, not aspirational ones

## Intended Inputs

- live tool registry contents
- relevant CLI/runtime capabilities
- prompt-library access surfaces
- backend-policy or action-lane limits when useful to mention

## Intended Outputs

- one or more dynamic prompts that a user can choose to insert into the transcript
- basic browsing/listing support so users can discover these capability prompts

## Constraints

- prompts must be explicit library material, not hidden runtime injection
- advertised capabilities must reflect current runtime truth
- prompts should be compact and useful, not exhaustive dumps
- prompts should include important limits where omission would mislead

## Non-Goals

- no static hand-maintained capability lists pretending to be dynamic
- no silent capability advertisement to the model
- no broad autonomous-agent claims beyond the current runtime surface

## Done When

- TOAS can render at least one truthful dynamic capability-advertisement prompt
- the prompt content is derived from current runtime state
- users can discover and explicitly choose those prompts
