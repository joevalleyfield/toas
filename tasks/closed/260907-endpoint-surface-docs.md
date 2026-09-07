Filed as: 260907-endpoint-surface-docs
FKA:
AKA: endpoint command documentation cleanup
Legacy index:

Parent: `260907-endpoint-command-cutover`
Depends on: `260907-endpoint-command-cutover`
Blocks:
Blocked by:
Related:

keywords: endpoint, documentation, command, backend

# Align Endpoint Surface Documentation

Update the maintained capability inventory after retiring command-level
backend catalog and selection adapters. Preserve backend terminology where it
describes actual lifecycle or policy controls.

## Progress Evidence

Completed: the maintained capability inventory now lists endpoint, target,
and secret config subcommands without implying a retired backend catalog
surface. Backend lifecycle and policy documentation remains backend-oriented.

Verification: repository status is clean after the endpoint command cutover;
the full suite passed with 100% coverage in the parent implementation slice.
