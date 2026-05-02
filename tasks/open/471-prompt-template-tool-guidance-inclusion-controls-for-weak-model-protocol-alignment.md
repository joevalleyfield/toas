# 471 Prompt/template tool-guidance inclusion controls for weak-model protocol alignment

## Objective
Add first-class prompt/template affordances that can include full or filtered tool/callable guidance (for example `/help tools`-equivalent slices) without requiring handcrafted operator prose each run, so routine operator workflows start with the right callable shape already present.

## Why
Recent scaffolded gemma4 spike showed that `/prompt dynamic/capabilities/...` + `/help tools` in transcript is still insufficient for reliable callable-protocol conformance. Operators currently need manual protocol coaching, which increases cognitive load and reduces reproducibility.
The same spike also showed avoidable tool-call back-and-forth for routine setup context that is almost always required; proactively projecting compact guidance slices should reduce that churn without bloating context.

## Scope
In scope:
- define reusable inclusion controls for prompt composition (dynamic prompt/template path)
- support full tools guidance and filtered subsets (by topic/profile/tool family)
- make inclusion available from operator-native affordances (`/prompt` and/or `/config` driven template shaping)
- add tests proving deterministic rendering and subset filtering behavior
- support proactive guidance presets for common first-move needs (shape/protocol reminders and bounded discovery scaffolds) so operators do not have to repeatedly fetch the same setup context

Out of scope:
- model-specific finetuning behavior
- changing core callable schema itself

## Acceptance criteria
- operator can request a prompt/template render that includes tool guidance without manual prose
- filtered inclusion modes exist (at least one subset mode) and are deterministic
- tests cover inclusion on/off and subset selection
- docs/help mention how to invoke this in live operator workflows
- guidance controls can provide compact, proactively useful first-move scaffolding that lowers repeated discovery/tool-call overhead for common workflows

## Notes
- Primary consumer: acceptance/repro spikes where weak model must follow callable protocol repeatedly.
- Related: `469` acceptance epic, `470` operator-api migration, `345` docs/capability surface clarity.
- Non-goal clarification: this task should not suppress legitimate repo discovery; it should make that discovery cleaner and more efficient by front-loading likely-needed callable guidance in compact form.

## Loop Findings (2026-05-02)
- Loop 1 artifact: `docs/acceptance/spikes/471-loop1-shape-contract-session.md`
- Adding an explicit response-shape contract (prose-only vs prose+yaml vs yaml-only, and no prose inside payload args) improved drift behavior.
- Observed output became `prose + YAML ops` with executable payloads, but remained low on repo-grounding quality (broad discovery ops instead of targeted edit path).
- Immediate implication: inclusion controls should pair callable-shape reminders with repo-grounding scaffolds (likely narrowed tool-guidance subsets and concrete first-discovery patterns).

## Progress
- Landed first reusable inclusion-control slice via prompt constraints:
  - added `tools-guidance-core`, `tools-guidance-repo-work`, and `tools-guidance-full` shared constraint assets
  - wired shorthand constraint aliases in prompt composer resolution
  - added deterministic tests proving `load_prompt_ref(..., constraints=[...])` includes expected guidance content for each new subset
- Landed operator-surface discoverability follow-on:
  - `/help config` now advertises the new `tools-guidance-*` prompt constraints with compact intent descriptions
  - regression coverage added to assert help-surface presence for those controls
