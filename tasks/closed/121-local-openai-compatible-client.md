## Goal

Add a narrow LLM client layer for a local OpenAI-compatible backend.

## Scope

- Define runtime settings for base URL, API key, and model name
- Add a small client wrapper for chat-completions style requests
- Normalize responses down to assistant text suitable for operator use

## Behavior

- The default backend can target a local OpenAI-compatible endpoint such as `llama-cpp`
- Client construction is explicit and testable
- The runtime does not require the caller to know HTTP details at every generation site

## Rules

- Keep the client boundary narrow and easy to replace later
- Do not spread raw backend-specific request logic through `step` or CLI code
- Treat the first pass as OpenAI-compatible only, not a general provider matrix

## Non-Goals

- No streaming support yet
- No provider plugin system yet

## Done When

- The repo has a stable config/client seam for local OpenAI-compatible generation
- The client can turn projected chat messages into one assistant text response
- The behavior is covered with mocked tests rather than requiring a live model
