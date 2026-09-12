Filed as: 260912-config-show-next-command-audit
FKA:
AKA: config next audit; vapor config navigation
Legacy index:

Parent: `260912-config-show-navigation-and-model-view`

keywords: config, discovery, surface, contract, hardening, active

# Audit and repair config-show navigation

## Objective

Ensure commands advertised by unfiltered `/config show` and config help are
real, useful, and covered by an executable discovery path.

## Contract

- Inventory the overview's `next:` commands and the corresponding help-asset
  actions against actual dispatch handlers.
- Repair misleading syntax, implement only small missing navigation aliases
  where the existing contract clearly implies them, and label genuinely
  deferred work instead of advertising it as available.
- Add acceptance coverage that follows the repaired path and checks that each
  advertised command produces a meaningful result or explicit next-step
  diagnostic.

## Acceptance criteria

- No advertised command is vapor without an explicit deferred label.
- `/config show`, `/config` usage, and `/help config` agree on the available
  navigation surface.
- The audit includes both semantic topic commands and structured endpoint/target
  commands.
- Existing config behavior and key discovery remain intact.

## Allowed write surfaces

- config overview/help rendering and help assets;
- focused unit/acceptance tests;
- this task and generated workboard.

## Completion evidence

Audited the overview navigation against dispatch and filtered-key behavior.
The combined `models|generation|extraction|execution` hint was vapor because
the filter parser treats it as one literal query. It now advertises individually
executable `/config show` topic commands for models, generation, extraction,
backend, shell, and tool_writes. Acceptance follows each command and verifies
that it produces a real view rather than a no-match diagnostic.

Focused result: `444` selected tests, including `17` acceptance tests.
Full result: `3234 passed, 17 deselected`; coverage `100%`; Ruff and mypy passed.

The structured `/config show models` redesign remains in the sibling child
task `260912-config-model-structured-view`.

## Status

Closed 2026-09-12.
