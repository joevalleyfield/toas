# Activity health and stall reporting

TOAS uses bounded activity-health observations instead of always-on wire logs
for normal stall diagnosis. Health is observational: reading it does not append
an event, advance a stream cursor, or change run terminality.

## User surfaces

For a Vim run:

```vim
:ToasWatchHealth [run_id]
:ToasWatchDebug [run_id]
```

`ToasWatchHealth` is the compact operator view. It reports transport state,
pending events, timeout status, decode/apply/render timing, resubscription and
recovery counts, transport transitions, terminal transitions, and the latest
transition. `ToasWatchDebug` retains the structured observer object and a
bounded recent history for deeper inspection.

Host stream clients receive the host observer on `push_complete`. It includes
bounded pacing counters and a `transition_summary` for timeout, upstream
transport loss, and terminal outcomes.

Runtime clients receive the producer-owned `health` object on `watch` and
`stream_read` responses. Producer health and adapter observations are separate:
the producer owns activity state and phase; Vim/host own delivery, queue, and
transport observations.

## Vocabulary

Producer state is one of:

- `progressing`: recent meaningful producer activity;
- `idle`: no meaningful producer progress for the configured warning window;
- `backlogged`: an observer has evidence of queued consumer work;
- `transport_lost`: an observer has explicit transport-loss evidence;
- `terminal`: the producer has reached success, failure, or cancellation.

Severity is `info`, `warning`, or `critical`. A quiet run is not automatically
transport loss, and a timeout does not identify the model, host, or editor as
the cause. Unknown causes remain `unknown` rather than being guessed.

Common producer reasons are `recent_activity`, `no_progress`,
`consumer_backlog`, `subscribe_timeout`, `host_unavailable`,
`terminal_success`, `terminal_failure`, and `cancelled`.

Adapter transition summaries aggregate `resubscribe`, recovery, transport
loss/recovery, and terminal transitions. They expose counters plus the latest
kind/reason/timestamp; they do not retain one record per poll or frame.

## Reading a silent stall

When no event arrives, the timeout reporter is the evidence. A Vim health line
with `timeout=1:subscribe_timeout` means the subscribe window crossed its
configured first-frame or inter-frame timeout. It also reports pending queue
depth and retry/recovery counters. The report is throttled to one update per
silent timeout phase and resets when a subscribe acknowledgement arrives.

Interpretation:

- timeout with `transport=open`, no pending events, and no recovery: the
  observer knows only that delivery made no progress;
- timeout followed by a resubscription and recovery: the stream window was
  renewed, but the cause remains unknown;
- explicit `transport=lost`: the adapter observed host/channel failure;
- terminal failure: use the terminal error and producer health as authoritative
  failure evidence, not the adapter timeout alone.

## Wire tracing

Raw host and Vim wire traces are forensic tools and are disabled by default.
Enable them only when frame-level investigation is needed:

```sh
TOAS_HOST_STDIO_WIRE_LOG_ENABLED=1
TOAS_HOST_STDIO_DIAG_LOG_ENABLED=1
```

In Vim:

```vim
let g:toas_local_host_wire_log = 1
```

Host diagnostic events still flow through the stdlib DEBUG logger when file
capture is disabled. Structured health and terminal/error responses do not
depend on trace files.

## Provisional policy

The producer idle warning default is 5 seconds. Timeout, backlog, and critical
thresholds remain policy rather than causal conclusions until real stall
reproductions are available. After evidence arrives, tune thresholds and
classifications without changing the observer/producer ownership boundary.

Timing controls should remain independently configurable. A future profile
should be a named set of explicit values—not a single multiplier—covering at
least producer idle warning, first-frame timeout, inter-frame timeout, host
request deadline, and recovery/resubscribe timeout. The precedence should be:

1. per-run or per-surface override;
2. selected profile value;
3. documented default.

This lets a fast interactive profile and a patient batch profile coexist while
preserving enough field-level control to investigate one suspected seam.

The runtime currently defines `default`, `interactive`, and `patient` presets
as policy data. Existing Vim and host knobs remain compatible while adoption is
incremental; selecting a profile does not silently overwrite an explicit
surface or run-level override.
