# Rolling Tool Failure Memory in Compound Observation

Filed as: 261010-rolling-tool-failure-memory
FKA:
AKA: rolling failure memory; recent tool attempt memory; dead end tracking; observation failure trail
Legacy index:

keywords: runtime, observation, state-step, error-recovery, in-context-learning, inception

Parent: `260926-state-step-requirements`
Related: `261009-batch-tool-non-fatal-execution-mode`

Status: OPEN; maintain a compact rolling log of recent tool attempts and failures in observation to prevent repeating dead ends

## Context and Motivation

Under state-step's single-turn ephemeral observation model, tool outcomes disappear from context on subsequent turns unless the model manually summarizes them into `state.notes`.

When a tool attempt fails (such as issuing a command with an invalid relative path), the model adapts on the immediate next turn, but several turns later it has no memory of the earlier failure and repeats the exact same failing command. Without a trail of recent attempts, the model lacks opportunity for in-context learning across turns.

## Intent

Provide a compact rolling record of recent tool attempts and failure outcomes in the compound observation so the model retains awareness of recent dead ends and avoids repeating known errors.
