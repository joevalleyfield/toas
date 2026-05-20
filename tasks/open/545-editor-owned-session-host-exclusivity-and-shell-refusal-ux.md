# 545 Editor-Owned Session Host Exclusivity And Shell Refusal UX

## Goal
Implement editor-owned session host exclusivity semantics with explicit shell refusal behavior while editor ownership is active.

## Why
`544` establishes host serve/stop and parent-coupled lifecycle primitives. Next, we need the user-visible ownership policy: editor owns host while active, shell async lifecycle commands in same repo are refused with clear diagnostics.

## Scope
In scope:
- extend session-host record with owner metadata sufficient for exclusivity checks:
  - `owner_kind` (`editor` | `shell`)
  - `owner_id` (session identifier)
- editor attach/start behavior contract:
  - create/attach host as editor owner
  - reuse only for matching active owner identity
- shell refusal path when active editor-owned host exists:
  - explicit diagnostic message
  - no implicit cross-owner attach
- proactive editor shutdown cleanup hook where integration allows
- focused tests for:
  - editor-owned attach/reuse
  - shell refusal while editor owner active
  - stale owner cleanup and recovery

Out of scope:
- multi-operator shared-host collaboration mode
- implicit cross-owner adoption
- full frontend redesign

## Done When
- editor ownership metadata is durable and validated in host attach path
- shell async local path refuses while active editor owner is present
- refusal/recovery behavior is test-backed and documented
- stale-owner fallback remains robust

## Related
- `544`
- `543`
- `542`
- `541`

## Progress
- 2026-05-19: implemented first exclusivity slice:
  - session-host records now carry owner metadata:
    - `owner_kind` (`shell` default)
    - `owner_id` (optional)
  - CLI async local ensure path now stamps owner metadata from environment:
    - `TOAS_OWNER_KIND` (default `shell`)
    - `TOAS_OWNER_ID` (optional)
  - shell refusal path landed:
    - when a live editor-owned host record is active, shell async attach is refused with explicit diagnostic
  - added focused async test for shell refusal against editor-owned host
