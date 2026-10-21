# Endpoint configuration continuity and discovery order

Filed as: 261020-endpoint-state-continuity
FKA:
AKA: endpoint added then missing; discover models before defaults
Legacy index:
keywords: config, implementation, closed, runtime, continuity

Related: `261020-endpoint-auth-discoverability`

Status: CLOSED 2026-10-20

Operator evidence: `.toas/session-261020-2200-testing-one.md:178-200` reports
successful endpoint creation followed by unknown endpoint. Durable history
contains the successful endpoint update. Transcript-native configuration
reconstitution handles ordinary set/unset/restore but omits endpoint commands,
so an earlier ordinary declaration can replace effective configuration without
the later endpoint declaration.

Acceptance:
- Endpoint-add guidance discovers models before suggesting a default model.
- Add then list/set works across steps alongside ordinary config declarations.
- Reconstituted branches preserve endpoint add/set/remove source order without
  inheriting endpoints from unrelated branches or replaying external probes.
- Invalid endpoint declarations remain non-mutating.
- Refreshed model catalogs survive subsequent steps without repeated probes.
- Inspect actual CLI output and durable records in an isolated workspace.

Roadmap and manual workboard triage reviewed during today's upstream integration;
their strategic claims remain unchanged for this focused correction.

## Implementation and evidence

Reproduced add-then-list failure through actual isolated CLI steps. Endpoint
add/set/remove declarations now share existing endpoint handlers during config
reconstitution. Selected durable messages also retain their recorded endpoint
catalog updates, preserving discovery/capture without replaying external probes.
Branches without those messages do not inherit their endpoints.

Guidance now orders refresh and known-model listing before optional default
selection. CLI regression covers add/list/refresh/known/set/list/known, verifies
one discovery call, then branches before creation and sees no endpoints.
Reducer checks cover source order, removal, malformed input, unknown endpoint,
and exclusion of fresh environment-dependent capture.

Focused verification: 302 passed (including environment matrix), Ruff and mypy
pass. Inspected actual CLI flow against a local HTTP models endpoint: refresh
reported two discovered models, known listed both, setting the chosen default
succeeded, and endpoint list retained it. Original operator history untouched.

The first check.sh attempt also exposed matrix isolation when launched from
Git Bash: Windows process launch can search the launching process PATH. Matrix
cases now scope both launcher and child PATH via a restoring monkeypatch
context. Git-root discovery supports both cmd/git.exe and mingw64/bin/git.exe.
Matrix rerun from Git Bash: 10 passed; real utilities remain independently
tested from controlled native Windows behavior.

Final verification: complete `scripts/check.sh` from Git Bash with
`TOAS_TEST_VIM_BIN=C:/Windows/vim.bat` passes: **3,583 passed**, eight skipped,
17 deselected, 201.51 seconds, **100.00% coverage**, zero missing statements;
all 17 acceptance scenarios pass in 6.96 seconds; repository Ruff and mypy pass.
