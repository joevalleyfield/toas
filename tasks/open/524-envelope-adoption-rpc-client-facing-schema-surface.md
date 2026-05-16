# 524 Envelope Adoption For RPC Client-Facing Schema Surface

## Objective
Define and validate a stable RPC client-facing schema surface for envelope-bearing payloads, including compatibility expectations for older consumers.

## Scope
- document RPC payload schema expectations at client boundary
- add compatibility tests around missing/extra envelope fields
- preserve default behavior for existing clients

## Done When
- schema surface is documented and test-covered
- compatibility behavior is explicit for envelope-present vs legacy-only payloads

## Related
- `517` transport contract
- `523` daemon dispatch contract docs/tests
