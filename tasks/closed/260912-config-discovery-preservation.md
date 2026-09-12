Filed as: 260912-config-discovery-preservation
FKA:
AKA: config key discovery hardening; exhaustive config escape hatch
Legacy index:

Parent: `260912-config-show-effective-overview`

keywords: config, discovery, surface, hardening, usability, active

# Preserve configuration-key discovery after overview projection

## Objective

Make the transition from the flat `/config show` output to the grouped
overview discoverable and regression-safe. Document the exhaustive provenance
view and ensure non-deprecated configuration keys remain reachable through
help or filtered inspection.

## Contract

- `/config show` remains the grouped effective overview.
- `/config show --sources` is documented as the exhaustive key/provenance
  escape hatch.
- `/config show <key-or-topic>` remains the focused inspection path.
- `/help config <query>` remains the searchable discovery path.
- No non-deprecated key may disappear merely because it is not represented in
  the overview.
- Deprecated/compatibility keys must be labeled as such when surfaced.

## Acceptance criteria

- Compact `/config` usage names both focused inspection and exhaustive
  `--sources` inspection.
- Help text explains that the overview is curated and filtered/source views are
  exhaustive or searchable.
- Regression coverage verifies representative keys outside the overview remain
  discoverable and inspectable.
- Existing grouped overview, filtered output, and winning-source behavior stay
  intact.

## Allowed write surfaces

- config usage/help assets;
- configuration discovery and rendering tests;
- this task and generated workboard.

## Required completion evidence

- Usage/help output showing the escape hatch;
- representative discovery checks for ordinary and compatibility keys;
- focused and full verification results.

## Completion evidence

Compact `/config` usage now documents both focused key/topic inspection and the
exhaustive `/config show --sources` provenance escape hatch. The config help
asset explains that the overview is curated and points to the exhaustive view
for every effective key. Regression coverage verifies the complete valid-key
surface, including compatibility and credential-reference keys, remains
available through the source view.

Focused result: `186 passed` across config/operator and help tests.
Full result: `3234 passed, 17 deselected`; coverage `100%`; acceptance and
integration `17 passed`; Ruff and mypy passed.

## Status

Closed 2026-09-12.
