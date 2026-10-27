Filed as: 261027-stdio-stall-diagnostics
FKA:
AKA: overlapping suite stall; blocking stderr diagnostic
Legacy index:

keywords: transport, hardening, historical, correctness, stream, coverage

Related: `261027-stream-bridge-timeout-test`

# Bound stdio integration failure diagnostics

Status: CLOSED; request failures no longer block on live stderr.

An overlapping full-suite run reached `_process_diag` after the sequential
stdio request received no response within four seconds. Its synchronous
`stderr.read(512)` then blocked on a live child until pytest's 20-second
timeout killed the suite. A serial run passed. Contention is a hypothesis,
not an established cause of the missing response.

## Plan

- Drain stderr independently and snapshot only already captured bytes on
  failure; never wait for stderr EOF in the assertion path.
- Exercise a live, deliberately nonresponding child to verify bounded failure
  and preservation of stderr evidence.
- Repeat actual host integration tests under concurrent load and inspect any
  newly exposed failure before deciding whether startup timing needs repair.
- Keep production transport semantics unchanged unless reproduction locates
  a production defect.

## Implementation and evidence

- Reused the output-pump pattern for stderr; diagnostics drain at most 512
  already captured bytes, never a live pipe. Request deadlines use monotonic
  time and retain the original four-second default.
- Added real-child regressions for empty and short open stderr. Each child
  signals readiness before the request, deliberately withholds a response,
  remains alive through the assertion, and is terminated and reaped afterward.
- Sequential interaction previously accepted an earlier response even if the
  next request timed out. It now requires clean child exit in that fallback,
  matching the other two existing host tests.
- Initial local baseline: all three original tests passed. Updated focused run:
  all five tests passed. A two-copy, four-worker run passed all ten cases.
- A larger stress attempt reported failures but was interrupted before failure
  diagnostics were collected. Its fail-fast repeat (20 copies, four workers)
  passed all 100 cases in 56.15 seconds. This does not establish a cause for
  the initial missing response; no startup timeout was increased.
- Full `uv run pytest` with the unchanged default 20-second timeout:
  3,600 passed, eight skipped, 17 deselected; 100.00% statement coverage.
- All 17 acceptance scenarios, Ruff, and mypy passed.

## Remaining uncertainty

The original missing response was not reliably reproduced. The observed
diagnostic hang is fixed and directly exercised; the tests now expose a
future live-host timeout instead of hanging or accepting a previous response.
No production defect or justification for a larger request timeout was found.
