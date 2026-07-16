# Durable History Preview Contract

Status: DIRECTIONAL
Task Link: `260628-durable-derived-history-previews`

## Decision

A rich history preview is a durable **derived reading aid**, not a shorter
message, not a transcript rewrite, and not a context-lens artifact.

The existing `lens_artifact` family is deliberately the wrong home: it is
title-keyed, replaceable working context that may shape model input. A history
preview instead needs immutable source attribution and must remain inert unless
an explicit history surface asks for it.

## Proposed Record

Use a new non-message record family, `history_preview`:

```yaml
kind: history_preview
payload:
  id: hp-42
  source:
    message_id: n71
    content_digest: sha256:...
  text: "Root-divergence fix landed; focused regression passed."
  derivation:
    kind: llm_summary          # or manual, heuristic
    recipe: history-preview/v1
    model: local/qwen3         # optional for non-model derivations
  intended_for: history_row    # optional: history_row, graph_node, search_hit
  supersedes: hp-31            # optional
```

Required fields are `id`, `source.message_id`, `source.content_digest`,
non-empty `text`, and `derivation.kind`. The digest is not an attempt to make
message identity content-addressed; it proves exactly which immutable message
revision was summarized and makes imports or corruption visibly non-equivalent.

## Selection and Freshness

- Cheap deterministic preview heuristics remain the default everywhere.
- A surface may request stored previews explicitly (for example a future
  `history --previews`), never silently replace its ordinary preview with one.
- The newest valid record for `(message_id, content_digest, intended_for)` wins
  when linked by `supersedes`; otherwise records coexist as alternatives.
- A preview is **source-valid** when its message id and digest match the chosen
  history scope. It is not made invalid merely because a better recipe/model
  exists later.
- A missing source, digest mismatch, or ambiguous source scope renders the
  preview unavailable—not an alternate transcript truth.

## Write Policy

No step-time generation and no background loop in the first version. Rich
previews should enter history only through an explicit operator request, with
the derivation recipe recorded. This supports both a manually authored note and
an explicitly requested model summary without making routine history reads
expensive or nondeterministic.

## Reading Shape

The useful creative affordance is a **margin**, not a rewrite:

```text
n71  ASSISTANT  "```yaml"
      ↳ Root-divergence fix landed; focused regression passed.
        [derived: llm_summary history-preview/v1]
```

The raw first-line preview remains visible, so an operator can see the source
and judge whether the derived note is helping. A compact marker should expose
the derivation without flooding routine history rows with provider metadata.

## Example Flow

1. An operator selects a noisy but important result message `n71`.
2. They explicitly request a preview using a named recipe.
3. TOAS writes `history_preview` with the source id, digest, text, and recipe.
4. Ordinary `history` remains fast and heuristic-only.
5. An explicit preview-aware surface discovers the matching record and renders
   it as an indented margin. It never feeds that material into `llm-input` or
   transcript reconstruction.

## First Implementation Criterion

Do not implement the record merely because the schema is available. Open a
focused implementation task only when one operator-facing surface is chosen
for explicit preview display and an explicit authoring request is specified.
That keeps the derived lane from becoming stored decoration with no reader.
