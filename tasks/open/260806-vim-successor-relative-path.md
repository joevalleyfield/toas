Filed as: 260806-vim-successor-relative-path
FKA:
AKA: leader-r successor path; Vim session continuation path
Legacy index:

keywords: surface, implementation, active, correctness, compatibility, vim

# Vim Successor Relative Path

## Current Objective

Open the successor transcript from `<leader>r` using the relative path returned
by the continuation operation, resolved against Vim's current working
directory.

## Acceptance

- `ToasContinue()` does not prepend the TOAS workdir to `successor_path`.
- The Vim regression covers continuation with Vim's cwd set to the TOAS
  workdir.
- The focused Vim test passes.

## Progress

- 2026-08-06: Identified and removed the absolute-path construction in
  `ToasContinue()`; the regression now runs from Vim's cwd and passes.
