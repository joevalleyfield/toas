# Help Config Scaffolded Gemma4 Spike

## Goal
Check whether TOAS-native protocol scaffolding (`/prompt` + `/help tools`) is sufficient for gemma4 to produce repo-grounded callable operations for the real `/help config` change shape.

## Baseline
- Repo snapshot: pre-`/help config` support (`35dd4d8`)
- Runtime model intent set by operator: `/config set llm.model gemma4`

## Operator sequence used
1. `/config set llm.model gemma4`
2. `/prompt dynamic/capabilities/repo-work_v1`
3. `/help tools`
4. Request: implement `/help config` in this repo, compact output, mention `/config values <key>`, return callable ops only

## Observed result
- Assistant repeatedly returned prose + pseudo-code blocks.
- Output was not TOAS callable schema.
- Even with explicit "Return callable operations only", protocol conformance did not emerge.
- Content was also not repo-grounded (generic dispatcher snippets, non-authoritative assumptions).

## Signal
1. Existing TOAS scaffolds are discoverable but not strong enough to reliably entrain this model into valid callable protocol output.
2. The operator currently must still add handcrafted protocol alignment moves beyond native affordances.
3. We need prompt/template-level inclusion controls for tool guidance subsets so operators can opt into stronger protocol railings without writing them manually each run.

## Implication for acceptance
- Current acceptance can validate behavior in replay/scratch paths.
- For real weak-model reproducibility of concrete repo change-shapes, we need stronger built-in protocol affordances before expecting close parity.
