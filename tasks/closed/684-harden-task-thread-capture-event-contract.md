# 684 Harden task-thread capture event contract

## Current Reality
The `capture_task_thread` tool logs event payloads directly to `tasks/events.jsonl` using a raw Python dictionary (`event_data`). The payload contains attributes like `title`, `kind`, `evidence`, `blocks_progress`, `active_task_id`, and `scope_hint`, while the outcome records fields like `target`, `file_path`, `directive`, `summary`, and `active_message_id`. This is purely ad-hoc dictionary instantiation without static type schemas, validation rules, or serialization consistency.

## Desired Reality
A formal, strongly typed, and versioned event contract for task capture. Payloads written to the ledger must be validated against a schema (e.g., via a typed class, dataclass, or Pydantic model). The ledger entries are guaranteed to be well-formed, preventing schema drift as the event schema evolves or integrations are added.

## Gap Analysis
Currently, `route_and_capture` constructs dictionaries directly. We need an intermediate parser/validator class (or dataclasses with JSON serialization helpers) to define, validate, and serialize these events.

## Known Facts
- Events are stored in `tasks/events.jsonl` in JSON Lines format.
- The tool runs synchronously inside the `capture_task_thread` tool wrapper.

## Assumptions
- Python dataclasses or typed dicts with helper validators should be preferred to avoid external package bloat if Pydantic is not a project dependency.

## Unknowns
- Whether multiple versions of the schema will need to be supported in the same ledger file simultaneously (forward/backward compatibility requirements).

## Investigations
- Check `pyproject.toml` to see if Pydantic or similar libraries are in use elsewhere in the project.

## Models
- Define `TaskCaptureEvent`, `TaskCapturePayload`, and `TaskCaptureOutcome` schemas.

## Forecasts
- Hardening the contract will prevent corrupt event lines when multiple agents or scripts parse `tasks/events.jsonl`.

## Risks
- Introducing validation errors might crash the tool during crucial triage moments. Fallback validation or permissive parsing is required for resilience.

## Transformations
- Move raw dictionary initialization in `tasks.py` to instantiated schema objects with `.model_dump()` or `.to_dict()`.

## Evidence
- Schema definitions and tests asserting invalid payloads are rejected.

## Decisions
- Use standard library `dataclasses` or `TypedDict` with custom validator functions to maintain local parity-safety without external dependencies.

## Open Fronts
- Schema versioning strategy for `tasks/events.jsonl`.

## Next Actions
- [x] Define `TaskCapturePayload`, `TaskCaptureOutcome`, and `TaskCaptureEvent` dataclasses with `.validate()`, `.to_dict()`, and `.from_dict()` methods in `src/toas/tasks.py`.
- [x] Update `TaskTrackerAdapter` and `LocalMarkdownAdapter` interfaces/implementations for `log_event()` to accept `TaskCaptureEvent`.
- [x] Add type validation tests asserting invalid types or payloads are rejected.
- [x] Verify everything compiles and passes tests.

