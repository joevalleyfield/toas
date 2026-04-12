## Goal

Add a built-in TOAS capability to replay progressive prompt/session command sequences against current prompt assets for repeatable behavior checks.

## Why Now

Current validation relies on ad-hoc shell scripting to append turns and run `toas step`. A first-class replay runner would preserve multi-turn interaction shape while naturally consuming updated prompt assets, making regression checks easier and less error-prone.

## Scope

- define replay input format for ordered turn scripts (for example newline command list or YAML sequence)
- support incremental "append turn, step, capture output" execution
- persist compact artifacts (history snapshot, session tail, step outputs) for deterministic comparison
- keep replay execution within normal TOAS semantics (no hidden bypass path)
- document usage for dogfood/regression workflows

## Intended Behavior

- operators can run one command to replay a progressive session-shaping script
- replay reflects current installed TOAS/prompt assets without hand-editing shell scripts
- output is consistent enough to support lightweight behavioral regression checks

## Constraints

- preserve append-only durable history model
- no implicit mutation outside normal `step`/control operations
- avoid introducing a separate execution semantics fork

## Done When

- replay command/subcommand is implemented and test-covered
- at least one real-world progressive prompt-discovery script is captured as fixture/example
- docs include a practical replay workflow for prompt-layer tuning
