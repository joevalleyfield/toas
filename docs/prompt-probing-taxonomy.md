# Prompt Probing Taxonomy

This document sketches a working narrative framework for evaluating prompt behavior against real inference backends.

It is not a single benchmark.
It is a provisional map of failure modes, expectations, and remediation strategies.

## Purpose

TOAS prompt behavior depends on a three-way interaction:
- backend model behavior
- hidden/provider prompt pressure
- visible TOAS prompt assets and runtime flags

The goal of prompt probing is to make this interaction more observable and actionable.

## Validity Horizon

Treat this document as a field note, not a hard doctrine.

- most claims here are hypotheses that need repeated real-world probes
- sections that do not improve decisions should be softened, revised, or removed
- confidence should be proportional to evidence

Current strongest practical signal:
- delegated execution framing (“you suggest, I run if safe, I return output”) is battle-tested in live use and often works where stricter admonition-first approaches fail

## Levels Of Probes

### Level 0: Reachability And Runtime Health

Questions:
- is the endpoint alive?
- is the requested model accepted?
- are timeouts/latency in an expected range?

Signals:
- `/health` status
- `/models` listing
- first-token and total latency ranges

If this fails:
- stop prompt analysis
- fix runtime connectivity/model selection first

### Level 1: Shape Discipline

Questions:
- can the model emit exact requested structural shapes?
- can it avoid extra prose and wrappers?

Signals:
- exact-match checks
- JSON parseability
- YAML fence presence
- leading-text violations

If this fails:
- tighten output contract language
- switch to stricter prompt variant
- reduce optionality in examples
- also test finesse-first phrasing before further hardening:
  - keep structure explicit but non-threatening
  - preserve role clarity and cooperation language
  - avoid language that can trigger “guardrail resistance” in model or overseer prompts
  - prefer incremental nudges over maximal constraint jumps

### Level 2: Vocabulary Collision

Questions:
- which trigger words activate provider-native tool behavior?
- which neutral words stay inside TOAS lane?

Signals:
- provider marker presence (`TOOL_CALL:`)
- action/object lane compliance by wording variant

Observed tendency (often, not guaranteed):
- `tool/tool-call/function` collides more
- `action/operation` collides less

If this fails:
- remove collision-prone terms
- prefer neutral operation vocabulary
- increase entrainment strength

### Level 3: Prompt Variant Robustness

Questions:
- which prompt variants hold under adversarial/hostile system pressure?
- where does each variant degrade first?

Signals:
- pass rates by prompt variant family
- degradation signatures (prose leakage, schema drift, provider markers)

If this fails:
- keep multiple prompt variants
- route by backend profile
- document per-backend “known good” defaults

### Level 4: Runtime Policy Interaction

Questions:
- how do runtime flags alter output reliability?
- does no-thinking materially affect structure and latency?

Signals:
- thinking on/off comparison
- retry/failure class distributions
- trace-mode diagnostics when malformed responses occur

If this fails:
- verify request-shape correctness
- tune generation policy defaults
- use full-trace only for debugging windows

### Level 5: Operational Loop Fitness

Questions:
- does the prompt behavior support real operator loops over multiple turns?
- does it maintain role contract clarity?

Signals:
- command-lane consistency across turns
- no model-owned-execution claims
- stable user-run/result-return loop

If this fails:
- strengthen role contract language
- restate execution ownership explicitly
- add lane-specific examples with negative constraints

## Taxonomy Of Failure Modes

- `F1: Shape drift`
  - expected structured output; got extra prose or mixed format
- `F2: Provider protocol collision`
  - emits provider-native tool protocol markers
- `F3: Role confusion`
  - model implies it ran commands or owns execution
- `F4: Contract ambiguity`
  - unclear who executes, what output format is required
- `F5: Runtime mismatch`
  - config/transport flags not aligned with backend behavior
- `F6: Hidden-reasoning side effects`
  - latency/format instability when thinking mode differs
- `F7: Error-opacity`
  - malformed responses without enough diagnostics to repair quickly

## Fallback Pattern: Delegated Execution Contract

Use this when backend/system pressure is high and stricter format mandates are causing resistance.

Core move:
- the model advises
- the user executes (conditionally, by safety judgment)
- the model never claims execution

Canonical framing:
- “You suggest commands; I decide whether to run them.”
- “If I run one, I’ll return output for your next step.”
- “Use one unambiguous structure, e.g. `command: \"...\"`.”

Why it often works:
- aligns with safety/guardrail expectations around execution ownership
- reduces ambiguity without threatening the model’s policy posture
- preserves a clear iterative evidence loop

When to prefer it:
- strong hidden/system prompt conflict
- mixed conflict (system prompt + model predisposition)
- repeated provider-protocol collisions after stricter prompting attempts

Failure signatures:
- model still claims to have executed commands
- model emits provider-native tool protocol instead of command suggestion
- model adds conversational wrappers despite explicit structure request

Escalations from this fallback:
- switch vocabulary away from collision terms
- use entrainment-backed examples that preserve delegated ownership
- adjust runtime transport/thinking policy only after language-level alignment attempts

## Probe Matrix (Starter)

Dimensions to vary:
- prompt variant: live-like / strict / advisor-clear / terse protocol / entrained protocol
- vocabulary: tool-call words vs action/operation words
- structure: YAML block vs JSON object vs loose command
- runtime mode: thinking on/off, transport mode
- pressure: neutral system vs hostile provider-protocol system

Each matrix cell should record:
- pass/fail
- failure mode ID(s)
- representative output snippet
- remediation applied
- post-remediation result

Current harness artifact shape (`src/toas/llm_harness.py`) now records this directly per probe in:
- `expectation_report.pass`
- `expectation_report.checks[]` (expectation-level pass/fail)
- `expectation_report.failure_mode_ids[]`
- `expectation_report.recommended_remediation[]`
- `scenario_pack`

## Remediation Playbook

Suggested response when a probe fails:
1. Confirm runtime health and request shape.
2. Start with finesse:
   - restate role ownership clearly
   - ask for one simple structure without adversarial tone
   - reduce ambiguity while keeping cooperative language
3. If conflict remains high, shift to Delegated Execution Contract as the primary lane.
4. Remove collision vocabulary (`tool`, `function`, etc.).
5. Tighten output contract (strict variant) only when evidence suggests model predisposition (not system conflict) is the dominant issue.
6. Escalate to entrainment-backed prompt.
7. Adjust runtime policy (thinking mode, transport mode).
8. Capture full-trace diagnostics for unresolved malformed responses.

## Relationship To Existing TOAS Material

- Endpoint behavior notes: `docs/llm-notes.md`
- Protocol-collision notes: `docs/protocol-notes.md`
- Harness implementation: `src/toas/llm_harness.py`
- Prompt assets under test: `src/toas/prompts/protocol/*.txt`

This document is the narrative glue tying those pieces into one operational model.

## What To Build Next

A first-class “prompt probe” workflow should include:
- named scenario packs mapped to failure-mode IDs
- machine-readable expectations per scenario
- summarized pass/fail output plus remediation hints
- stable artifact output for comparison across backend/model changes
