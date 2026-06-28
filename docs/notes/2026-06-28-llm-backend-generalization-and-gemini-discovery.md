# LLM Backend Integration & Generalization: Options Analysis

This report evaluates strategies for extending TOAS's LLM capabilities to Gemini and other backends, with particular consideration for dependency footprints, configuration surface ownership, and the potential requirement for **in-process `llama-cpp` inference**.

---

## TOAS's Raison d'Être: The Alternate Tool-Calling Lane

A critical design requirement of TOAS is that **it does not force the use of native LLM provider tool-calling APIs** (e.g. OpenAI's `tools` parameter or Gemini's function declarations). 

### Why Native Tool-Calling is Bypassed
1.  **Proxy Interference**: Hosted enterprise proxies, security gateways, and cloud provider firewalls frequently inspect, strip, or block payloads that look like native tool/function calls or raw shell executions.
2.  **Transcript Durability**: TOAS operates over a durable, append-only history of chat transcripts. Tool requests (`tool_request`) and results (`tool_result`) are materialized as graph-native history entries from raw model text projections, rather than API-specific out-of-band payloads.

### Coexisting with Native Lanes
While alternate (text-based) tool-calling is the default path to route around proxies, we must **not preclude native tool-calling lanes**. In high-trust environments (or when using models highly optimized for function calling), routing tool-calls natively through the provider API can improve reliability. 

Unifying both lanes requires our client abstraction to capture both raw text generations and structured native tool-calls:
*   **Alternate Lane**: Model outputs text containing fenced blocks, parsed by TOAS into `tool_request`.
*   **Native Lane**: The driver translates provider-specific function calls into a normalized schema in `BackendResponse`, allowing TOAS to project them into `tool_request` events identically.

---

## Under the Hood: How LiteLLM Handles Providers

A common assumption is that unified libraries like LiteLLM act as wrappers around official provider SDKs (like `google-genai` or `google-generativeai`). In reality, LiteLLM's architecture is different:

1.  **Direct HTTP Client**: LiteLLM **does not** import or use Google's official SDK or Anthropic's official SDK for its core operations. Instead, it is itself a **heavy custom REST driver**: it translates payloads and sends direct HTTP requests to Google/Anthropic REST endpoints using the `httpx` HTTP library.
2.  **Required SDK Dependencies**: LiteLLM *does* import the official `openai` SDK (for its core interface and schema parsing).
3.  **Why LiteLLM is "Heavy"**: Even though LiteLLM bypasses vendor SDKs for Gemini and Anthropic, it pulls in a large tree of dependencies (`httpx`, `pydantic` v2, `tokenizers`, `importlib-metadata`, `click`, etc.) to support its auxiliary features: cost tracking, logging, token counting, and API gateway routing.

### The Trade-off
*   **LiteLLM**: A well-tested, feature-rich "custom REST driver" registry that carries a large dependency footprint.
*   **urllib.request REST Drivers (Option 1)**: The same architectural approach as LiteLLM (directly calling REST endpoints), but using Python's standard library `urllib` instead of `httpx`/`pydantic`, reducing the dependency footprint to **zero**.

---

## Latency Audit: CLI Startup Time & Import Overhead

In addition to installation size, **python module import overhead** is a critical consideration for terminal-native CLI applications:

*   **The 1-Second Tax**: Importing the `openai` SDK (along with Pydantic v2 and related packages) takes **approximately 1.0 second**, even on fast Apple Silicon SSDs.
*   **The Warm Daemon Mitigation**: Because of this import penalty, TOAS relies on a resident daemon (`toasd`) to stay "hosted/warm" in memory so interactive CLI operations (`toas step`) do not suffer the 1-second startup delay.
*   **Unlocking CLI-Local Mode**: If we design a modular driver registry where `openai` is loaded **lazily** (or replaced entirely by a lightweight `urllib` REST driver), the base CLI command boot time would drop to **sub-100ms**. This would make local-first execution (`TOAS_RPC_MODE=off`) extremely fast and highly usable without needing to run a background daemon.

