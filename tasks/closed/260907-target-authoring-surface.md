Filed as: 260907-target-authoring-surface
FKA:
AKA: config target commands; target authoring; durable target editing
Legacy index:

Parent: `260906-named-model-targets`
Depends on: `260906-named-model-targets`
Blocks:
Blocked by:
Related: `260907-model-observation-grammar`; `docs/notes/2026-09-06-endpoints-models-and-targets.md`

keywords: config, runtime, surface, implementation, historical, contract, naming

# Add Structured Target Authoring

Provide a durable configuration surface for named endpoint/model/generation
targets without making `/model select` mutate configuration.

## Contract

- `/config target list` inspects configured targets.
- `/config target add NAME [ENDPOINT] [MODEL]` creates a target.
- `/config target set NAME FIELD VALUE` updates structured target fields.
- `/config target remove NAME` removes a target.
- Mutations emit config updates; `/config save` controls file persistence.
- Shorthand declarations and network probing remain out of scope.

## Progress Evidence

Closed: implemented structured `/config target list|add|set|remove` authoring.
Mutations emit keyed `llm.targets` config updates; removal uses the named-target
unset operation, nested generation fields and list-valued fields are parsed, and
`/config save` remains the persistence boundary. Help and compact config usage
advertise the surface. Shorthand declarations, file-scope selection, and network
probing remain out of scope.

Verification: focused command/config tests 227 passed; full suite 3,202 passed,
12 deselected, 100% coverage; Ruff clean.
