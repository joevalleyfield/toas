# 660: Shell Lane Spawn Semantics Unification Follow-up

## Goal

Track and defer a focused cleanup to eliminate unintended behavior differences between assistant and user shell execution lanes by centralizing spawn semantics behind explicit policy flags.

## Why

Recent investigation under `571` found a deterministic lane split:
- Assistant lane shell calls could hang for commands like `rg ...` when no explicit path was provided.
- User lane calls for the same command shape completed immediately.

Root cause was implicit stdin inheritance from different runtime call chains. Assistant lane inherited a non-terminal stdin context that allowed stdin-reading behavior; user lane did not present the same effective stdin mode.

Immediate mitigation is landed (`stdin=subprocess.DEVNULL` for assistant lane subprocess launch), but the deeper issue remains: lane behavior divergence is still partly driven by call-chain transport context instead of explicit policy.

## Scope

- Document current spawn semantics for user vs assistant shell execution:
  - stdin/stdout/stderr bindings
  - env normalization and overrides
  - timeout behavior
  - streaming vs buffered execution
- Design a shared shell spawn launcher seam used by both lanes.
- Keep lane differences explicit and policy-driven only (authorization, cwd limits, timeout caps, env restrictions).
- Preserve current user-facing contracts while removing implicit fd inheritance differences.
- Add regression coverage asserting parity for non-policy behavior across lanes.

## Non-Goals

- Broad tool-policy redesign.
- Reworking transcript/result projection formats.
- Large runtime ownership refactors outside this shell seam.

## Done When

- A shared spawn seam is adopted by both user and assistant shell paths.
- Non-policy lane parity tests cover stdin-sensitive commands (including ripgrep call shapes without explicit search paths).
- Any intentional lane difference is documented as explicit policy, not transport inheritance.

## Notes

- This is intentionally deferred. The tactical fix is sufficient for now, and this issue exists to avoid losing the architectural cleanup.
