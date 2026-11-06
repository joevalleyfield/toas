Filed as: 261106-adaptive-token-estimator
FKA:
AKA: adaptive token estimator; dynamic char-to-token ratio; history-calibrated token estimation; empirical telemetry tokens
Legacy index:

keywords: transcript, telemetry, token-count, adaptive-estimation, calibration, llm-usage, ratio-tuning

Parent: `261106-token-count-decorations`
Related: `260825-visible-transcript-turn-ids`; `261105-user-turn-and-result-telemetry-decorations`

# Adaptive History-Calibrated Token Estimator

## Intent

Dynamically calibrate character-to-token (or word-to-token) ratios for transcript
telemetry estimation from recent transcript history where provider ground truth
(`llm_call` usage) is available, replacing hardcoded static ratios (`chars:4.0`)
with session-calibrated empirical rates that reflect actual content density
(code, unified diffs, JSON, prose).

## Calibration Mechanics

1. **Ground Truth Discovery**:
   - Inspect recent `llm_call` records in durable event history.
   - For an `llm_call` with `usage` (`prompt_tokens`, `completion_tokens`, `total_tokens`):
     - Calculate characters (or words) across prompt context and completion.
     - Derive empirical $\text{rate} = \frac{\sum \text{characters}}{\sum \text{tokens}}$.

2. **Windowing & Stability**:
   - Window across recent `llm_call` records (e.g. up to last 3 calls or until a token floor of $\ge 200$ tokens is accumulated) to prevent high variance on 1-line tool triggers.
   - Clamp empirical character ratios to safe bounds ($1.5 \le \text{rate} \le 6.0$ chars/tok) and word ratios ($0.3 \le \text{rate} \le 1.5$ words/tok).
   - Fall back smoothly to baseline (`4.0` chars/tok, `0.75` words/tok) when no `llm_call` records are present in history.

3. **Configuration & Compatibility**:
   - Support `session.telemetry_token_estimator = "adaptive"` (and `"adaptive:chars"`, `"adaptive:words"`).
   - Preserve explicit static heuristics (e.g. `"chars:3.5"`, `"words:0.75"`).
   - Make `"adaptive"` the default estimator in `SessionPolicy`.

## Acceptance Criteria

1. Implement `calibrate_token_estimator_ratio(items: list[dict], mode: str = "chars", *, default_rate: float = 4.0) -> float` in `toas.runtime.turn_telemetry`.
2. Update `estimate_tokens` to accept dynamically calibrated rates or support `"adaptive"` / `"adaptive:chars"` / `"adaptive:words"` with `items` context.
3. Update `compute_cumulative_tokens` to derive the adaptive ratio from preceding history when estimator mode is adaptive.
4. Set default `telemetry_token_estimator` in `SessionPolicy` to `"adaptive"`.
5. Add unit and integration tests covering cold starts (fallback default), windowed LLM call calibration, clamping on extreme ratios, and static overrides.
6. Achieve 100.00% statement coverage under `./scripts/check.sh`.

## Status & Verification

- Implemented `calibrate_token_estimator_ratio` in `toas.runtime.turn_telemetry`, windowing over recent LLM interactions to compute text units divided by tokens and clamping to safe bounds ($1.5 \le \text{chars/tok} \le 6.0$, $0.3 \le \text{words/tok} \le 1.5$).
- Updated `estimate_tokens` to support `"adaptive"`, `"adaptive:chars"`, and `"adaptive:words"` modes with history items.
- Updated `compute_cumulative_tokens` to use `"adaptive"` as default heuristic and pass accumulated history items into `estimate_tokens`.
- Set default `telemetry_token_estimator: str = "adaptive"` in `SessionPolicy`.
- Updated test suites with comprehensive calibration coverage (cold start fallbacks, LLM prompt+completion ratio derivation, clamping, static overrides).
- Executed `./scripts/check.sh` achieving 100.00% statement coverage across all 161 source files (3,781 passed).
