# Context Construction Without Prefix Caching

## Insight

In a runtime with no prefix caching, aggressively constraining context and constructing prompts mechanically can produce outsized performance and reliability gains.

## Why It Matters

Without cached prefixes, every extra token is paid again on every inference. Narrative or loosely assembled context becomes expensive quickly and can also increase model drift.

## Implications

- Prefer deterministic context projection from durable records over freeform recap.
- Keep only frontier-relevant content in prompt input.
- Make optional context retrieval explicit instead of always included.
- Treat strict context budgeting as a product-level capability, not just a prompt tweak.

## Open Questions

- Which context classes should always be included versus lazily fetched?
- How should we expose context budget policy in operator-facing configuration?
