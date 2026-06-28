Filed as: 260628-acceptance-live-prompt-realism
FKA:
AKA: tiny-prompt spike; acceptance live smoke-test depth; bootstrap prompt not projected in acceptance
Legacy index:

keywords: acceptance, spike, projection, prompt, llm-input, smoke-test, investigation, follow-on

Parent:
Related: `260628-acceptance-suite-revival`; `260628-acceptance-per-step-hybrid-generation`; `260628-acceptance-live-generation-bounds`

# Acceptance Live Prompt Realism

## Spike Result (done 260628)

While diagnosing live/hybrid acceptance timeouts, a spike captured exactly what
TOAS sends to the model on the `stage_frontier` step (by passing a recording
`generate` override into `operator_step_once`):

```
[ { "role": "user", "content": "acceptance S1 staged frontier" } ]
# 1 message, ~29 chars, ~7 est tokens
```

So the live request is a single ~7-token bare user message. No system prompt, no
session-start bootstrap, no capability advertisement — even though the workspace
config has `session.bootstrap_prompt_ref =
session-start/templates/pragmatic-default_v1`.

This matched the backend logs (llama.cpp showed ~14-56 token prompts, then the
model decoding 500-600 tokens at ~30 t/s with no stop until the 20s
pytest-timeout cancelled it). A context-free prompt gives the model nothing to
anchor on, so it free-associates until cut off.

## Why It Matters

This is consistent with TOAS's transcript-authoritative design (nothing is
hidden/auto-injected; the operator places prompt material in the transcript).
But it means the *live* acceptance path is a degenerate smoke test: it proves
"the backend round-trips" but not "TOAS projects a realistic operator prompt."
The scenarios never seed the bootstrap prompt into the transcript, so live runs
never exercise system/bootstrap/capability projection.

## Decision Needed

- (a) **Make live acceptance realistic**: have the scenarios insert the
  configured session-start bootstrap prompt (e.g. via `toas prompt
  session-start/templates/pragmatic-default_v1` into the transcript, or an
  explicit control turn) before the first generating step, so live runs project
  a representative prompt.
- (b) **Keep it a connectivity smoke test**: accept the bare-prompt behavior and
  document that live acceptance only checks backend reachability/round-trip, not
  projection fidelity.

Leaning (a): a realistic prompt is also what makes a bounded, terminating
response likely, which removes most of the live-timeout pressure independent of
model speed.

## Exit Evidence

- [x] captured the exact projected llm-input for an acceptance generating step
- [ ] decision recorded: enrich vs. document-as-smoke-test
- [ ] if enriching: scenarios project the bootstrap prompt and a live run shows a
  representative (non-trivial) prompt reaching the model
