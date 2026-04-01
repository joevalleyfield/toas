# TOAS Roadmap

## Purpose

This roadmap starts from the now-closed bootstrap tasks and charts a path from the current core toward the full TOAS vision and the broader capabilities it should enable.

`vision.md` explains the system model.

This document explains what still needs to be built, in what order, and why.

---

## Current State

The current implementation has a coherent core:

- transcript parsing and step semantics
- graph-native message history
- durable control records for binding
- transcript and LLM-input projection from lineage
- durable tool request/result records

This is enough to prove the model, but it is not yet a complete operator runtime.

---

## Capability Tracks

The work ahead falls into five tracks.

### 1. Core Graph And Operator

Keep the history/transcript/operator contract correct and legible.

Focus:
- branch-aware alignment
- head selection ergonomics
- replay and projection correctness
- anchor usage beyond nominal storage

### 2. LLM Integration

Turn the current abstract generation/execution hooks into a real model interface.

Focus:
- provider/model abstraction
- request construction from projected lineage context
- response normalization
- retry/error behavior
- durable recording of model interactions where appropriate

### 3. Tool Library

Turn structured callable intent into a reusable capability surface.

Focus:
- tool registry
- argument validation
- execution policy
- result normalization
- durable request/result records with traceable provenance

### 4. Prompt Library

Treat prompts as explicit system assets.

Focus:
- reusable prompt templates for generation
- extraction prompts for tool intent
- repair prompts for malformed outputs
- prompt versioning and selection

### 5. Ergonomics And Scale

Make the system pleasant and durable as usage grows.

Focus:
- branch navigation UX
- transcript rebuild ergonomics
- anchor/index optimization
- history inspection tools

---

## Milestones

## Milestone 1: Core Runtime Maturity

Goal:
- make the current core behave like an intentional operator runtime, not a promising prototype

Work:
- surface lineage/head selection more explicitly
- use anchors for actual projection/alignment shortcuts
- tighten branch-aware continuation semantics around non-tip heads
- decide where projection belongs in the operator surface

Tasks:
- `110`: milestone umbrella
- `111`: head selection and inspection
- `112`: anchor-backed alignment and projection
- `113`: non-tip continuation semantics
- `114`: projection commands

Not now:
- no merge semantics
- no complex branch UI

## Milestone 2: Real LLM Integration

Goal:
- connect projected lineage context to actual model calls

Work:
- provider abstraction
- model request/response layer
- context assembly from `project_llm_input(...)`
- failure and retry policy
- durable records for model-facing operations if needed

Tasks:
- `120`: milestone umbrella

Not now:
- no multi-provider orchestration complexity up front
- no aggressive caching strategy before correctness

## Milestone 3: Real Tool Library

Goal:
- make tools a usable, intentional subsystem

Work:
- tool registration/discovery
- structured argument contracts
- execution adapters
- result shaping into durable records and canonical transcript consequences
- policy boundaries around what tools may run

Tasks:
- `130`: milestone umbrella

Not now:
- no giant kitchen-sink library at first
- no implicit tools hidden in prompts

## Milestone 4: Prompt Assets

Goal:
- make prompting legible, reusable, and replaceable

Work:
- prompt storage/layout conventions
- prompt selection rules by operator phase
- prompt versioning
- extraction/generation/repair prompt separation

Tasks:
- `140`: milestone umbrella

Not now:
- no premature prompt optimization without observability

## Milestone 5: Operator Ergonomics

Goal:
- make the system usable for longer-lived sessions and larger histories

Work:
- branch/head inspection commands
- transcript rebuild commands
- anchor/index optimizations
- better debugging and history introspection

Tasks:
- `150`: milestone umbrella

Not now:
- no heavy UI layer unless the CLI/editor workflow proves insufficient

---

## Near-Term Priorities

The next few concrete priorities should be:

1. Real LLM integration over lineage-projected input
2. A minimal tool library with durable execution contracts
3. A prompt library for generation, extraction, and repair
4. Practical use of anchors beyond storage

Those are the pieces most likely to broaden the system from a well-specified core into a usable runtime.

---

## Boundaries

The roadmap should preserve these constraints:

- no hidden mutable state outside durable history unless clearly justified
- no conflation of message events with control/tool records
- no rewriting of user transcript content from the system side
- no storage decisions that make branching or replay ambiguous

If a future feature weakens those constraints, it should be called out explicitly rather than introduced accidentally.
