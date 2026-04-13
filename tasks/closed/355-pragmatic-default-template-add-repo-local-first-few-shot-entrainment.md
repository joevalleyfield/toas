## Goal

Improve local-model startup behavior for repo tasks by adding explicit few-shot/mimicry examples to the pragmatic default template.

## Why Now

Dogfood runs showed persistent "please provide repository access" responses even after progressive prompt layering, despite local TOAS tools being available. This is better handled by behavior-shaping examples than stricter policy language.

## Scope

- add a protocol-entrainment prompt fragment with local-workspace-first repo-task examples
- include that fragment in `session-start/templates/pragmatic-default_v1`
- add regression tests asserting the template now includes the new few-shot content

## Outcome

Implemented in current pass:
- new `session-start/protocol-entrainment/repo-local-first_v1` asset added
- `pragmatic-default_v1` template now composes `protocol/repo-local-first_v1`
- prompt tests assert presence of the few-shot and local-workspace-first guidance

## Errata

- early dogfood probes were confounded because `/prompt ...` output was rendered to command results but not appended into `session.md`
- additional probe confusion came from running against a stale dogfood-local runtime path instead of the system editable `toas` install
- after correcting method (append-first transcript flow + system `toas`), behavior shifted from hard external-repo refusal to local-tool usage in the first step (`capability_help`), with further autonomy still needing improvement
