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

## Status

Ready for implementation.
