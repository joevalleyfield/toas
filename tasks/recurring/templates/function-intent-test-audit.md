# Recurring: Function-Intent Test Audit

## Purpose
Audit behavioral intent assertions for active/high-risk surfaces so confidence comes from explicit behavior checks, not coverage alone.

## Trigger
- Biweekly during heavy refactor periods
- Or after major decomposition/runtime-lane changes

## Inputs
- Current hotspot/task focus areas
- Existing tests for target modules
- Coverage report as secondary signal

## Checklist
- Pick 1-3 target modules/functions
- Enumerate key intents per function
- Map current assertions to intents
- Identify unasserted intents and add focused tests where practical
- Open follow-on tasks only for larger uncovered intent seams

## Output
- Dated run artifact with audited surfaces and outcomes
- Test additions and/or focused follow-on task links
