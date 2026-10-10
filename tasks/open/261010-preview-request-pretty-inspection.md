# Near-Literal Preview Request Pretty Inspection

Filed as: 261010-preview-request-pretty-inspection
FKA:
AKA: preview request pretty; preview request decoded; step preview pretty print; near literal request view
Legacy index:

keywords: cli, inspection, preview-request, ergonomics, inception

Parent: `260926-state-step-requirements`

Status: OPEN; support near-literal pretty-printed inspection of model request messages in toas step --preview-request

## Context and Motivation

`toas step --preview-request` outputs the exact JSON wire payload sent to the LLM API. Because model APIs accept request messages with a string `content` field, the entire state-step packet (`instructions`, `schema`, `tools`, `state`, `observation`) is serialized into a single JSON-encoded string.

In this raw wire view, multiline instructions have escaped `\n` characters and JSON structures inside the packet are condensed into escaped strings, making human operator inspection and debugging difficult without external pipelines (`jq`, python one-liners).

## Intent

Add an inspection option (such as `--pretty` or `--format pretty`) to `toas step --preview-request` that unpacks stringified message contents, rendering multiline text with unescaped newlines and pretty-printing inner JSON structures.
