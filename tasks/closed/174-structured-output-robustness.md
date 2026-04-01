## Goal

Probe how reliable the live endpoint is for structured outputs that matter to agentic workflows.

## Scope

- Test YAML/tool-call response behavior
- Test JSON exactness beyond trivial cases
- Compare prompt variants where the current behavior looks fragile

## Behavior

- TOAS has direct evidence about structured-output reliability
- Timeouts, malformed outputs, and hidden extras are visible in reports
- Prompt strategies can be compared on practical agentic criteria

## Rules

- Focus on structures TOAS actually uses or is likely to use soon
- Keep scenario prompts compact and reproducible
- Treat timeouts and parse failures as first-class outcomes

## Non-Goals

- No exhaustive prompt search
- No claims of general model quality outside TOAS use cases

## Done When

- The harness and notes cover structured-output scenarios relevant to TOAS
- The repo has concrete evidence about where YAML/JSON prompting is robust or fragile
- Future extraction/repair work can start from those observations rather than intuition
