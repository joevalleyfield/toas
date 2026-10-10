# Direct Tool-to-Artifact Capture

Filed as: 261010-direct-tool-artifact-capture
FKA:
AKA: tool call save_as artifact; direct artifact capture; tool result to artifact
Legacy index:

keywords: runtime, tools, state, artifacts, inception

Parent: `260926-state-step-requirements`
Related: `261009-explicit-reference-expansion-and-report-projection`

Status: OPEN; allow tool calls to declare an artifact label and auto-populate state.artifacts upon execution

## Context and Motivation

Persisting tool output into `state.artifacts` currently requires a two-turn ceremony: the model issues a tool call in Turn N, receives the output or scratch path in Turn N+1's ephemeral observation, formulates an explicit reference string, and patches `state.artifacts` so the content is available in Turn N+2.

This introduces turn latency and puts bookkeeping burden on the model to track scratch paths and reference syntax. At the moment of requesting a tool, the model already knows whether it wants the result saved into its durable state.

## Intent

Allow tool calls to declare an artifact target (e.g. `artifact: <label>` or `save_as: <label>`) so the runtime automatically captures the resulting output into `state.artifacts` upon execution, making it immediately available in state on the subsequent turn.
