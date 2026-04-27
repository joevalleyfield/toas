## Goal

Introduce a procedure library and invokable procedure surface so common agent workflows are reusable, explicit assets rather than ad-hoc prompt text.

## Why Now

The system needs low-activation execution guidance that can be composed and replayed, while keeping stable principles in `AGENTS.md` and avoiding hardcoded hidden runtime behavior.

## Scope

- define procedure asset format and storage conventions
- implement invocation surface (for example `operation: procedure`)
- create first procedures:
  - repo-local discovery/triage
  - task selection and first-action handoff
- wire procedure references into session templates where appropriate

## Progress

- added packaged procedure asset library under `src/toas/procedures/*.yaml` with normalized loader (`toas.procedures`)
- added invokable `operation: procedure` tool surface with `name` and optional `dry_run`
- added first reusable procedures: `repo_discovery_triage_v1` and `task_pick_first_action_v1`
- wired procedure bootstrap example into default session template (`session-start/templates/pragmatic-default_v1`)

## Intended Behavior

- operators can reference/invoke procedures by name
- models receive consistent stepwise execution scaffolding with minimal extra load
- procedures are inspectable, versionable, and replayable

## Done When

- procedure assets and invocation surface are implemented and tested
- at least one default template composes a procedure
- docs describe procedure authoring and invocation
