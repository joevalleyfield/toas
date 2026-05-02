# Help Config YAML Prompt Exploration Notes

## Setup
- canonical append workflow: `toas step >> session.md`
- baseline snapshot: pre-`/help config` support (`35dd4d8`)
- model selection in-session: `/config set llm.model gemma4`

## Iterative prompt path used
1. `/prompts`
2. `/prompts session-start`
3. `/prompts dynamic/capabilities`
4. `/prompt dynamic/capabilities/overview_v1`
5. `/prompt dynamic/capabilities/repo-work_v1`
6. `/help tools`
7. implementation request with explicit YAML requirement

## Outcome
- final assistant response switched to YAML-callable shape (no freeform prose-only reply).
- returned operations were still imperfect for direct execution (used `shell_script` then `search` rather than direct targeted edits), but protocol conformance improved materially.

## Signal
1. iterative TOAS-native prompt browsing materially improved protocol alignment for this weak-model path.
2. `/prompt dynamic/capabilities/repo-work_v1` + `/help tools` appear to be high-value context pairings.
3. this supports productizing a reusable prompt/template inclusion control (task `471`) so operators do not manually reconstruct this sequence.
