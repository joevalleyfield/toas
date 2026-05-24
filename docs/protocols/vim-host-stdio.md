# TOAS Vim Host Stdio Protocol

## Lifecycle

Vim owns the host lifecycle. `toas host` is a child process of Vim.

## Stream Purity

Stdout is protocol-pure newline-delimited JSON. Every complete line on stdout must be exactly one JSON frame. No logs, banners, tracebacks, progress text, or human-readable diagnostics may be written to stdout.

Stderr is diagnostic side-channel output only. Stderr has no protocol semantics.

Stdout ownership is exclusive to the protocol serializer.

Only the protocol framing layer may write to stdout. All library logging, print/debug output, subprocess stdout, and traceback text must be redirected, captured, suppressed, or rerouted away from protocol stdout before frame emission.

Subprocesses invoked by the host must default to:
- stdout captured
- stderr captured or inherited intentionally
- no inherited direct access to protocol stdout

## Framing and Encoding

Frame boundary is `\n`.

Frame encoding is UTF-8 JSON text.

NUL bytes are transport noise and should be ignored, not treated as delimiters.

The host must flush stdout after each emitted frame.

## Reader Model (Vim)

Vim reads in timer-sliced callbacks. Parsing must be resumable:
- append incoming bytes to RX buffer
- strip/discard NUL bytes
- split complete newline-terminated frames
- retain incomplete trailing bytes
- decode complete frames only

## Frame Types and Semantics

Request/response commands and async pushed stream events may share the same stdout frame stream.

Frames must include enough fields to distinguish request responses, stream events, completion, errors, and shutdown/fault reporting.

Completion of streamed output is semantic only when an explicit terminal frame is received.

EOF means host death or transport closure, not successful completion.

### `stream_subscribe` Lifecycle Frames

`stream_subscribe` follow sessions use this lifecycle on stdout:
- `push_ack` once, after the first successful upstream read
- zero or more `push_event` frames
- exactly one `push_complete` terminal frame

If the upstream read fails before the first successful read, the host emits the
single upstream error response frame and terminates the subscribe request
without synthetic `push_ack`/`push_complete`.

Forwarding requirement:
- every emitted subscribe frame must be written and flushed immediately
- hosts must not accumulate a full subscribe frame batch before writing

## Ordering

Frames are transport-ordered by emission sequence.

Per-stream `seq` values must be monotonic and replay-stable.

Consumers may use `seq` for:
- dedupe
- gap detection
- deferred render ordering
- replay validation

Transport order alone must not be assumed sufficient for semantic reconstruction across deferred/coalesced rendering.

## Backpressure

Backpressure means producer output exceeds Vim’s ability to parse/render promptly.

Track it with:
- pending frame count
- RX buffer bytes
- deferred frame count
- render latency
- dropped/coalesced frame count, if applicable

Policy:
- bound per-tick parsing/rendering work
- defer remaining complete frames
- preserve control-frame order
- allow content-frame coalescing only when final rendered text is preserved
- never let completion pass earlier content
