# 677 Task Thread Capture and Routing
keywords: tooling, explore, active, contract, capture, routing, markdown, tasks

## Goal

Design and implement a synchronous, deterministic, and local task-capture tool `capture_task_thread` to let the active agent explicitly defer side threads (blockers, follow-ups, cleanup, risks, etc.) to a pluggable task tracker without pursuing them inline.

## Why

During complex execution loops, agents frequently encounter secondary thoughts, cleanups, minor bugs, and blockers. If the agent addresses these inline, its context window bloats, and it drifts from the primary task. If it ignores them, useful repository context is lost. Handoff to a fast, synchronous task-capture tool keeps the agent focused on the active thread while ensuring all secondary thoughts are durably tracked.

## Scope

- **Expose Tool:** Expose `capture_task_thread` as a callable tool for the active agent with fields: `title`, `kind`, `evidence`, `blocks_progress`, `active_task_id`, `scope_hint`.
- **Durable Event Log:** Write all captured payloads synchronously to a local append-only event ledger (`tasks/events.jsonl`).
- **Deterministic Routing Layer:** Decide the storage target using categorical matching and explicit heuristics:
  - **Micro (Node):** Edit the currently active task file to insert checklist items/sub-todos into specific target sections based on the interrupt category (e.g. `Risks`, `Unknowns`, `Next Actions`).
  - **Macro (Standalone):** Create a new standalone task file `tasks/open/{id}-{slug}.md` using a standardized markdown task template.
  - **Blockers:** Generate a blocker task, mark the active parent task as `blocked`, and inject continuation metadata (`blocked_by`, `why blocked`, `source capture id`, `resume condition`, `suggested resume action`).
  - **Low-Confidence Cases:** Route to a review inbox task (e.g., `tasks/open/inbox.md`) instead of guessing.
- **Pluggable Adapter Interface:** Define the `TaskTrackerAdapter` interface and implement the `LocalMarkdownAdapter` for local file system operations.
- **Structured Patching:** Implement regular-expression-based header matching to insert items into markdown files.
- **Resume Directives:** Return a structured output indicating whether the agent should `continue`, `pause`, or `pivot`.

## Non-Goals

- No passive capture mechanisms (no overwatch process, transcript monitor, background daemons, or lifecycle hooks).
- No asynchronous processing in v1 (all actions run synchronously inside the tool wrapper).
- No speculative LLM-based classification in the core router (use categorical/heuristic mapping).
- No integration with remote trackers (e.g., GitHub, Linear) in the first version, though the interface supports it.

## Done When

- The `capture_task_thread` tool is registered and callable by the agent.
- Calling the tool appends to the event log and returns a structured resume/pivot directive.
- Micro-level calls successfully edit the active task file under the correct section.
- Macro-level calls create a new task file matching the standard format and link it correctly.
- Blocker calls apply the `blocked` status and resume metadata to the parent task.
- Golden-file tests confirm that markdown patching edits only target sections and does not corrupt adjacent text block nodes.

## Initial Slices

1. **Adapter Interface & Golden-Files:** Define `TaskTrackerAdapter` and implement the regex-based `LocalMarkdownAdapter` editing logic. Validate using pre/post golden-file tests.
2. **Deterministic Router & Event Logger:** Write the routing rules mapper, the JSONL event logger, and implement the categorical section mapping.
3. **Tool Registration:** Integrate `capture_task_thread` into the agent's callable registry.
4. **Integration Testing:** Write integration tests simulating explicit agent calls and verifying file system outputs.

## Outcome

We have implemented:
- The pluggable `TaskTrackerAdapter` and `LocalMarkdownAdapter` for handling markdown patching and file operations.
- The `capture_task_thread` tool registry runner and integration with the agent's capability profile.
- Routing heuristics for Micro, Macro, Blocker, and Low-Confidence task triage.
- Extraction of active parent message IDs from the events log to preserve context.
- High-coverage unit and integration tests confirming correct behavior across all routing outcomes.

