Filed as: 260829-compound-tool-request-records
FKA:
AKA: compound action plan persistence; multi-plan tool request history
Legacy index:

keywords: runtime, implementation, active, correctness, provenance, frontier, graph

Parent: `260829-canonical-action-ingress-contract`
Depends on: `260829-assistant-candidate-convergence`
Related: `260626-events-jsonl-multiplicity-and-merge-provenance`

# Compound Tool Request Records

Persist the selected action plans from one frontier without losing the
incumbent single-plan `tool_request` payload shape.

## Scope

- preserve legacy list payloads for one `ActionPlan`;
- persist multiple sibling plans in one compound `tool_request` payload;
- keep ordered `ToolRequest` values within each plan;
- preserve the related frontier message id;
- keep result records and execution policy semantics unchanged unless a
  minimal association field is required by observed tests;
- add compatibility tests for writing and reading both payload forms.

## Non-Goals

- introducing a runtime `ToolRequest` or `ActionPlan` class;
- changing capability execution or arbitration;
- redesigning all durable record families;
- adding native provider call identity;
- deduplicating or evaluating semantic equivalence.

## Acceptance

- one-plan history remains byte/shape compatible with existing fixtures;
- multiple selected plans are represented by one `tool_request` occurrence
  record without flattening plan boundaries;
- existing history readers and summaries tolerate the compound form;
- focused tests and the relevant full regression suite pass;
- completion evidence records the compatibility decision and remaining seam.

## Outcome

Implemented the compatibility-preserving durable shape. A single selected
`ActionPlan` continues to write the incumbent list payload. Multiple selected
plans from one frontier are written as one `tool_request` record with a
`{"plans": [{"requests": [...]}, ...]}` payload, preserving sibling plan
boundaries and request order. Existing graph and summary behavior remains
compatible because the record kind and related frontier id do not change.

Verification:

- `./.codex-local/bin/uvt run pytest tests/test_runtime_session_step_edges.py tests/test_graph.py tests/test_cli.py -q --no-cov` (`403 passed`)
- `./.codex-local/bin/uvt run ruff check src/toas/runtime/session_step_edges.py src/toas/graph.py tests/test_runtime_session_step_edges.py`

Result records remain related to the frontier occurrence rather than gaining a
new plan-association field. Native provider call identity and richer
per-request provenance remain later canonical-boundary work.
