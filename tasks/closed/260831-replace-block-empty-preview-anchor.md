# replace_block empty replacement preview anchor

Filed as: 260831-replace-block-empty-preview-anchor
FKA:
AKA: replace_block deletion preview; empty replacement context
Legacy index:
keywords: tooling, implementation, historical, correctness, projection
Status: closed

## Problem

`replace_block` successfully removes a matched block when `replacement_block` is
empty, but its confirmation preview is anchored at the beginning of the file.

## Acceptance criteria

- An empty replacement anchors the confirmation line range at the removed
  block's location in the resulting file.
- Non-empty replacement previews retain their existing behavior.
- A regression test covers removal of a non-leading block and its preview.

## Closure

The empty-replacement preview now anchors from the first matched block's
post-edit position. Regression and full-suite verification pass, including
3,051 tests and 100% total coverage.
