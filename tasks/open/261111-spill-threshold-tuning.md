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

## Discovery notes (2026-11-13)

### Existing collection paths

- `toas policy harvest` delegates to `src/toas/runtime/command_harvester.py`.
  It counts executable invocations and profiles command prefixes, subcommands,
  flags, and origins. It does not inspect general tool-result sizes or spill
  decisions.
- `src/toas/runtime/turn_telemetry.py` decorates transcript turns with token,
  duration, and timestamp information. It does not record tool spill outcomes.
- `src/toas/runtime/activity_health.py` reports async-run health and aggregate
  output/answer byte counters. Its snapshot has no tool identity, spill event,
  scratch-read event, or turn denominator for spill rates.
- Tool request/result events are already durable in `.toas/events.jsonl`, but
  their current payloads do not expose normalized spill-trip metadata or
  scratch reread relationships. Existing `read_file` requests could be
  searched for scratch paths, but the current logs contain none and this alone
  would not reliably identify subsequent reads through shell/script tools.

### Local-history check

Scanned the two local logs `.toas/events.jsonl` and
`.toas/broken_events/events.jsonl`, emitting only event/tool counts and Boolean
marker matches (no content, arguments, paths beyond repository-relative log
names, or secret values):

| Log | Tool requests | Results | Spill-banner matches | Scratch-path mentions |
| --- | ---: | ---: | ---: | ---: |
| `events.jsonl` | 15 (12 shell, 3 shell_script) | 19 | 0 | 0 |
| `broken_events/events.jsonl` | 57 (57 shell) | 58 | 0 | 0 |

The normal log has 218 `state_transition` and 218 `state_observation` records;
these are not spill observations. The histories therefore provide no observed
spill trips or scratch rereads, and cannot support per-tool trip-size
distributions, trip rates, or fitted thresholds. No `SpillProfile` proposal is
justified by this sample.

### Reproducible aggregate method

For each JSONL record, parse JSON in memory; count `tool_request` calls by
`payload[].tool_name` and `tool_result` records by `payload.tool_name` (or pair
with the request using `related_to` when absent). Inspect result text only for
the fixed spill-banner marker `Output exceeded threshold` and the fixed
`.toas/scratch/` marker. Print counts only. The scan used this method on the two
logs above; it did not print payload text, command arguments, or scratch names.

### Minimum collection gap

The trip decision must durably emit a bounded observation containing tool
identity, output line/byte counts, whether it spilled, and a stable block/event
identity. A later scratch read needs a durable or harvestable relationship to
that identity plus reader tool identity and read count. To calculate rates,
retain the denominator: all eligible tool outputs by tool, including outputs
that did not spill. A small aggregate-only harvester can then report per-tool
trip count/rate, trip-size distributions, and attributable reread rates without
retaining output contents or scratch paths. The existing local sample is too
small and spill-free for threshold fitting; continue gathering such records
before selecting values.
