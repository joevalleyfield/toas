# 367: Model-addressable apply_patch lane

- **Status**: Closed
- **Resolution**: Fixed

## Summary

Implemented a model-addressable `apply_patch` capability so assistant-side edits can use structured patch payloads instead of shell heredoc workarounds.

## What Landed

1. Added `apply_patch` to the tool registry (`arguments.patch` required).
2. Implemented strict patch parsing for `*** Begin Patch` / `*** End Patch` envelopes with:
   - `*** Add File: ...`
   - `*** Delete File: ...`
   - `*** Update File: ...` (optional `*** Move to: ...`)
3. Enforced strict update semantics: context mismatch fails the hunk instead of relocating edits.
4. Added tests for update success, mismatch failure, and add+delete behavior.
5. Added capability advertisement/help coverage so models discover and prefer the lane.
