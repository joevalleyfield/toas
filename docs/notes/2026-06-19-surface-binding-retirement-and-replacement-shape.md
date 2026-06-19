# Surface Binding Retirement and Replacement Shape

Status: DIRECTIONAL
Normative Scope: exploratory replacement-shape note for a potentially retiring surface-binding layer
Related Tasks: `260619-session-md-compatibility-retirement`, `260619-daemon-package-facade-shrinkage`, `260615-legacy-surface-retirement-inventory`

## Context

TOAS has a durable surface-binding concept that can associate a named surface
with a transcript path. The idea is coherent, but the current use case does not
yet clearly justify keeping the indirection as a first-class requirement.

The main observed need is simple transcript stickiness:

- an editor or agent should be able to say which transcript path it is using
- that path should remain durable when explicitly configured
- named surface identity should only survive if it solves a real multi-surface
  orchestration problem

## Working Hypothesis

The likely eventual replacement is not a more elaborate binding system. The
likely replacement is one of these:

1. explicit transcript paths as the primary operator-facing control
2. a very small alias registry where `surface_id` is just a short name for a
   transcript path, with minimal disambiguation
3. no separate surface concept beyond configured transcript path plus durable
   selected-surface records where there is a real multi-surface need

If the indirection does not earn its keep beyond a filename shortcut, it should
probably go away.

## Design Questions

- Is `surface_id` doing meaningful work beyond shortening a path?
- Do agents or operators need stable identity independent of path churn?
- Can explicit transcript paths alone cover the common case?
- If we keep a registry, should it look more like `stem -> path` plus a small
  disambiguator than a richer surface model?

## Current Observation

The editor-centric workflow can already tell TOAS which transcript file it is
working on. That suggests the direct path is sufficient for the common case.
Surface binding only becomes compelling if it supports a durable, agent-drivable
named workflow that path strings alone do not represent well.

## Replacement Shape

If the layer is eventually retired, the replacement should preserve:

- explicit transcript-path selection
- durable selected-surface records only where a workflow needs them
- clear agent-facing ergonomics for named workflows if we keep aliases

The replacement should not silently recreate hidden fallback behavior.

## Exit Criteria

This note can be considered resolved when either:

- a concrete multi-surface use case proves the indirection valuable, or
- the system is simplified toward explicit transcript paths and any surface
  registry is reduced to a lightweight alias convenience

