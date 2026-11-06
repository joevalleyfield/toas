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
In Vim, `<leader>s` was mapped to `:ToasStep<CR>`.
When an operator prefixes a normal-mode mapping with a count (e.g. `10\s`), Vim feeds the count to the command line as a range (`:10ToasStep<CR>`). Because `:ToasStep` lacked `-count` / `-range`, Vim failed with `E481: No range allowed`.

Wiring `v:count` into `ToasStep` allows natural Vim command multiplication:
- `\s` -> step 1 turn (current default)
- `5\s` -> step up to 5 turns until quiescence
- `10\S` (`ToasStepHere`) -> step up to 10 turns starting from cursor location

## Scope

- **Vim Plugin Mapping & Command Definition** (`vim/plugin/toas.vim`):
  - Updated `command! -count=0 -nargs=? ToasStep call ToasStep(<q-args> !=# '' ? str2nr(<q-args>) : <count>)`.
  - Updated `nnoremap <silent> <leader>s :<C-U>call ToasStep(v:count)<CR>`.
  - Updated `command! -count=0 -nargs=? ToasStepHere call ToasStepHere(<q-args> !=# '' ? str2nr(<q-args>) : <count>)`.
  - Updated `nnoremap <silent> <leader>S :<C-U>call ToasStepHere(v:count)<CR>`.
- **Vim Step Transport Wiring**:
  - Accepted optional `count` in `ToasStep([count])` and `ToasStepHere([count])`.
  - In nonblocking/async lane (`step_async` / `step_async_warm`), include `"max_turns": count` in payload when `count > 1`.
  - In synchronous RPC lane (`step`), include `"max_turns": count` in payload when `count > 1`.
  - In synchronous / CLI fallback lane, pass `count` to CLI: `toas step ' . l:count`.
- **Host / RPC Handler Support**:
  - Ensured `step_async` payload validation accepts optional positive integer `max_turns` in `src/toas/runtime/request_contract.py`.
  - Forwarded `max_turns` to `step_bounded` via `_dispatch_runtime_step` in `src/toas/runtime/async_step_runtime_worker.py`.
- **Tests**:
  - Created Vader test suite `tests/vim/step_count_prefix.vader` asserting `ToasStep`, `:ToasStep 5`, `:7ToasStep`, `10\s`, `ToasStepHere`, `:ToasStepHere 6`, `:8ToasStepHere`, and `4\S`.
  - Added unit test coverage in `tests/test_daemon_request_contract.py` for `max_turns` validation.
  - Added unit test coverage in `tests/test_daemon_async_runner.py` for `_resolve_async_step_start_options` parsing of `max_turns`.

## Acceptance Criteria

1. [x] Typing `\s` in Vim performs a standard single step (count=1).
2. [x] Typing `10\s` in Vim does not raise `E481: No range allowed`; it dispatches a step with `max_turns=10`.
3. [x] Typing `5\S` in Vim dispatches `ToasStepHere` with `max_turns=5`.
4. [x] Command line `:ToasStep 5` and `:5ToasStep` execute with `max_turns=5`.
5. [x] `./scripts/check.sh` passes with 100.00% statement coverage.

## Resolution & Verification

- `vim -Nu NONE -n -es -S ... tests/vim/step_count_prefix.vader` passes all 3 cases with 13/13 assertions.
- `./scripts/check.sh` passes 3,817 unit tests, 17 acceptance tests, 100.00% statement coverage across 161 modules, clean mypy and ruff check.
