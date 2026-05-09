# Operator Spike Runbook

## Purpose
Run repeatable operator-mode spikes that exercise TOAS affordances directly and preserve durable artifacts for later distillation into acceptance scenarios.

## Baseline Loop
1. Create an isolated workspace.
2. Enter the subject repo root and initialize a fresh transcript.
3. Prime context via TOAS affordances and step each addition into transcript state.
4. Choose a historical bounded work-unit to recreate (prefer prior code+test commit, not docs-only).
5. Run iterative operator turns with `toas step >> session.md` toward actual implementation.
6. Continue interactively until completion or first stable failure boundary after recovery attempts.
7. Preserve transcript + event-log artifacts at meaningful boundaries.
8. Distill outcomes against expected work-unit shape (behavioral equivalence, not exact patch text).

## Commands
```bash
tmp="$(mktemp -d /tmp/toas-operator-spike.XXXXXX)"
cd "$tmp"
git clone <subject-repo> repo
cd repo

mkdir -p .toas
printf '## TOAS:USER\n\n' > .toas/session.md
```

Preferred staging pattern (repo at chosen ref in isolated temp):
```bash
tmp="$(mktemp -d /tmp/toas-operator-spike.XXXXXX)"
git clone <subject-repo> "$tmp/repo"
cd "$tmp/repo"
git checkout <chosen-ref>
mkdir -p .toas
printf '## TOAS:USER\n\n' > .toas/session.md
```

If TOAS runtime repo differs from subject repo, prefer subject-scoped runner style:
```bash
uv run --project /path/to/toas toas step >> .toas/session.md
```
This keeps runtime tooling stable while operating on the chosen target workspace.

Preflight (mandatory before first step):
```bash
pwd
test -d .git
test -f .toas/session.md
```

For each operator turn:
```bash
cat >> .toas/session.md <<'EOF'
## TOAS:USER

<turn content>
EOF
uv run toas step >> .toas/session.md
```

Critical rule:
- Always append step output into the transcript (`toas step >> .toas/session.md` or the active configured session path).
- Do not redirect step output to side files during active turns.
- Reason: TOAS progression depends on what is actually present in transcript state; side-capturing stdout can create false negatives when rendered prompt/help output is not fed forward.
- After an assistant emits a YAML action block, run `toas step >> session.md` once before adding any new `TOAS:USER` turn.
- Do not append `Continue.` (or any new user prompt) until the corresponding `## RESULT` for the pending action is projected.
- Reason: asking for a new turn before execution commonly causes repeated action proposals (for example repeated `read_file`) and hides true chaining behavior.
- If a frontier gets noisy or malformed, truncate back to the last clean boundary and restep from there.
- Preferred clean boundary: right after a successful `## RESULT` tied to the last intended action.
- If using a non-default session filename (for example `.toas/session-purpose.md`), set it explicitly with `/session path <path>` and then verify the active path with `/session`.

## Context Priming Order (Recommended)
1. Prompt template/fragment:
`/prompts session-start` then a valid leaf `/prompt ...` for the staged commit.
2. Tool lane grounding:
`/help tools` only if prompt content does not already provide equivalent tool guidance.
3. Repo/process constraints:
prefer control-lane projection of local constraints with `$ cat AGENTS.md`, then tasking in `TOAS:USER`.
4. Optional operational controls:
`/config ...`, `/extract ...`, `/replay ...`, `/queue ...`.

Step after each turn so artifacts are durable and visible to the next model call.

## Artifact Capture
When signal appears (progress or failure), copy both files:
```bash
cp .toas/session.md docs/acceptance/spikes/transcripts/operator-spikeN-session.md
cp .toas/events.jsonl docs/acceptance/spikes/transcripts/operator-spikeN-events.jsonl
```

Use monotonic `N` (or include current jj change id) to avoid collisions.
Record the exact live paths used in notes (`tmp dir`, `repo root`, `active session path`) so later review can distinguish repo-root vs nested paths.

## Stop Criteria
- Continue while the loop yields actionable progress toward implementation (not just setup/discovery).
- Stop when:
  - a complete change/test loop is achieved, or
  - a stable failure boundary is identified after at least 1-2 concrete retry/recovery attempts aimed at reaching a positive end-state.
- Preserve artifacts before teardown.

## Notes
- Prefer TOAS affordances over bespoke operator prose whenever possible.
- Gentle operator nudges are allowed; avoid hand-writing implementation solutions.
- If slash-command outputs could re-trigger execution, inert them explicitly before restep.
- For functional spikes, ask for real bounded work that is possible in the staged workspace.
- Historical work-unit recreation is usually easier to evaluate than open-ended novel tasks.
- Avoid weak prompts like bare `Continue.` unless prior context is already clean and action-oriented.
- Never auto-select arbitrary `tasks/open/*` by filename order; choose a task explicitly relevant to the staged commit/work-unit.

## Streaming Troubleshooting Checkpoints (483)
- Verify local CLI streaming first with a deliberate slow-output shape; confirm output appears before terminal completion.
- Verify daemon/RPC watch semantics:
  - `poll` returns all output/events currently available.
  - `follow` waits for progression and still drains currently available output each tick.
- Verify Vim integration:
  - `ToasWatch` shows mid-run chunks (not terminal-only burst).
  - `ToasWatchDebug <run_id>` shows increasing `bytes_seen` and non-zero `chunk_len` before terminal status.
- If output appears only at terminal, rerun the same slow-output shape across both shell lanes (user shorthand and callable) to isolate lane-specific behavior.
