Filed as: 261111-spill-threshold-tuning
FKA:
AKA: spill threshold data tuning; per-tool spill profile fit
Legacy index:

keywords: spill, threshold, projection, telemetry, data-collection, tuning, discovery
Depends on:
Related: `261111-skill-output-spill-exemption` (categorical exemption; this is the data-driven half)

# Tune spill thresholds from observed data, not a guessed constant

Status: OPEN; discovery/data-collection task, no implementation yet

## Objective

Replace the arbitrary fixed spill thresholds (`threshold_lines=40` /
`threshold_bytes=4000` defaults in `src/toas/config.py` `SpillProfile`)
with per-tool thresholds fit from observed usage. The current constants
trip on ordinary output (a 42-line skill block, a routine read) often
enough that the operator learns to ignore the spill signal. That frequent
"nag" is the signal to harvest and fit a policy from, not to suppress by
raising the global number.

## Why a data-collection task (not a one-off number)

- 40 lines / 4000 bytes were arbitrary; no evidence they are right for any
  tool.
- The right threshold differs per tool (a `search` with 200 matches vs. a
  42-line `read_file` vs. a `shell` stdout burst have very different
  useful-inline cutoffs).
- The fit depends on two observables that only exist in use: (a) how often
  each tool's output trips the current threshold, and (b) how much the
  operator actually re-reads from a spilled scratch file vs. ignores it
  (re-read = the inline cutoff was too aggressive; ignored = the spill was
  fine or the output was genuinely large).

## Scope (discovery phase first)

- Instrument / harvest, per tool: spill trip count, trip size distribution
  (lines/bytes at trip), and post-spill re-read count (operator reading the
  `.toas/scratch/<block_id>.txt`).
- Reuse existing machinery where it fits: `policy harvest`,
  `turn_telemetry`, `activity_health`. Do not build a new telemetry stack
  if the existing one can carry these signals.
- Produce a per-tool `SpillProfile` proposal (lines/bytes/mode) from the
  collected data, and a short write-up of the trip/re-read distributions
  that justify each number.
- Land the tuned profiles as config (`spill.profiles` already exists in
  `config_overrides.py`); the hard-coded 40/4000 default should become the
  documented fallback, not the only value.

## Out of Scope

- The categorical skill-output exemption (handled by
  `261111-skill-output-spill-exemption`). This task tunes the thresholds
  that apply to genuine discovery output; it does not re-litigate which
  categories are exempt from spilling entirely.

## Verification

- A data write-up with per-tool trip-rate and re-read-rate distributions,
  and a justified per-tool `SpillProfile` table.
- After landing tuned profiles: a before/after trip-rate comparison showing
  the operator-visible "nag" is reduced without blunting spill protection
  for genuinely large output (large outputs still spill).
- Config-driven, not hard-coded: the tuned values live in `spill.profiles`
  and the 40/4000 default is the documented fallback.
- `uv run pytest` / `./scripts/check.sh` green and 100% coverage for any
  production code the instrumentation adds.
