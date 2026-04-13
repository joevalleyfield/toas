# TOAS Roadmap

## Purpose

This roadmap is forward-looking planning, not a full implementation ledger.

Use it to answer:
- what is active now
- what should land next
- what open arcs exist

Current capability shape belongs in `docs/capabilities.md`.

## Now

Open arc clusters in progress:
- shell execution unification and queueing: `328` umbrella with `330`-`333` (`329` landed)
- runtime and QoL hardening: `336`-`340`
- lineage-bounded projection diagnostics and fix: `354` (minimal deterministic branch repro passes; scope narrowed to oversized replay-content ingress/append interactions)
- prompt/session replay ergonomics for behavior regression: `356`
- context assembly prototype from lens artifacts: `344`
- docs surface rebalance roadmap vs capabilities: `345` umbrella (first pass `346` landed)

## Next

Near-term sequencing intent:
1. execute remaining `328` umbrella subtasks in order (`330`-`333`)
2. run targeted runtime/QoL hardening from `336`, `339`, and `340` alongside shell-arc implementation (`337` landed)
3. advance `344` prototype seam to first inference-path integration

## Open Arcs

### A. Real-Environment Backend Adaptation And Prompt-Lane Alignment

Why this arc exists:
- live backend behavior has exposed seams that do not appear in ideal OpenAI-compatible paths

Current state:
- this arc is functionally complete for current scope (`298`-`306`, `308`-`315` closed)
- follow-on work should open as new tasks when additional probing/runtime adaptation scope is identified

### B. Unified Shell Execution And Authorization

Why this arc exists:
- shell behavior still has syntax/context friction across assistant proposals and user-staged execution

Current state:
- umbrella `328` open
- `329` landed
- active subtasks: `330`-`333`

Target outcome:
- one internal shell normalization/authorization model with deterministic queue behavior for mixed authorization sequences

### C. Runtime / UX Hardening

Why this arc exists:
- practical runtime behavior and editor workflows still benefit from tight, test-backed iterations

Current state:
- `336`: Windows daemon detachment parity
- `337`: Vim `:ToasRestart` implemented and closed
- `339`: optional thinking stream projection
- `340`: runtime prompt-processing progress projection

### D. Context Assembly Evolution

Why this arc exists:
- hierarchical context/lensing design exists in notes but needs implementation seam

Current state:
- `344` open: Context Assembly Engine prototype from lens artifacts

### E. Documentation Surface Rebalance

Why this arc exists:
- roadmap drifted toward history density; user-facing capability shape needs first-class docs

Current state:
- `345` open umbrella
- `346` implemented and closed (first-pass reshape landed)

### F. Capability Help And Advertisement Profiles

Why this arc exists:
- capability detail currently enters the operator loop with too much relay friction during active tasks

Current state:
- `348` implemented and closed

### G. JSON Callable Lane (Parked)

Why this arc exists:
- JSON action-object callable semantics should be a separate explicit lane, not implied by prompt wording in the current YAML callable model

Current state:
- `349` open and parked at low priority pending explicit reprioritization

## Recently Closed

Recently closed tasks that still inform current planning:
- `355`: pragmatic-default template adds repo local-first few-shot entrainment (early probes had method/runtime-path confounders; corrected in task errata)
- `353`: repo-work capability advertisement includes required args and help-first guard
- `352`: capability_help shell-shape clarity and topic normalization
- `351`: remove stale JSON action entrainment and reinforce shell `argv` callable shape
- `350`: core capability advertisement includes `capability_help`
- `337`: Vim `:ToasRestart` daemon recycle command
- `348`: model-addressable capability help and advertisement profiles
- `347`: composed prompt templates as first-class assets
- `346`: roadmap compression and capability-map first pass
- `329`: unified shell authorization model and command normalization
- `315`: multi-op prompt and tool advertisement touchup
- `314`: tail-armed user structured command execution
- `313`: multiline user-shell execution and adoption semantics
- `312`: unified `/prompt` selector surface
- `311`: config capability space vs model selection state

## Compressed History (Capability Stories)

Older closed work, compressed:
- durable message-graph runtime is in place with lineage-aware stepping, branching, head/jump selection, transcript projection/rebuild, and durable non-message records
- operator command substrate is established (`command_request` / `command_result`) with adoption-oriented projection behavior
- operator config persistence is established (`toas.toml`, durable `config_override` records, transcript/runtime capability layering)
- LLM runtime seam is established with retries, richer `llm_call` durability, backend normalization, and daemon/RPC integration
- provenance/index/inspection surfaces are established (provenance markers, correction capture, seekable index, ancestry/diff inspection)
- help and discoverability surfaces are unified across CLI and session commands

## Recurring Docs-Maintenance Lane

Recurring work (proposed and in-flight):
- keep roadmap forward-looking; compress older closures into short capability-story bullets
- keep current behavior detail in capability/reference docs rather than roadmap history
- treat this as periodic maintenance work, not one-time rewrite

## Boundaries To Preserve

Future work should preserve:
- no hidden mutable state outside durable history unless explicitly justified
- no conflation of message events with control/tool/model-call/operator-command records
- no system-side rewriting of user transcript content during ordinary operation
- no storage decisions that make lineage or replay ambiguous
