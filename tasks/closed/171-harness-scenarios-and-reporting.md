## Goal

Expand the local LLM harness so it probes the response-shape and latency questions TOAS actually cares about.

## Scope

- Add more scenario prompts
- Capture more structured report fields
- Make harness output easy to diff or archive

## Behavior

- The harness can probe exact-match, JSON, YAML, and other structured-response cases
- Reports capture timing, parseability, and notable side fields
- Slow or failing scenarios return structured failures instead of wedging the run

## Rules

- Keep the harness focused on TOAS-relevant questions
- Prefer report fields over prose in the tool output
- Live probes should fail clearly rather than silently omit scenarios

## Non-Goals

- No generic benchmark suite
- No dashboard or UI layer

## Done When

- The harness covers the main prompt/response cases TOAS cares about
- Output is structured enough to compare runs
- Tests cover harness-side parsing and failure behavior
