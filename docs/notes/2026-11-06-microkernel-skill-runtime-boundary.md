# TOAS Microkernel Architecture: Fast-Path Code Skills and Sugar Decoupling

Date: 2026-11-06
Author: Tim Myers & Assistant Pair
Status: Inception / Design Note
Related: `tasks/open/261106-standard-agent-skills-integration.md`, `tasks/open/261106-skill-specialization-and-script-distillation.md`

---

## 1. Executive Summary

TOAS is conceived as a transcript-oriented operator over append-only durable
history. Over time, extensive operator convenience sugar—such as `/model select`,
`/config set`, `/endpoint`, `/models refresh`, `/prompt`, and `/lens`—has accumulated
directly inside the core runtime, spanning several thousand lines in
`src/toas/runtime/operator_command_*.py` and a hardcoded command table in
`src/toas/step.py`.

This design note establishes the **Microkernel Boundary**: stripping the core
runtime down to its fundamental primitives (durable event logging, transcript
synchronization, consequence stepping, LLM transport, and OS primitives) while
recasting all operator command sugar as **Fast-Path Code-Only Skills**.

---

## 2. The Problem: Engine Congestion by Operator Sugar

Currently, the TOAS runtime engine bears the maintenance cost of two distinct concerns:

1. **The Kernel (The True System Engine)**:
   - Durable append-only event recording (`events.jsonl`, `graph.py`).
   - Transcript-to-graph projection and bidirectional synchronization (`session.md`).
   - Consequence resolution (`step_state_once`).
   - LLM transport and connection abstraction (`llm.py`).
   - Low-level OS capabilities (`read_file`, `write_file`, `replace_block`, `shell`).

2. **Operator Sugar & Administrative Userland**:
   - Argument parsing for model selection (`/model select ENDPOINT MODEL`).
   - Target and endpoint catalog inspection and formatting.
   - Interactive configuration mutation (`/config set <dotted_key> <val>`).
   - Interactive prompt fragment and template browsing (`/prompt ...`).

Bundling this userland logic into the core engine has several negative consequences:
* **Bloat**: Large monolithic modules (`operator_command_prompt_workspace.py` >1,500 lines).
* **Asymmetry**: Humans type `/model select`, but models cannot easily leverage the same syntax or share the exact same execution machinery.
* **Extensibility Barrier**: Users cannot introduce new slash commands or workflows without modifying the core TOAS repository.

---

## 3. The Solution: Fast-Path Code-Only Skills

In standard agent ecosystems, a skill is commonly viewed as a prompt runbook
instructing an LLM how to reason through a workflow.

We define a **Fast-Path Code-Only Skill** as a skill that operates in
**deterministic mode**:
* **No LLM Generation**: It never calls a model; token expenditure is zero.
* **Instant Execution**: Runs locally in milliseconds via Python code or scripts.
* **Event & Consequence Emission**: Rather than mutating hidden in-memory state,
  it outputs standard TOAS result nodes, event records, or policy directives.

```text
┌────────────────────────────────────────────────────────┐
│ Operator / Model Invocation: /model select gpt-4o      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Skill Dispatcher: Resolves alias '/model'              │
│ Target: skills/toas-model/scripts/model_ctl.py         │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Deterministic Execution: Validates target in catalog   │
│ Emits: policy_update(key="llm.target", val="gpt-4o")   │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ TOAS Kernel: Incorporates policy event into graph;     │
│ Next LLM step immediately uses target 'gpt-4o'         │
└────────────────────────────────────────────────────────┘
```

---

## 4. Architectural Invariants Preserved

1. **No In-Memory Sidecar State**:
   A common concern when moving commands into external scripts or skills is
   how daemon state is mutated. Because TOAS already models configuration and
   targets through explicit result nodes and `policy_update` events, code-only
   skills output the exact same structured consequence payloads. The kernel
   ingests the payload and updates the event log.
2. **Operator/Model Symmetry**:
   Because `/model select` is backed by a standard skill with a schema, a model
   agent running in an autonomous lane (`step n`) can invoke the exact same skill
   using standard tool calls (`operation: toas-model, arguments: {action: select, target: ...}`).
3. **Progressive Layering**:
   - Built-in sugar ships as bundled core skills (`toas/assets/skills/toas-model/`,
     `toas/assets/skills/toas-config/`).
   - Workspaces can override them in `.agents/skills/` if a repository requires
     custom policy constraints.

---

## 5. Roadmap & Phasing

* **Phase 1**: Introduce the standard skills discovery and dynamic slash-command
  aliasing engine (`tasks/open/261106-standard-agent-skills-integration.md`).
* **Phase 2**: Implement fast-path execution mode in the skill runtime, allowing
  skills to bypass model generation when companion scripts return final consequence.
* **Phase 3**: Migrate `/model` and `/config` helper commands out of `src/toas/runtime/`
  into bundled fast-path skills, verifying 100% backward compatibility.
