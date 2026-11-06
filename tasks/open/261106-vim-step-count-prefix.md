Filed as: 261106-vim-step-count-prefix
FKA:
AKA: vim count step; 10\s; ToasStep count; vim step multiplier
Legacy index:

keywords: vim, plugin, mapping, count, stepping, bounded, runtime, rpc

Related: `261106-bounded-step-quiescence`

# Support Count Prefix for Vim Step Mapping (`[N]\s` -> `toas step [N]`)

## Intent

Enable Vim operators to prefix the step normal-mode mapping (`<leader>s`) with a count (e.g. `10\s` or `5\s`) to trigger bounded multi-turn stepping for up to $N$ turns until quiescence, matching CLI `toas step [N]` ergonomics directly from Vim.

## Context & Motivation

With task `261106-bounded-step-quiescence`, TOAS supports bounded multi-stepping (`toas step [N]`, `-n <N>`, and `/step [N]`).
In Vim, `<leader>s` is currently mapped to `:ToasStep<CR>`.
When an operator prefixes a normal-mode mapping with a count (e.g. `10\s`), Vim feeds the count to the command line as a range (`:10ToasStep<CR>`). Because `:ToasStep` lacks `-count` / `-range`, Vim fails with `E481: No range allowed`.

Wiring `v:count` into `ToasStep` allows natural Vim command multiplication:
- `\s` -> step 1 turn (current default)
- `5\s` -> step up to 5 turns until quiescence
- `10\S` (`ToasStepHere`) -> step up to 10 turns starting from cursor location

## Scope

- **Vim Plugin Mapping & Command Definition** (`vim/plugin/toas.vim`):
  - Update `command! -count ToasStep call ToasStep(<count>)`.
  - Update `nnoremap <silent> <leader>s :<C-U>call ToasStep(v:count)<CR>`.
  - Update `command! -count ToasStepHere call ToasStepHere(<count>)` and `<leader>S`.
- **Vim Step Transport Wiring**:
  - Accept optional `count` in `ToasStep([count])` and `ToasStepHere([count])`.
  - In nonblocking/async lane (`step_async` / `step_async_warm`), include `"max_turns": count` in payload when `count > 1`.
  - In synchronous / CLI fallback lane, pass `count` to CLI: `toas step ' . a:count`.
- **Host / RPC Handler Support**:
  - Ensure `step_async` payload validation accepts optional positive integer `max_turns`.
  - Forward `max_turns` to `step_bounded` in `async_step_runtime_worker.py`.
- **Tests**:
  - Vader test verifying `ToasStep` with count starts async step with `max_turns` in payload.
  - Python test verifying `step_async` payload schema accepts `max_turns`.

## Acceptance Criteria

1. Typing `\s` in Vim performs a standard single step (count=1).
2. Typing `10\s` in Vim does not raise `E481: No range allowed`; it dispatches a step with `max_turns=10`.
3. Typing `5\S` in Vim dispatches `ToasStepHere` with `max_turns=5`.
4. Command line `:ToasStep 5` and `:5ToasStep` execute with `max_turns=5`.
5. `./scripts/check.sh` passes with 100.00% statement coverage.
