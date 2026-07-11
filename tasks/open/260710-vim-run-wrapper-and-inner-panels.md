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