---

## Fluidity: Dynamic Driver Architecture

To achieve fluidity—allowing the operator to seamlessly move between zero-dependency REST implementations, optional provider SDKs, LiteLLM wrappers, or in-process engines—we propose a **Modular Driver Registry**.

```
                           ┌──────────────────┐
                           │   call_backend   │
                           └────────┬─────────┘
                                    │ (lookup registry)
             ┌──────────────────────┼─────────────────────┐
             ▼                      ▼                     ▼
     ┌──────────────┐       ┌──────────────┐      ┌──────────────┐
     │  UrllibREST  │       │  LiteLLMDrv  │      │  LlamaCppDrv │
     │ (Zero-Config)│       │ (Opt-Dep)    │      │ (Opt-Dep)    │
     └──────────────┘       └──────────────┘      └──────────────┘
```

### The Driver Protocol Interface
We define a clean protocol/interface in [llm.py](file:///Users/tim/Documents/Projects/toas/src/toas/llm.py) that generalizes inputs (messages, temperature, native tools) and outputs (`BackendResponse` containing content, reasoning, and optional native `tool_calls`).

```python
class LLMDriver(Protocol):
    def call(
        self, 
        messages: list[dict], 
        *, 
        tools: list[dict] | None = None, 
        **kwargs
    ) -> BackendResponse: ...
    
    def call_stream(
        self, 
        messages: list[dict], 
        *, 
        tools: list[dict] | None = None, 
        **kwargs
    ) -> Iterator[BackendResponseChunk]: ...
```

---

## Recommended Staging Blueprint & Implementation Plan

Rather than a broad "all-at-once" custom implementation, we recommend a targeted, staged cadence to validate driver boundaries and realize immediate latency/architecture wins:

### Stage 1: Lazy-Load OpenAI First
Before writing a generic registry or new drivers, modify [llm.py](file:///Users/tim/Documents/Projects/toas/src/toas/llm.py) to lazy-load the `openai` dependency.
*   **Goal**: Drop CLI-local command startup delay under 100ms when the LLM client is not invoked.
*   **Validation**: Verify that running standard commands (like `toas history` or local queries that do not invoke active completions) avoids the 1-second import tax.

### Stage 2: Introduce the `LLMDriver` Protocol
Establish the internal `LLMDriver` protocol in [llm.py](file:///Users/tim/Documents/Projects/toas/src/toas/llm.py).
*   **Goal**: Unify chat completion inputs and outputs. Avoid a "lowest common denominator" API—ensure the protocol models TOAS-native concepts (including stream lanes, reasoning text, usage dicts, raw diagnostics, and future native `tool_calls`).
*   **Refactor**: Refactor the current OpenAI integration as `OpenAIDriver` implementing this protocol.

### Stage 3: Implement Native Gemini REST Driver (urllib)
Integrate the native Gemini REST driver behind the protocol seam, using Python's standard `urllib`.
*   **Goal**: Allow calling Gemini Pro/Flash natively without relying on OpenAI compatibility layers (which distort provider-native semantics) and without introducing new dependency packages.
*   **Verification**: Run the self-contained mock server spikes in the test suite to certify JSON mapping and SSE stream parsing.

### Stage 4: Treat In-Process Llama as another Driver Shape
Introduce a local in-process `LlamaCppDriver`.
*   **Goal**: Support local `.gguf` file execution natively within the Python process.
*   **Design**: Treat this as a "model invocation" driver, completely decoupled from HTTP assumptions. Keep its compiler/C-bindings (`llama-cpp-python`) as an optional lazy import that only executes on config selection.

### Stage 5: Keep LiteLLM / SDKs as Optional Escape Hatches
Support LiteLLM or official SDKs as optional third-party drivers.
*   **Goal**: Allow quick integration of niche providers if broad provider coverage becomes a prioritized escape hatch.
