Filed as: 260927-state-step-raw-response
FKA:
AKA: state-step response-only call; raw model response probe
Legacy index:

keywords: runtime, implementation, follow-on, projection, observability

Parent: `260926-state-step-requirements`
Depends on: `260927-state-step-request-preview`

# Print The Unaltered State-Step Model Response

## Objective

Add a model-response preview alongside the request preview. `toas step
--preview-request` prints the request without calling the model; `toas step
--preview-response` sends the same request through the configured invocation
and prints the returned assistant content without accepting it as a
state-step proposal. The flags compose, printing the request before the
response when both are selected. Keep `--preview` as a compatibility alias
for `--preview-request`.

## Desired Behavior

- Reuse the same packet and request-message construction shown by
  `toas step --preview-request`, plus TOAS's normal model, endpoint, transport, and
  retry resolution.
- Print the model adapter's returned content string verbatim, preserving its
  whitespace, JSON formatting, and fences. Do not parse, validate, trim,
  reformat, or otherwise normalize the content.
- Do not apply a state patch, create a pending batch, execute proposed calls,
  alter the editable transcript, or append state-transition/diff/snapshot/tool
  records.
- Preserve ordinary model-call audit and configured trace behavior, while
  keeping the displayed content separate from diagnostic framing. If output is
  empty, preserve that fact without inventing a response body.
- Respect the next-step phase: do not send a model request when `step` would
  execute a pending batch or stop at a terminal state; report that phase.

## Acceptance Criteria

- A deterministic injected model response is emitted byte-for-byte at the
  content-string boundary, including leading/trailing whitespace and fences.
- Malformed JSON is still printed unchanged; it is not treated as an error by
  the response-only operation.
- The configured model path and request messages match `toas step --preview-request`.
- No state-step or transcript mutation occurs, and proposed tool calls never
  execute.
- Provider failures remain visible and auditable through existing model-call
  diagnostics.

Status: Complete.

Implementation: Added composable `--preview-request` and `--preview-response`
flags to `toas step`; retained `--preview` as a request-preview alias. Response
preview writes the ordinary `llm_call` audit record, prints successful content
without adding formatting, and returns before state acceptance or tool
execution. Non-inference phases are reported without invoking the model.
