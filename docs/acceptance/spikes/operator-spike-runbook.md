# Operator Spike Runbook

## Purpose
Run repeatable operator-mode spikes that exercise TOAS affordances directly and preserve durable artifacts for later distillation into acceptance scenarios.

## Baseline Loop
1. Create an isolated workspace.
2. Initialize a fresh transcript.
3. Prime context via TOAS affordances and step each addition into transcript state.
4. Run iterative operator turns with `toas step >> session.md`.
5. Preserve transcript + event-log artifacts at meaningful boundaries.
6. Stop on completion or first clear failure boundary.

## Commands
```bash
tmp="$(mktemp -d /tmp/toas-operator-spike.XXXXXX)"
cd "$tmp"
git clone <subject-repo> repo
cd repo

printf '## TOAS:USER\n\n' > session.md
```

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
- Continue while the loop yields actionable progress.
- Stop when:
  - a complete change/test loop is achieved, or
  - a stable failure boundary is identified.
- Preserve artifacts before teardown.

## Notes
- Prefer TOAS affordances over bespoke operator prose whenever possible.
- Gentle operator nudges are allowed; avoid hand-writing implementation solutions.
- If slash-command outputs could re-trigger execution, inert them explicitly before restep.
