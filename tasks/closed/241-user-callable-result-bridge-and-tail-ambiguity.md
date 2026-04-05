## Goal

Reduce user-facing ambiguity around repeated callable YAML execution by making post-execution continuation boundaries explicit in projected output.

## Problem Synopsis

Current callable extraction executes when the last fenced YAML block in a message parses as a plan, even when prose appears after that block.

This can feel sticky in user flow:
- user message with YAML plan executes
- transcript appends `## RESULT`
- continuing text can be perceived as part of the same execution cadence unless an explicit `## TOAS:USER` boundary is inserted manually

Observed consequence:
- operators may repeatedly insert explicit user headings to break the perceived loop
- this is especially visible in dogfooding sessions where call/prose/call patterns are common

## Scope

- treat this as a projection/UX bugfix first (not parse-rule change)
- emit a synthetic blank `## TOAS:USER` block before `## RESULT` for user-callable executions
- keep durable linkage unchanged (`tool_request` / `tool_result` remain related to the executed frontier message)
- document rationale and behavior in tests

## Intended Inputs

- existing callable extraction semantics (last YAML block)
- existing assistant-side synthetic user bridge behavior
- current CLI block projection/output path

## Intended Outputs

- consistent bridge behavior for both assistant- and user-origin callable executions
- clearer continuation affordance without changing execution parsing rules
- regression tests capturing expected stdout shape and unchanged durable records

## Constraints

- do not change callable extraction semantics in this task
- do not require terminal YAML block in this task
- do not alter message-event parentage or tool record linkage

## Non-Goals

- no terminal-block enforcement policy yet
- no parser fuzzing or new callable syntax

## Decision Rationale

Why bridge-first:
- low risk: projection-only change
- preserves existing flexibility for assistant trailing commentary
- reduces perceived "auto-call loop" pressure for users without forcing stricter authoring rules

Future option (separate decision):
- consider user-only terminal-block enforcement if ambiguity remains high after bridge rollout

## Done When

- user-callable and assistant-callable executions both project a user bridge before result blocks
- durable records remain unchanged and correctly related to executed frontier message
- tests explicitly cover prior ambiguous flow and expected bridge output
