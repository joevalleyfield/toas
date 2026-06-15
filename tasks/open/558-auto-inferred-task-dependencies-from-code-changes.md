# 558 Auto-Inferred Task Dependencies from Code Changes
keywords: tooling, explore, parked, research, dependencies, inference, code-changes, automation

## Why
Task dependencies are currently recorded manually in the `## Related` section of task files. This is error-prone and often leads to outdated or missing dependency information, making it difficult to understand the impact of changes or the sequence of work.

The system keeps trying to infer structure from code (e.g., module decomposition, graph edges). Extending this to task dependencies would create a more accurate and dynamic view of the project's state.

Manual relationship fields now cover intentional structure for active planning.
This task should infer additional or stale graph edges from evidence; it should
not replace explicit `Parent:`, `Blocks:`, `Blocked by:`, or `Related:` links.

## Goal
Develop a mechanism to automatically infer task dependencies from code changes and commit history, reducing manual overhead and improving accuracy.

## Scope
- Analyze commit history to identify patterns of co-occurrence (e.g., tasks whose tasks files are modified in the same commit, or tasks whose code changes touch the same modules).
- Design a lightweight inference algorithm to generate dependency graphs.
- Create a tool to visualize and verify inferred dependencies.
- Integrate inferred dependencies into the Workboard (e.g., as "Inferred Related" sections).

## Non-Goals
- Replacing manual `## Related` fields entirely (they provide context and intent that code changes don't).
- Replacing explicit manually-authored parent/blocking relationships for active
  coordination tasks.
- Heavyweight static analysis of the entire codebase.

## Proposed Direction
1. **Co-occurrence Analysis:** Track which task files are modified in each commit. Tasks modified in the same commit are likely related.
2. **Code Proximity Analysis:** Track which source files are modified. If Task A and Task B both modify `src/toas/cli.py`, they may be related.
3. **Dependency Graph Generation:** Use the above signals to generate a weighted dependency graph.
4. **Verification Loop:** Present inferred dependencies to the operator for verification/correction.

## Validation
- Run the inference tool on the last 6 months of commits.
- Compare inferred dependencies with manually recorded ones.
- Verify that the inferred graph helps identify hidden bottlenecks or parallelization opportunities.

## Related
- `400` Tools/Step CLI module decomposition
- `525` Post-envelope runtime ownership
- `sync_workboard.py` (existing automation)
