Filed as: 260710-vim-run-wrapper-and-inner-panels
FKA:
AKA: vim run metadata dashboard; inner content panels; stall proxies; tool vs llm wrapper metadata
Legacy index:

keywords: surface, explore, active, usability, vim, stream, projection, tool, llm

Parent: `260614-architecture-follow-through-coordination`
Related: `260620-host-stdio-reasoning-terminality-ux`; `260705-host-subscribe-terminal-event-parity`; `260710-vim-command-transcript-dedup`

# Vim Run Wrapper And Inner Panels

## Current Reality

The Vim async/watch surface still mixes multiple concerns:

- the outer activity/run wrapper
- provisional inner content from tool or llm lanes
- canonical projected transcript/result content
- metadata whose ownership is lane-specific but is currently rendered too
  generically

Recent spike work exposed two related issues:

- tool and projection content can cross-contaminate when they share one text
  accumulator
- wrapper metadata such as `thinking` / `prompt_progress` is really llm-owned
  state, but today it is rendered at too generic a level

The spike also clarified that explicit visible labels like `kind: llm` are
probably not the right UI. The user should infer what kind of inner content is
active from the shape and fields of the wrapper rather than from a taxonomy
label.

## Desired Reality

The Vim surface should treat:

- `run` as the outer wrapper/activity shell
- `tool` and `llm` as inner content shapes chosen by observed frontier/lane
- canonical projection as its own authoritative content surface rather than as
  text merged into provisional inner output

The wrapper should render a small, context-rich panel:

- shared run fields at the outer level
- llm-specific fields only when the inner content is llm-shaped
- tool-specific fields only when the inner content is tool-shaped

The implementation should support a future templated dashboard without forcing
that full UI now.

## Design Notes

### Outer Run Wrapper

Always-owned wrapper fields currently in scope:

- run status
- elapsed time
- terminal failure/cancel summary when relevant

Possible later additions:

- transport/backend mode if operationally useful
- started-at time if that proves helpful

### LLM Inner Panel

Likely high-value llm-owned fields:

- endpoint identity
- token counts
- prompt progress line/state
- stall-proxies rather than stall classification
- stream flags such as `thinking` / `prompt_progress` only as secondary detail

`stall-proxies` means observable inputs to operator judgment, not a runtime
claim that a run is stalled. Candidate proxies:

- last activity age
- last content age
- connection/subscription state
- last progress age

### Tool Inner Panel

Likely high-value tool-owned fields:

- tool/procedure identity
- subprocess/process identity when relevant
- terminal summary such as exit/success/failure

Slash/operator commands do not need bespoke long-lived UI yet while they remain
effectively instantaneous; their output is usually the answer to the user's
anxiety.

## Implementation Direction

Prefer clean ownership over ad hoc rendering fixes:

- keep separate inner text/state buffers for tool, llm, and canonical
  projection
- keep wrapper metadata separate from inner-content metadata
- classify inner content for rendering purposes without necessarily surfacing a
  literal `kind:` label
- prefer canonical projection over provisional inner text when both exist

Architectural smell to preserve for follow-up:

- if the old RPC wrapper/test seam implies live streaming or UI-shape behavior,
  concerns are still crossing the wrong axis; transport compatibility seams
  should not be the thing that determines wrapper/dashboard semantics

The current spike should be treated as exploratory material to harvest from,
not as the final UI contract.

## Spike Findings

- separate buffers/state for tool text, llm text, and canonical projection do
  reduce cross-contamination pressure in the Vim watch surface
- explicit visible `content:` / `kind:` labels are not necessary if the panel
  shape itself makes llm-vs-tool state legible
- endpoint identity felt more valuable than stream flags as an llm-facing cue
- token counts and prompt-progress lines are useful first-pass llm fields even
  before a richer templated dashboard exists
- tool-facing metadata is currently thinner than llm-facing metadata; tool
  identity is available now, but richer subprocess detail likely needs better
  event ownership upstream
- elapsed-time repaint can freeze if wrapper refresh is coupled only to content
  changes; wrapper chrome needs its own refresh path for quiet runs
- current Vim/RPC test seams are not a trustworthy oracle for wall-clock UI
  repaint behavior, which reinforces the transport-vs-surface separation note

## Progress Notes

- first boundary slice landed internal `tool` / `llm` run-kind classification
  so wrapper rendering can stop treating llm-only stream/progress fields as
  generic run metadata
- prompt-progress classification now counts as llm-owned activity even before
  answer text arrives
- next ownership slice landed canonical projection as separate Vim run state so
  projection can be preferred without being merged back into generic streamed
  run text
- tool-lane text now has its own Vim run state as well, so active tool output
  and first-pass tool identity no longer have to borrow the generic run-text
  slot before projection arrives
- run wrapper elapsed time now repaints on its own coarse clock path, and tool
  identity is seeded from frontier/request shape (`$ ...`, `tool_name: ...`,
  `operation: ...`) instead of waiting for terminal tool metadata alone

## Remaining Split

### Landable Without Runtime Updates

These are still Vim/surface-owned and can land against current facts:

- wrapper copy/layout polish now that the ownership split is clearer
- choosing which current run/tool/llm fields stay visible by default
- transport/backend label if we decide it is worth showing
- started-at time if we want it in addition to elapsed
- completion persistence policy for the wrapper versus transcript-only collapse
- local reduction/retuning of noisy Vim wire logging after the current spike
- renderer cleanup toward a future templated dashboard without changing owned
  runtime facts

### Wants Runtime-Owned Facts

These likely want new or better upstream event ownership rather than more Vim
inference:

- endpoint identity for llm runs
- token counts and eventual cost fields
- richer tool identity than frontier aliasing or terminal `operation`
- subprocess/process identity for tool runs
- last-activity / last-content / last-progress ages as true stall proxies
- explicit connection/subscription state if it should be shown to operators
- stronger terminality guarantees so elapsed/stall surfaces reflect real run
  lifecycle rather than orphaned-open state

### Rough Runtime Update Shape

The likely runtime asks are:

- emit first-class llm metadata records or stream events for endpoint/model and
  token usage
- emit first-class tool lifecycle metadata earlier than terminal `tool_done`
  when tool identity/process facts are known
- make run-level activity timing facts available without Vim reconstructing them
  from receive cadence alone
- tighten async terminality contract so every started run reaches a terminal
  run-owned consequence or an explicit intermediate state

## Scope

- define the wrapper vs inner-panel ownership model for Vim async/watch UI
- define first-pass metadata fields for run, llm, and tool panels
- define projection authority relative to provisional tool/llm text
- identify which current fields move from generic wrapper rendering into
  llm-only or tool-only rendering

## Non-Goals

- polished final dashboard visuals in this task alone
- premature stall heuristics/classification
- over-design of instantaneous slash/operator command UI

## Exit Evidence

- [ ] wrapper vs inner panel ownership is explicit
- [ ] tool, llm, and projection state boundaries are explicit
- [ ] llm-only metadata is no longer rendered generically on tool runs
- [ ] first-pass metadata set is chosen for run, llm, and tool views
- [ ] the design is usable as input to a later templated dashboard surface
