Filed as: 261106-token-count-decorations
FKA:
AKA: cumulative token count decorations; token count up to this point; turn header token stamps; telemetry tokens
Legacy index:

keywords: transcript, telemetry, token-count, cumulative-tokens, compact-stamps, estimation, hybrid-usage

Parent: `260825-visible-transcript-turn-ids`
Related: `261105-user-turn-and-result-telemetry-decorations`; `261104-visible-turn-ids-and-compact-headers`

# Cumulative Token-Count Turn Telemetry Decorations

## Intent

Add cumulative token-count up to each turn into transcript telemetry decorations
(`## TOAS:USER`, `## TOAS:ASSISTANT`, and `## RESULT`) using a clean compact
format (`420 tok` for scalars under 1000, `1.8k` / `12.4k` with multiplier when
>= 1000), calculated via a hybrid model that uses exact provider usage where
available and a configurable fallback heuristic (`chars:4` / `words:0.75`).

## Formatting Rules

1. **Compact Style (`style='compact'`)**:
   - Scalar (< 1000): space plus `tok` label, e.g. `420 tok`.
   - Multiplier (>= 1000): multiplier suffix without label, e.g. `1.8k`, `12.4k`, `120k`, `1.2M`.
   - Examples:
     ```markdown
     ## TOAS:USER [alpha 11:40:00 12s 420 tok]
     ## TOAS:ASSISTANT [bravo claude-3-7-sonnet 11:42:00 1.2s 1.8k]
     ## RESULT [bravo.p1.o1 OK shell 11:42:02 45ms 2.1k]
     ```
2. **Inline & Comment Styles**:
   - `tokens=420 tok` / `tokens=1.8k` in inline bracket and comment attributes.

## Token Tracking Semantics

1. **Cumulative Up-To-This-Point**: Each turn displays the total token context
   accumulated from the session start through that turn.
2. **Hybrid Accuracy**:
   - When an LLM response provides exact usage (`total_tokens` / `prompt_tokens`),
     that ground truth anchors the running count.
   - For human user turns, tool result blocks, and offline projections, a configurable
     fallback heuristic estimates token volume.
3. **Configurability**:
   - `session.telemetry_token_estimator` in `SessionPolicy`, default `"chars:4"`
     (e.g. `len(text) / 4`), supporting `chars:<rate>` and `words:<rate>`.

## Acceptance Criteria

1. Implement `humanize_token_count(tokens: int | None) -> str | None` obeying
   scalar `420 tok` and multiplier `1.8k` rules.
2. Update `parse_turn_stamp` to parse both scalar `420 tok` and multiplier `1.8k`
   forms without ambiguity against IDs, timestamps, or durations.
3. Extend `format_turn_telemetry` with `tokens: int | None = None` across
   `compact`, `inline`, and `comment` styles.
4. Implement hybrid cumulative token accumulation across transcript turns using
   provider usage when present and configurable heuristic fallback (`chars:4` / `words:0.75`).
5. Decorate human `## TOAS:USER`, `## TOAS:ASSISTANT`, and `## RESULT` turns with
   cumulative token counts under active telemetry styles.
6. Achieve 100.00% statement coverage across all modified files under `./scripts/check.sh`.
