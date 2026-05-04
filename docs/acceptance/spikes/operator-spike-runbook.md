# Operator Spike Runbook

## Purpose
Run repeatable operator-mode spikes that exercise TOAS affordances directly and preserve durable artifacts for later distillation into acceptance scenarios.

## Baseline Loop
1. Create an isolated workspace.
2. Initialize a fresh transcript.
3. Prime context via TOAS affordances and step each addition into transcript state.
4. Choose a historical bounded work-unit to recreate (prefer prior code+test commit, not docs-only).
5. Run iterative operator turns with `toas step >> session.md` toward actual implementation.
6. Continue interactively until completion or first stable failure boundary after recovery attempts.
5. Preserve transcript + event-log artifacts at meaningful boundaries.
7. Distill outcomes against expected work-unit shape (behavioral equivalence, not exact patch text).

## Commands
```bash
tmp="$(mktemp -d /tmp/toas-operator-spike.XXXXXX)"
cd "$tmp"
git clone <subject-repo> repo
cd repo

printf '## TOAS:USER\n\n' > session.md
```

Preferred staging pattern (repo at chosen ref in isolated temp):
```bash
tmp="$(mktemp -d /tmp/toas-operator-spike.XXXXXX)"
git clone <subject-repo> "$tmp/repo"
cd "$tmp/repo"
git checkout <chosen-ref>
printf '## TOAS:USER\n\n' > session.md
```

If TOAS runtime repo differs from subject repo, prefer subject-scoped runner style:
```bash
uv run --project /path/to/toas toas step >> session.md
```
This keeps runtime tooling stable while operating on the chosen target workspace.

For each operator turn:
```bash
cat >> session.md <<'EOF'
## TOAS:USER

<turn content>
EOF
uv run toas step >> session.md
```

## Context Priming Order (Recommended)
1. Prompt template/fragment:
`/prompt session-start/templates/collaborative-builder_v1`
2. Tool lane grounding:
`/help tools`
3. Repo/process constraints:
ask assistant to read `AGENTS.md` and relevant task files.
4. Optional operational controls:
`/config ...`, `/extract ...`, `/replay ...`, `/queue ...`.

Step after each turn so artifacts are durable and visible to the next model call.

## Artifact Capture
When signal appears (progress or failure), copy both files:
```bash
cp session.md docs/acceptance/spikes/transcripts/operator-spikeN-session.md
cp .toas/events.jsonl docs/acceptance/spikes/transcripts/operator-spikeN-events.jsonl
```

Use monotonic `N` (or include current jj change id) to avoid collisions.

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
