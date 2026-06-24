Filed as: 260624-cli-message-timestamp-assertion-cleanup
FKA:
AKA: cli test timestamp cleanup; message event assertion drift; provenance graph inspection fallout
Legacy index:

keywords: tooling, hardening, active, correctness, timestamp, graph, provenance, coverage

Related: `260624-large-event-graph-render-performance`; `260624-message-timestamps-and-toas-provenance`; `672`
Status: closed

# CLI Message Timestamp Assertion Cleanup

## Current Reality

Recent large-log graph inspection and related provenance work left a set of CLI
tests asserting older durable message-event shapes that did not include
timestamps.

The runtime now materializes message events with UTC epoch-second timestamps, so
those assertions fail even though the underlying behavior is correct.

## Desired Reality

CLI tests that validate durable history content should either assert the
timestamp explicitly when it matters or normalize it away when the test is about
parentage, provenance, or adjacent non-message records.

The remaining assertion surface should match the current durable contract rather
than preserving stale pre-timestamp expectations.

## Plan

- normalize the affected CLI message-event assertions so they compare the
  intended durable structure without depending on wall-clock values
- rerun the focused CLI coverage slice to confirm the failures are resolved
- update the roadmap to note this active hardening cleanup

## Closure

Closed by `cli: close timestamp assertion cleanup`.

Normalized the stale CLI durability assertions onto parsed event comparisons,
preserving explicit checks that newly materialized message timestamps are
integer-valued while allowing seeded pre-timestamp history fixtures to remain
historical. Focused CLI coverage returned to 100% for the touched surface.
