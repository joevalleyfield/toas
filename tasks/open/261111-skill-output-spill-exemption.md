Filed as: 261111-skill-output-spill-exemption
FKA:
AKA: skill spill nag; skill output inline
Legacy index:

keywords: tool-output, spill, projection, skill, rendering, operator-ergonomics
Depends on:
Related: `261111-spill-threshold-tuning` (named follow-on, data-driven)

# Skill activation output should not spill

Status: OPEN; defect confirmed, seam located, awaiting implementation

## Objective

Stop skill-activation output from being routed through the spill threshold.
A skill's instruction block is the operator's explicitly-requested, bounded,
deterministic payload; spilling it to a scratch file forces the operator to
go read the file to see what the skill just told them to do, which defeats
the purpose of activating it inline.

## Defect (observed)

Activating the `record-task` skill produced a 42-line / ~2 KB instruction
block that was projected as:

    Output exceeded threshold (2 KB, 42 lines); spilled to
    .toas/scratch/ib_...txt

The default spill threshold is `threshold_lines=40` /
`threshold_bytes=4000` (`src/toas/config.py` `SpillProfile` defaults). The
42-line skill block crossed the 40-line line-threshold by 2 lines and
spilled. This is a symptom of a broader under-tuned threshold (see follow-on),
but the skill case is categorical and should be fixed regardless of what the
threshold number eventually is.

## Root Cause / Seam

- Skill output is projected through the same generic spill gate as
  discovery output (file reads, shell, search):
  `src/toas/tools_cluster/rendering.py` `render_*` functions call
  `render_fenced_output(..., **spill_kwargs)` with `threshold_lines` /
  `threshold_bytes` from the result (defaulting to the 40/4000 policy).
- `rendering.py` has NO skill special-case (search for "skill" in that file
  returns nothing), so a skill result is spilled identically to any other
  oversized tool output.

## Scope (immediate, categorical)

- Exempt skill-activation output from the spill path: project it inline,
  not via `extract_spill_preview`'s threshold gate. A 42-line OR 420-line
  skill block is the operator's payload and belongs inline.
- This is a categorical exemption, NOT a threshold change. Do not raise the
  global 40/4000 defaults to fix this; that would blunt real spill
  protection for genuine discovery output.
- Keep the exemption localized to the skill result rendering path so the
  general spill policy is untouched.

## Out of Scope (named follow-on)

- **`261111-spill-threshold-tuning` (data-driven):** the actual 40-line /
  4000-byte balance is arbitrary. Figuring out the right per-tool threshold
  is a DISCOVERY / data-collection task: measure how often each tool's
  output trips the current threshold, how much the operator re-reads from
  spilled scratch files vs. ignores, and fit a per-tool `SpillProfile` from
  that. The frequent spill "nag" is the signal to harvest, not to suppress.
  Likely fed by existing `policy harvest` / `turn_telemetry` /
  `activity_health` machinery. This task does NOT guess the number.

## Verification

- `uv run pytest` green; `./scripts/check.sh` green; 100.00% statement
  coverage on the touched rendering path.
- Operator-perspective end-to-end (mandatory, projection surface):
  - Activate a skill whose `SKILL.md` block exceeds 40 lines -> the full
    instruction block renders INLINE, no "spilled to .toas/scratch" line,
    no forced re-read of a scratch file.
  - Confirm a genuine oversized discovery result (e.g. a large `read_file` /
    `search`) STILL spills under the existing policy (exemption did not leak).
- Test the public rendering seam (the skill result render entrypoint), not
  private `_` helpers.
