## Goal

Enable execution of user-authored multiline shell commands (including heredocs) through the explicit user-intent path, while clarifying/locking adoption semantics for assistant-proposed runnable content.

## Why Now

Task `308` preserves multiline loose-command shape, but the current execution trigger still expects single-line tail shorthand (`$ ...`). This blocks direct execution of preserved multiline commands and creates ambiguity around how assistant proposals become runnable user intent.

## Scope

- extend explicit user-shell execution detection beyond single-line `$ ...` tail form to support multiline command bodies
- support heredoc-bearing multiline commands in the user intent execution path
- define and implement clear adoption semantics:
  - assistant proposal -> user adoption node
  - user can mutate freely
  - execution remains explicit and user-owned
- evaluate operation/callable shell form parity:
  - ensure model-addressable `shell` operation remains bounded
  - ensure user-intent multiline execution remains separate and unbounded by tool allowlist
- preserve current two-step safety posture where appropriate (proposal then explicit user-run)

## Intended Inputs

- user shell extraction/execution in `src/toas/step.py`
- tool request/result durability wiring in `src/toas/cli.py` and `src/toas/graph.py`
- extraction/adoption mechanics in `src/toas/step.py`

## Intended Outputs

- multiline/heredoc commands can be executed via explicit user-intent flow
- no projection loss between adopted assistant proposal and executed user content
- clear, documented distinction between:
  - user-unbounded shell intent
  - bounded model-addressable `shell` tool

## Constraints

- no hidden shell rewriting or quote normalization
- no collapse of multiline content into lossy single-line representation
- keep execution explicit; avoid accidental auto-run of arbitrary user prose

## Non-Goals

- no broad redesign of tool registry policy
- no automatic execution of assistant output without user adoption/intent signal
- no shell parser beyond practical step-level intent extraction

## Done When

- user multiline command blocks (including heredocs) can execute intentionally through `toas step`
- durability records still capture `tool_request`/`tool_result` with clear user-intent provenance
- tests cover single-line shorthand, multiline commands, heredocs, and adoption->edit->execute flow
- docs explain the execution contract and safety boundary clearly
