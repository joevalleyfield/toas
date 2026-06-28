Filed as: 260628-gemini-endpoint-discovery
FKA:
AKA: gemini integration; multi-provider abstraction; llm backend generalisation; gemini api discovery
Legacy index:

keywords: runtime, exploration, investigation, explore, inception, research, compatibility

# Gemini Endpoint Discovery and Multi-Provider Generalization

Investigate Gemini API integration paths to transition from OpenAI-bound client code to fluid, multi-provider capabilities without introducing heavyweight SDK dependencies, avoiding reliance on provider compatibility wrappers.

## Current Reality

- The LLM client implementation in [llm.py](file:///Users/tim/Documents/Projects/toas/src/toas/llm.py) is tightly bound to the `openai` python library: it imports `OpenAI`, creates a client instance using `openai.OpenAI`, and calls `client.chat.completions.create(...)` in both streaming and non-streaming modes.
- Configurations in `Settings` are geared towards OpenAI (e.g. `llm_base_url`, `llm_api_key`, `llm_model`, `llm_transport_mode`).
- There is a clear extension seam documented in [llm.py](file:///Users/tim/Documents/Projects/toas/src/toas/llm.py#L826):
  `# Extension seam for additional backend shapes: normalize to BackendResponse.`
- The user is bound to the OpenAI shape but wants to extend to Gemini. However, introducing a new library dependency (like the official `google-genai` or `google-generativeai` SDK) for every endpoint is a maintainability concern they want to avoid.

## Desired Reality

- A clear, dependency-free (or minimal-dependency) strategy for integrating the Gemini API and other providers in the future.
- Unified backend calling capability in [llm.py](file:///Users/tim/Documents/Projects/toas/src/toas/llm.py) that normalizes inputs and outputs to/from multiple backends via the `call_backend` method.
- Transparent configuration through environment variables (e.g. adding `TOAS_LLM_PROVIDER` or similar) that selects the appropriate backend driver/path.
- A codebase that remains light and maintains its current 100% test coverage targets.

## Gap Analysis

- Currently, [llm.py](file:///Users/tim/Documents/Projects/toas/src/toas/llm.py) only instantiates `OpenAI` client.
- We need to discover the feasibility, trade-offs, and alignment of primary architectural options that do NOT rely on third-party compatibility layers:
  1. **Direct REST Driver (Zero-Dependency)**: Implement direct REST payload translation in Python (using standard library `urllib.request`) for both Gemini and OpenAI. This matches the zero-external-dependency goal, keeping TOAS lightweight and fully in control of streaming/reasoning extraction.
  2. **LiteLLM / Unified Library Integration**: Evaluate if a lightweight, unified translation package like `litellm` (the Python equivalent of the Vercel AI SDK pattern used by OpenCode) is a viable fit, or if its dependency footprint is too large for the project goals.
  3. **Vercel AI SDK for Python (`ai-python`)**: Evaluate if the newly available Vercel AI SDK for Python fits the codebase's architecture and if it introduces too many dependencies.
- We lack concrete evidence on how native Gemini API request/response formats (especially streaming SSE/JSON formats) align with TOAS's streaming and reasoning needs.

## Known Facts / Assumptions / Unknowns

### Facts
- OpenCode (Anomaly's coding agent) is built primarily in TypeScript/Node.js and uses Vercel's **AI SDK** (`ai`, `@ai-sdk/openai`, `@ai-sdk/google`, etc.) to span the gamut of LLM endpoints.
- TOAS relies on standard Chat Completion schemas, streaming chunks, model names, and token usage counts.
- [llm.py](file:///Users/tim/Documents/Projects/toas/src/toas/llm.py) has a 100% test coverage gate.
- Standard HTTP/REST calls can be executed dependency-free using Python's standard `urllib.request`.

### Assumptions
- Direct REST endpoints (using `urllib.request` as seen in [llm_harness.py](file:///Users/tim/Documents/Projects/toas/src/toas/llm_harness.py)) are highly maintainable and don't require external library updates.
- Writing a simple converter/adapter for payload schemas is cleaner and more robust than adding SDK dependencies or using provider compatibility proxies.

### Unknowns
- How do Gemini's native API parameters (e.g., system instructions, generation config, safety settings) map to OpenAI equivalents?
- Does Gemini's native streaming endpoint return reasoning/thinking tokens as a separate field, and how does it signal stream completion?

## Investigations

- **Discovery Report**: [gemini_discovery_report.md](file:///Users/tim/.gemini/antigravity/brain/c5b1b753-0d51-4c39-a7c7-8f1be2113248/gemini_discovery_report.md) records the detailed analysis of LLM backend integration strategies, comparing zero-dependency REST wrappers, LiteLLM, Vercel AI SDK, and official SDKs, as well as handling in-process `llama-cpp`, the coexistence of tool-calling lanes, and CLI startup import overhead.
1. **Native Gemini REST API Exploration**: Research the native v1/v1beta Gemini API REST endpoints, payload format, and Server-Sent Events (SSE) streaming structure.
2. **REST Driver Prototype**: Build a simple prototype or scratch script calling the native Gemini API directly via `urllib.request` to test streaming and response normalization.
3. **Unified Libraries Evaluation**: Perform a package weight and dependency audit for `litellm` and `ai-python` to determine if their adoption is justified compared to a zero-dependency REST wrapper, especially given that TOAS's alternate tool-calling lane bypasses native provider tool-calling features.
4. **Modular Driver Registry & Interface Design**: Draft a lightweight client driver registry and protocol/interface in [llm.py](file:///Users/tim/Documents/Projects/toas/src/toas/llm.py) that generalizes inputs (messages, parameters, native tools) and outputs (text, reasoning, native tool_calls), allowing fluid switching between zero-config drivers (like native REST) and optional drivers (like `llama-cpp-python` or `litellm`).
5. **In-Process `llama-cpp` Driver Viability**: Spike a dynamic import wrapper for `llama-cpp-python` to ensure it acts as an optional dependency that compiles only on demand.
6. **Import Latency & Startup Audit**: Audit the import timings of standard libraries (`openai`, `pydantic`) and research lazy-import strategies for the driver registry to keep core CLI startup under 100ms.

## Models / Forecasts / Risks

- **Risk**: Maintaining multiple custom REST payloads and response parsers can lead to subtle bugs or maintenance overhead if the APIs change, though standard API versions (e.g., `/v1`) are highly stable.
- **Risk**: Adding the official SDK package introduces dependency rot and build complexity, particularly in local/isolated execution environments.
- **Risk**: Core CLI command latency is tightly bound to import overhead. Importing `openai` and its dependencies introduces a 1.0s penalty, which currently forces reliance on `toasd` to stay warm.
- **Forecast**: Developing a lightweight driver registry that lazily loads `openai` (or replaces it with a `urllib` client) would allow base `toas` to run completely local-first under 100ms without background daemon processes.

## Transformations

- Create a research spike script in `scratch/` or as a utility to probe both the compatibility layer and native REST endpoints.
- Update `docs/roadmap.md` and/or `tasks/WORKBOARD.md` to reference this discovery task.

## Evidence

- [x] Completed discovery report summarizing findings, API behavior, and recommended architecture: [gemini_discovery_report.md](file:///Users/tim/.gemini/antigravity/brain/c5b1b753-0d51-4c39-a7c7-8f1be2113248/gemini_discovery_report.md)
- [x] Working spike scripts showing successful completion, streaming, and error handling for Gemini: [spike_gemini_rest.py](file:///Users/tim/.gemini/antigravity/brain/c5b1b753-0d51-4c39-a7c7-8f1be2113248/scratch/spike_gemini_rest.py) and [spike_litellm_driver.py](file:///Users/tim/.gemini/antigravity/brain/c5b1b753-0d51-4c39-a7c7-8f1be2113248/scratch/spike_litellm_driver.py)
- [ ] A package dependency/weight comparison matrix.
- [ ] A proposed design/implementation plan for multi-provider support.

## Decisions

- **260628**: Rejected Google's OpenAI-compatible endpoint route. We want to be fluid with the endpoints we configure/choose, and avoid dependency on translation layers or fidelity-lowering compatibility adapters. Focus instead on discovering custom direct payload-mapping / REST implementations or minimal client abstractions.
- **260628**: Validated the Modular Driver Registry architecture via two code spikes. Option 1 (zero-dependency REST driver) successfully runs native REST chat completions and parses SSE streams. Option 1 wraps Option 2 (LiteLLM) dynamically as an optional driver via lazy imports, preventing compile-time/dependency pollution.
- **260628**: Implemented Stage 1 (lazy loading of the OpenAI client in `llm.py`). Added a pre-warming hook to `toas host serve` to prevent import-time latency spikes from causing event-loop timeouts in the socket stream integration tests.

## Open Fronts

- Direct REST calling implementation overhead.
- Mapping of streaming reasoning/thinking tokens from native Gemini streams.
- Local compilation and dependency management overhead for `llama-cpp-python` as an optional driver.
- Mapping of native tool-calling JSON schemas to a unified backend response structure without introducing API translation bloat.
- CLI startup/import overhead mitigation (lazy-loading of the default OpenAI backend).

## Next Actions

- [x] Stage 1: Refactor [llm.py](file:///Users/tim/Documents/Projects/toas/src/toas/llm.py) to lazy-load the `openai` dependency, verifying that non-completion CLI commands boot under 100ms.
- [ ] Stage 2: Define the `LLMDriver` protocol/interface in [llm.py](file:///Users/tim/Documents/Projects/toas/src/toas/llm.py) that models TOAS-native concepts (including stream lanes, reasoning, and native `tool_calls`). Refactor current OpenAI integration into `OpenAIDriver`.
- [ ] Stage 3: Implement `GeminiRESTDriver` implementing the `LLMDriver` protocol using direct `urllib.request` REST calls (supporting streaming SSE and response mapping).
- [ ] Stage 4: Implement local in-process `LlamaCppDriver` that dynamically imports `llama-cpp-python` only if `llama-cpp` is the configured provider.
- [ ] Stage 5: (Optional) Add optional driver wrappers for `litellm` or `ai-python` if broad provider coverage becomes a prioritized escape hatch.
