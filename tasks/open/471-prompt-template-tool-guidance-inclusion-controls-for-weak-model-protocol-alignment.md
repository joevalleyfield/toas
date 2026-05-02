# 471 Prompt/template tool-guidance inclusion controls for weak-model protocol alignment

## Objective
Add first-class prompt/template affordances that can include full or filtered tool/callable guidance (for example `/help tools`-equivalent slices) without requiring handcrafted operator prose each run.

## Why
Recent scaffolded gemma4 spike showed that `/prompt dynamic/capabilities/...` + `/help tools` in transcript is still insufficient for reliable callable-protocol conformance. Operators currently need manual protocol coaching, which increases cognitive load and reduces reproducibility.

## Scope
In scope:
- define reusable inclusion controls for prompt composition (dynamic prompt/template path)
- support full tools guidance and filtered subsets (by topic/profile/tool family)
- make inclusion available from operator-native affordances (`/prompt` and/or `/config` driven template shaping)
- add tests proving deterministic rendering and subset filtering behavior

Out of scope:
- model-specific finetuning behavior
- changing core callable schema itself

## Acceptance criteria
- operator can request a prompt/template render that includes tool guidance without manual prose
- filtered inclusion modes exist (at least one subset mode) and are deterministic
- tests cover inclusion on/off and subset selection
- docs/help mention how to invoke this in live operator workflows

## Notes
- Primary consumer: acceptance/repro spikes where weak model must follow callable protocol repeatedly.
- Related: `469` acceptance epic, `470` operator-api migration, `345` docs/capability surface clarity.

## Loop Findings (2026-05-02)
- Loop 1 artifact: `docs/acceptance/spikes/471-loop1-shape-contract-session.md`
- Adding an explicit response-shape contract (prose-only vs prose+yaml vs yaml-only, and no prose inside payload args) improved drift behavior.
- Observed output became `prose + YAML ops` with executable payloads, but remained low on repo-grounding quality (broad discovery ops instead of targeted edit path).
- Immediate implication: inclusion controls should pair callable-shape reminders with repo-grounding scaffolds (likely narrowed tool-guidance subsets and concrete first-discovery patterns).
