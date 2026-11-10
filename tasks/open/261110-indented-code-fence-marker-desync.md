Filed as: 261110-indented-code-fence-marker-desync
FKA:
AKA: code fence indentation transcript desync; nested fence marker parsing; yaml code fence close; transcript turn marker swallowing; bottom up turn marker check
Legacy index:

keywords: active, bugfix, transcript, parsing, markdown, code fences, containment, desynchronization

Related: `261106-fence-aware-transcript-markers`

# Indented Code Fence CommonMark Conformance and Turn Marker Containment

## Intent

Prevent indented code fences (such as backtick fences nested inside YAML tool plans) from prematurely closing or opening top-level Markdown code fences in `parse_transcript`, which causes subsequent transcript turns and markers to be silently swallowed into prior turns.

## Context & Motivation

In `src/toas/transcript.py`, `_CODE_FENCE_OPEN_RE` and `_CODE_FENCE_CLOSE_RE` use `^[ \t]*`:

```python
_CODE_FENCE_OPEN_RE = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_CODE_FENCE_CLOSE_RE = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})[ \t]*$")
```

When an assistant turn outputs a YAML tool plan containing an indented code fence (e.g. multi-line string content formatted with ```` ```text ... ``` ```` indented by 4 spaces):

1. The inner indented `    ``` ` matches `_CODE_FENCE_CLOSE_RE` and prematurely terminates the outer 3-backtick YAML fence.
2. When the outer closing ```` ``` ```` arrives at column 0, the parser believes it is outside any fence and treats it as an *opening* code fence via `_CODE_FENCE_OPEN_RE`.
3. That phantom open fence never closes, causing `parse_transcript` to absorb all subsequent transcript content—including tool results, user turns, and frontier commands like `$ jj st`—into the assistant turn.
4. On subsequent `toas step` executions, the frontier is mistakenly resolved as the prior assistant turn with an unfulfilled tool plan, causing prior tool calls to be re-executed destructively rather than stepping into the new user turn.

Under CommonMark specification §4.5, a code fence can have up to 3 leading spaces (`^[ ]{0,3}`). Lines indented with 4 or more spaces or tabs are indented code/data lines, not Markdown code fences.

Additionally, investigating a secondary bottom-up scan or sanity check for unindented column-0 `## TOAS:(USER|ASSISTANT|SYSTEM)` turn markers when trailing unclosed fences occur provides defense-in-depth against fence balance drift.

## In Scope

- [ ] Enforce CommonMark indentation rules (`^[ ]{0,3}`) for both `_CODE_FENCE_OPEN_RE` and `_CODE_FENCE_CLOSE_RE` in `src/toas/transcript.py`.
- [ ] Verify that indented fences inside YAML plans or literal blocks do not alter the top-level Markdown fence state.
- [ ] Investigate secondary verification (e.g. bottom-up check from EOF or unindented column-0 turn marker safety check) to prevent unclosed trailing fences from silently swallowing genuine user/assistant turns.
- [ ] Add regression tests in `tests/test_transcript.py` replicating the exact YAML tool plan scenario with indented fences followed by `## TOAS:USER` turns and user shell shorthand (`$ ...`).
- [ ] Maintain 100.00% statement coverage across all modified transcript and step runtime modules.

## Out of Scope

- Rewriting the YAML tool plan extractor or changing how tool plans serialize nested code snippets.

## Acceptance Criteria

1. `parse_transcript` correctly parses transcripts where an assistant turn has a 3-backtick ```` ```yaml ```` fence containing 4-space-indented 3-backtick fences (`    ```text ...    ``` `).
2. The subsequent `## TOAS:USER` and `$ jj st` lines are recognized as distinct turns at their respective roles rather than absorbed into the assistant turn.
3. Existing fence-containment behavior from `261106-fence-aware-transcript-markers` (ignoring validly contained specimen markers inside code blocks) continues to pass without regression.
