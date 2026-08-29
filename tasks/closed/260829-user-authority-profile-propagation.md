Filed as: 260829-user-authority-profile-propagation
FKA:
AKA: user action authority; unbounded user lane; user capability policy
Legacy index:

Parent: `260803-tool-intent-ingress-separation`
Related: `260530-shell-lane-spawn-semantics`; `260829-declared-objective-lane`

# User Authority Profile Propagation

Ensure that every direct-user action-intent receives the intentionally
unbounded user authority profile before capability dispatch, rather than
inheriting assistant policy through a non-process execution path.

## Current Pressure

The user-mediated transcript protocol intentionally distinguishes:

- `TOAS:USER`: user action-intent with unbounded user authority;
- `TOAS:ASSISTANT`: assistant action-intent presented by the user and processed
  under the user-configured assistant policy.

The current runtime gives the user profile special handling for `shell` and
`shell_script`, but delegates other callable actions through assistant-style
execution machinery. This can impose accidental workspace, grant, or timeout
limits on direct-user actions such as `read_file`.

## Desired Behavior

- direct-user command syntax and direct-user structured callable syntax select
  the same unbounded user authority profile for the requested capability;
- assistant action-intent selects the configured assistant authority policy;
- ordinary argument validation, capability validation, and operating-system
  permissions continue to apply to both profiles;
- a user action is not bounded merely because its capability is not process
  execution;
- assistant policy remains user-configurable, with boundedness as its normal
  profile rather than an immutable ceiling;
- execution still requires the user-mediated `step` roundtrip.

## Anchor Regression

For a file outside the configured workspace:

- direct-user `read_file` is not rejected by assistant-style workspace policy;
- assistant `read_file` follows the configured assistant workspace policy;
- strict assistant policy may reject the path;
- explicitly unbounded assistant policy may allow it when selected by the
  user;
- ordinary missing-file and operating-system access failures remain valid.

Also prove that direct-user YAML and direct-user command syntax have equivalent
authority behavior for process execution.

## Scope

- locate the authority-selection seam before capability dispatch;
- propagate user versus assistant execution context without duplicating
  capability runners;
- preserve direct-user process execution as intentionally unbounded;
- add focused tests for user and assistant `read_file` and process execution;
- verify request/result behavior remains append-only and step-mediated;
- document the authority distinction where the implementation boundary is
  established.

## Non-Goals

- native provider tool-call integration;
- renaming `shell` or `shell_script`;
- redesigning durable request/result records;
- introducing a universal intent ontology;
- making direct-user authority configurable without a demonstrated use case;
- removing assistant policy controls or workspace configuration;
- bypassing ordinary capability validation or operating-system permissions.

## Done When

- direct-user non-process actions no longer inherit assistant-only bounds;
- assistant actions continue to honor the selected assistant policy;
- the anchor regression passes for strict and unbounded assistant policy;
- tests cover both user ingress forms and assistant callable ingress;
- no hidden execution loop or role-boundary regression is introduced;
- the implementation seam and remaining taxonomy/evidence gaps are recorded
  for subsequent follow-ons.

## Outcome

Closed on 2026-08-29.

The frontier dispatch now routes the default executor through the user context
for every direct-user structured action, not only plans containing `shell` or
`shell_script`. Non-process calls such as `read_file` therefore use the
intentionally unbounded user workspace profile while retaining shared
validation, capability dispatch, and operating-system permissions.

Explicit injected executors remain honored as a dependency-injection seam for
callers and tests.

Verification:

- `./.codex-local/bin/uvt run pytest tests/test_step.py -k 'direct_user_read_file or assistant_read_file_follows or user_tail_shell_is_unbounded or execute_plan_user_context or user_tail_with_callable_executes or successful_direct_retry_promotes' --no-cov -q`
- `./.codex-local/bin/uvt run pytest tests/test_step.py tests/test_tools_file_ops.py tests/test_runtime_session_step_edges.py -k 'shell or read_file or tool_request or command_request or workspace or user_context or frontier' --no-cov -q`
- `./.codex-local/bin/uvt run pytest --no-cov -q` — 2906 passed, 9 deselected
