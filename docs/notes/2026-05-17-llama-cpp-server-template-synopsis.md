# llama.cpp server template synopsis

- `llama-server` supports:
  - `POST /completion` for raw prompt completion (string/tokens).
  - `POST /v1/chat/completions` for OpenAI-like chat messages.

- Chat formatting is template-driven:
  - default template comes from GGUF metadata `tokenizer.chat_template`.
  - server can override with `--chat-template ...` (supported template set).

- Runtime/template introspection:
  - `GET /props` includes `chat_template` and default generation settings.

- Practical usage:
  - if chat-template metadata is missing/incorrect, `/v1/chat/completions` behavior can degrade.
  - fallback path is `/completion` with explicitly rendered prompt text.
