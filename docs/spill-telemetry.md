# Spill telemetry

Newly executed tool results collect spill observations by default. No output text,
command arguments, file paths, transcript identifiers, or workspace identifiers
are added to the telemetry fields. For each rendered output block that is
eligible for spilling, TOAS records the tool bucket, original line and byte
counts, whether that block spilled, and a stable block identity only when it
spilled. One tool call can yield multiple eligible blocks, such as separate
stdout and stderr; each block is one observation.

The telemetry is stored locally alongside the durable result record. Existing
result payloads remain available to TOAS as before. Collection applies to the
standard rendered tool-result and direct user-shell result paths. Historical
records without telemetry remain unobserved; rendering or replaying an old
result does not create a new observation. Tool results that do not use the
spill renderer are not in the eligible-output denominator.

After a sample has accumulated, print a human-readable summary with:

```sh
toas spill telemetry
```

Export the fixed-schema aggregate JSON without result text, paths, IDs,
commands, or per-event rows with:

```sh
toas spill telemetry --json
```

The JSON includes eligible output counts, spill counts and rates, fixed line
and byte size buckets for all eligible outputs and spilled outputs, plus
collection coverage. `unobserved_result_records` counts older tool and direct
shell results that predate collection. Reread matching scans locally for exact
known spilled block IDs in later `read_file`, model-addressable `shell` and
`shell_script`, and direct shell request text. It counts unique request/block
pairs and excludes references from the request that produced the spill or
references before the spill was recorded. These are inferred references: a
command can mention a path without opening it. Other read mechanisms are
unobserved. The aggregate export includes only counts, fixed buckets, and
fixed-schema labels; block IDs and raw request text never leave the local
aggregation process.

Current collection does not assign spill decisions to state-step tool outputs,
which use a separate execution/result protocol and do not use this renderer.
