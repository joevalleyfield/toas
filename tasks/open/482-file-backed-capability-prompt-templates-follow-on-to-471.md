# 482 File-Backed Capability Prompt Templates (Follow-on To 471)

## Objective
Complete the prompt/template migration by moving capability prompt template prose out of `src/toas/capability_prompts.py` and into file-backed prompt assets, while keeping runtime population/interpolation in code.

## Why
Task `471` landed deterministic tool-guidance inclusion controls and bootstrap wiring, but dynamic capability prompts still carry substantial hardcoded template text in Python. That makes editing prompt language harder, increases code churn for wording-only changes, and weakens the explicit prompt-library model.

## Scope
In scope:
- move capability prompt body templates for:
  - `dynamic/capabilities/overview_v1`
  - `dynamic/capabilities/repo-work_v1`
  - `dynamic/capabilities/start-here_v1`
  into file-backed assets under `src/toas/prompts/...`
- keep runtime-driven population in code (tool registry, allowed-shell list, profile/hidden-tool filtering, policy avoid-terms)
- preserve rendered behavior and compatibility for existing dynamic prompt refs
- update tests to validate file-backed template usage + interpolation outputs

Out of scope:
- changing operator-visible prompt refs
- redesigning capability wording beyond minimal migration-safe edits
- removing dynamic renderers entirely where runtime data insertion is still required

## Plan
1. Add file-backed template assets for the three capability prompt refs (with metadata + placeholders)
2. Refactor `capability_prompts.py` to load template bodies and populate placeholders
3. Keep `prompts.py` dynamic ref mapping stable, but route through file-backed template-backed render path
4. Update/add tests in `tests/test_prompts.py` (and any focused module tests) for:
   - template load path
   - interpolation correctness
   - profile/hidden-tools filtering parity
5. Run full test suite and fix regressions

## Acceptance Criteria
- No substantial hardcoded template prose remains in `capability_prompts.py`
- The three `dynamic/capabilities/*` refs render from file-backed templates
- Existing behavior for profile/hidden-tool/policy interpolation remains correct
- Tests clearly cover template-backed rendering semantics
- `uv run pytest` passes

## Related
- `471` prompt/template tool-guidance inclusion controls
- `475` edit-mode guidance/template refinement follow-up
- `345` docs/capability surface clarity umbrella

## Progress
- Opened as follow-on after confirming `dynamic/capabilities/*` still render via hardcoded template prose in `capability_prompts.py`.
