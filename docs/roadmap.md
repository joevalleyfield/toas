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
- shell execution unification and queueing: `328` umbrella with `331`-`333` (`329`, `330` landed)
- agentic low-activation execution arc (procedures + lane splits): `358` umbrella with `360`-`362` (`359`, `364` landed; includes replay evolution from `356`)
- runtime and QoL hardening: `336`-`340`
- coverage-led refactor/testability pass: `374` (use targeted coverage increases to surface and remove deferred code smells)
  - immediate ratchet slice: `375` (raise floor to 80, then land focused module-level coverage gains)
  - first module subtasks opened: `376` (rpc tcp/transport), `377` (llm stream/reasoning), `378` (daemon async/fallback orchestration)
- lineage-bounded projection diagnostics and fix: `354` (minimal deterministic branch repro passes; scope narrowed to oversized replay-content ingress/append interactions)
- prompt/session replay ergonomics for behavior regression: `356`
- modifier-resolution checkpoint optimization (LCP/tail replay): `365` (deferred until correctness-first pass lands)
- context assembly prototype from lens artifacts: `344`
- docs surface rebalance roadmap vs capabilities: `345` umbrella (first pass `346` landed)
- immediate shell-policy follow-up cleanup/testing tasks: complete (`371`, `372` landed)

## Next

Near-term sequencing intent:
1. execute remaining `328` umbrella subtasks in order (`331`-`333`)
2. run targeted runtime/QoL hardening from `336`, `339`, and `340` alongside shell-arc implementation (`337` landed)
3. advance `344` prototype seam to first inference-path integration
4. continue remaining shell-queue arc delivery (`331`-`333`) on top of stabilized shell grant policy surfaces
5. execute `374` in small slices: add seam tests first, refactor internals second, spin out follow-on tasks for larger smells
6. complete `375` as first ratchet checkpoint before additional floor increases
7. execute `376` first (fastest low-risk gain), then `377`, then `378` for deeper runtime coordination coverage

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
- `329` and `330` landed
- active subtasks: `331`-`333`
- immediate follow-up tasks: none (policy view/copy + contract stabilization complete)

Target outcome:
- one internal shell normalization/authorization model with deterministic queue behavior for mixed authorization sequences

### C. Runtime / UX Hardening

Why this arc exists:
- practical runtime behavior and editor workflows still benefit from tight, test-backed iterations

Current state:
- `336`: Windows daemon detachment parity
- `337`: Vim `:ToasRestart` implemented and closed
- `339`: optional thinking stream projection
  - in progress: broaden streamed reasoning extraction beyond `delta.reasoning_content` to tolerate provider-specific chunk shapes, with opt-in reasoning diagnostics
  - in progress: re-enable `reasoning_format=auto` request hint when thinking callback is active to recover backend reasoning emission where supported
  - in progress: align `runtime.streaming_mode` with core runtime settings to remove lane-dependent stream/thinking behavior
  - in progress: harden shared LLM client cache access under concurrent daemon requests
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

### H. Agentic Low-Activation Execution

Why this arc exists:
- weaker/local models need reusable execution procedures and expressive but explicit action lanes to maintain bias-to-action without policy drift

Current state:
- umbrella `358` open
- active subtasks: `360`-`362`
- `359` and `364` implemented and closed
- `356` replay runner intent remains open and is incorporated into this arc

### I. Modifier Resolution Scaling

Why this arc exists:
- transcript-derived modifier state (`/shell`, `/env`, similar command state) should scale with tail replay rather than full transcript scans once correctness is stable

Current state:
- `365` open and explicitly deferred until modifier correctness pass lands

### J. Coverage-Led Testability Refactor

Why this arc exists:
- complexity has grown in runtime paths while coverage has drifted; targeted tests can both improve reliability and reveal architectural smells worth immediate cleanup

Current state:
- `374` open: prioritize low-coverage/high-churn modules, lock seam behavior with tests, refactor internals in validated slices
- `375` open: enforce 80% floor and deliver first targeted testability slice under `374`
- `376` open: TCP transport seam coverage pass (`rpc_tcp.py`, `rpc_transport.py`)
- `377` open: LLM stream/reasoning/progress normalization coverage pass (`llm.py`)
- `378` open: daemon async watch/lane fallback orchestration coverage pass (`daemon.py`)

## Recently Closed

Recently closed tasks that still inform current planning:
- `373`: transcript-safe escaping/unescaping for closed-set transcript role markers at projection/extraction boundaries (including RESULT-body rendering and streamed-delta projection paths)
- `372`: shell grant policy output contract tests for `/shell` and `/shell config` view/update surfaces
- `371`: centralized shell grant policy rendering and `/shell` usage/help copy via shared helpers
- `330`: semi-durable shell grants across transcript/config lanes with source-attributed effective policy and segmented shell-script authorization checks
- `367`: model-addressable `apply_patch` lane for structured assistant-side patch execution with strict context mismatch failure semantics
- `368`: async latency reduction via lane ladder completed for current single-session scope
- `370`: step/daemon/llm rationalization and reliability arc completed (stages 1-8)
- `369`: cleanup pass after Windows async restoration, intentionally squashed into the original fix changeset
- `366`: fix async execution on Windows with msys-vim
- `364`: shell-grant correctness in append-style transcripts
- `363`: replace_block result preview with context and line numbers
- `359`: explicit shell_script lane with policy-preserving boundaries
- `357`: project capability_help content into result blocks
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
