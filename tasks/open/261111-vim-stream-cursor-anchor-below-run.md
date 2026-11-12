Filed as: 261111-vim-stream-cursor-anchor-below-run
FKA:
AKA: vim stream cursor anchor; TOAS:RUN cursor drift; streaming cursor below run region
Legacy index:

keywords: tooling, hardening, active, correctness, usability, vim, stream, transcript, frontier

## Summary

When streaming content into a `## TOAS:RUN` / `## /TOAS:RUN` region, the
cursor should maintain its relative position to the text **below** the run
region. Currently, when the cursor is at or below `## /TOAS:RUN`, each
streamed newline causes the cursor to drift upward by one line relative to
the surrounding text, because the absolute line number is preserved while
content above shifts down.

## Reproduction

1. Open a transcript in the TOAS Vim plugin.
2. Start a step that produces streaming output (e.g. a long LLM response
   with tool calls).
3. Place the cursor on or below the `## /TOAS:RUN` end marker.
4. Observe: as newlines are streamed into the run region, the cursor stays
   on the same absolute line number, but the text it was on moves down,
   so the cursor effectively moves up one line per streamed newline.

## Current Behavior

Two code paths handle streaming buffer updates:

1. **`toas_replace_buffer_region`** (line 1685): Uses
   `winsaveview`/`winrestview` to preserve the view. This is correct for
   cursors **above** the run region — the saved absolute line is still
   valid because content above is unchanged. However, when the cursor is
   **at or below** the run region, the saved absolute line now points one
   line higher in the *new* layout because new content was inserted above.

2. **`append(line('$'), ...) + normal! G`** (lines 3890, 3923, 3979,
   4155): These paths force the cursor to end-of-buffer after each chunk,
   which is a separate but related issue — it overrides any user cursor
   position entirely.

## Desired Behavior

- **Cursor above `## TOAS:RUN`**: No change. The cursor stays on the same
  text. (Already works via `winsaveview`/`winrestview`.)
- **Cursor at `## TOAS:RUN` or `## /TOAS:RUN` markers**: The cursor should
  stay on the marker line (i.e., track the marker as it moves).
- **Cursor below `## /TOAS:RUN`**: The cursor should maintain its offset
  from the `## /TOAS:RUN` end marker (or equivalently, its offset from the
  end of the buffer). When N new lines are inserted into the run region,
  the cursor should shift down by N lines.

## Affected Code

- `vim/plugin/toas.vim`:
  - `toas_replace_buffer_region` (line 1685): The `winsaveview`/`winrestview`
    path needs to detect whether the saved cursor is at or below the run
    region's end marker and, if so, adjust the restored line by the delta
    in region size.
  - Streaming append paths (lines 3890, 3923, 3979, 4155): The
    `append(line('$'), ...) + normal! G` pattern needs the same anchor
    logic. These paths currently force cursor to EOB regardless of
    position.
  - `toas_find_run_region` (line 797): Available to determine the run
    region's `[start, end]` for the anchor calculation.

## Fix

Added `s:toas_shift_view_below_region()` in `vim/plugin/toas.vim`, called
from both code paths in `toas_replace_buffer_region` before `winrestview`.
When the saved cursor line is ≥ the region end, the cursor and topline
are shifted by the delta in region size.

Key finding: `winsaveview()` in ex mode / scripted contexts can return a
view dict where direct `a:view.cursor` access throws. Must use
`get(a:view, 'cursor', [])` and guard on type/length before indexing.
This was discovered through test regression bisection — the unguarded
direct access corrupted vim state silently.

## Acceptance

- [x] Cursor above `## TOAS:RUN` stays on the same text during streaming
      (regression check — already works).
- [x] Cursor on `## TOAS:RUN` or `## /TOAS:RUN` tracks the marker line.
- [x] Cursor below `## /TOAS:RUN` maintains its relative offset from the
      end marker as newlines are streamed.
- [ ] The `append(line('$')) + normal! G` paths also respect the anchor
      (do not force cursor to EOB when the user is positioned below the run
      region).
- [ ] Vader test or Python integration test covering cursor position
      before/during/after a streaming sequence with the cursor below the
      run region.

## Notes

- The `winsaveview`/`winrestview` pair in `toas_replace_buffer_region` is
  the primary seam. The fix should live there so all callers benefit.
- The `normal! G` call sites in the watch/streaming loop are a secondary
  concern; they may be appropriate for the "follow to end" use case but
  should not override a user who has intentionally positioned the cursor
  below the run region.
- Consider whether `toas_insert_run_region` (line 1947, which already uses
  `winsaveview`/`winrestview`) needs the same fix for the initial marker
  insertion.
