## Goal

Audit and explicitly retire the three `BackendGenerationPolicy` fields that are stored but never consumed, leaving a clean and honest policy object and a clear documented seam for future wiring.

## Why Now

`preferred_action_formats`, `protocol_prompt_version`, and `entrainment_prompt_version` were added during the backend-adaptive protocol arc (180–183) with the intent of eventually driving prompt selection and action format choices. That wiring was never implemented. They now create false expectations — the fields imply the system does something it doesn't. Retiring them explicitly is cheaper than wiring them and more honest than leaving them.

## Scope

- remove `preferred_action_formats`, `protocol_prompt_version`, and `entrainment_prompt_version` from `BackendGenerationPolicy`
- remove corresponding values from `default_backend_policy()` and `generation_policy_from_config()`
- update any tests that reference these fields
- add a clear comment in `backend_policy.py` (or a note in `docs/`) documenting:
  - what these fields were intended to do (drive prompt version selection and action format guidance)
  - why they were removed (never wired to consumers; false affordance)
  - what would be needed to reintroduce them properly (a prompt-selection mechanism that reads from config and injects or suggests prompts based on backend type)

## Constraints

- no behavioral change — these fields were never consumed, so removal has no runtime effect
- the removal note should be honest about intent, not just mechanical

## Non-Goals

- no actual prompt-selection wiring in this pass
- no new config fields for the retired concepts (that belongs to a future arc when the wiring is real)

## Done When

- `BackendGenerationPolicy` has only `name`, `extra_body`, and `avoid_terms`
- all tests pass
- the seam for future prompt-selection wiring is documented where the fields were removed
