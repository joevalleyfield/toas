# 682 Review capture_task_thread capability prompt behavior

## Current Reality
The `capture_task_thread` tool is documented in `src/toas/capability_prompts.py` and advertised in `overview_v1.txt`. However, the prompt does not specify the runtime policy/guidelines (e.g. how the agent should react to the `continue` resume directive, how to keep payloads minimal, and how the call acts as a "fork marker" transferring the side thread out of the conversation).

## Desired Reality
The system/capability prompts explicitly instruct the agent on when to call `capture_task_thread` (side threads, blockers, cleanups, missing tests, etc.), how to construct minimal payloads, and how to immediately return to the primary task on receiving `continue` without bloating the conversation context.

## Gap Analysis
We need to integrate the newly defined prompting rules into `overview_v1.txt` or a dedicated tool guidance section.

## Known Facts
- Capability prompts are loaded from txt templates under `src/toas/prompts/dynamic/capabilities/`.

## Assumptions
- Adding these rules to the prompts will dramatically decrease context drift for agents during complex tasks.

## Unknowns
- Whether we need to dynamic-interpolate the rules depending on whether the tool is active or hidden.

## Investigations
- Check how dynamic help/topics are loaded in `src/toas/prompts.py`.

## Models
- Prompt structure detailing: Trigger condition -> Action (`capture_task_thread`) -> Fork rule -> Resume behavior.

## Forecasts
- Proper prompt behavior will improve execution loop speed and success rate.

## Risks
- Bloating the prompt template might cause context overhead for weak models.

## Transformations
- Update `src/toas/prompts/dynamic/capabilities/overview_v1.txt` or create a dedicated instruction template.

## Evidence
- Prompts rendering verified by tests.

## Decisions
- Insert the guidance block directly into the tool instruction template or capability prompts template.

## Open Fronts
- Testing prompt adherence with actual model runs.

## Next Actions
- Edit `overview_v1.txt` to include the execution policy block.
