Filed as: 260912-config-navigation-hint-correction
FKA:
AKA: config pipe hint; config topic navigation shorthand
Legacy index:

Parent: `260912-config-show-navigation-and-model-view`
Related: `260912-config-show-next-command-audit`

keywords: config, surface, implementation, follow-on, contract, discovery

# Restore compact config topic navigation hint

## Objective

Keep the unfiltered `/config show` view compact by presenting the focused topic
choices as a pipe-separated navigation hint, while retaining individually
usable `/config show <topic>` commands in the help and parser.

## Acceptance criteria

- The overview contains the compact `models|generation|extraction|execution`
  topic hint.
- The hint is understood as a choice/navigation aid, not advertised as a
  literal filter query.
- Existing individual topic commands remain covered and functional.
- This change does not define an `execution` key set; that requires separate
  design work.

## Allowed write surfaces

- config overview rendering;
- focused unit/acceptance tests;
- this task.

## Completion evidence

Restored the compact pipe-separated topic hint and retained executable
individual topic coverage in the acceptance path.

Focused result: `1 passed, 6 deselected` for the targeted unit and acceptance-step module.

## Status

Closed 2026-09-12.
