Filed as: 261110-indented-code-fence-marker-desync
FKA:
AKA: code fence indentation transcript desync; nested fence marker parsing; yaml code fence close; transcript turn marker swallowing; bottom up turn marker check
Legacy index:

keywords: historical, bugfix, transcript, parsing, markdown, code fences, containment, desynchronization

Related: `261106-fence-aware-transcript-markers`

# Indented Code Fence CommonMark Conformance and Turn Marker Containment

Status: CLOSED (implemented)

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

- [x] Enforce CommonMark indentation rules (`^[ ]{0,3}`) for both `_CODE_FENCE_OPEN_RE` and `_CODE_FENCE_CLOSE_RE` in `src/toas/transcript.py`.
- [x] Verify that indented fences inside YAML plans or literal blocks do not alter the top-level Markdown fence state.
- [x] Investigate secondary verification (e.g. bottom-up check from EOF or unindented column-0 turn marker safety check) to prevent unclosed trailing fences from silently swallowing genuine user/assistant turns.
- [x] Add regression tests in `tests/test_transcript.py` replicating the exact YAML tool plan scenario with indented fences followed by `## TOAS:USER` turns and user shell shorthand (`$ ...`).
- [x] Maintain 100.00% statement coverage across all modified transcript and step runtime modules.

## Out of Scope

- Rewriting the YAML tool plan extractor or changing how tool plans serialize nested code snippets.

## Acceptance Criteria

1. `parse_transcript` correctly parses transcripts where an assistant turn has a 3-backtick ```` ```yaml ```` fence containing 4-space-indented 3-backtick fences (`    ```text ...    ``` `).
2. The subsequent `## TOAS:USER` and `$ jj st` lines are recognized as distinct turns at their respective roles rather than absorbed into the assistant turn.
3. Existing fence-containment behavior from `261106-fence-aware-transcript-markers` (ignoring validly contained specimen markers inside code blocks) continues to pass without regression.

## Implementation and verification

Opening and closing fence lines now accept zero through three literal spaces
before the delimiter. Tabs and indentation of four or more columns leave fence
state unchanged. A closing fence still accepts trailing spaces and tabs.

A genuinely unclosed fence continues through EOF under
[CommonMark §4.5](https://spec.commonmark.org/0.31.2/#fenced-code-blocks).
A backward scan cannot distinguish a literal column-zero marker in such a fence
from an intended turn boundary. Reinterpreting it could promote example
commands to user intent. A regression test keeps a marker and shell shorthand
literal in this case.

All 48 focused transcript tests passed at 100.00% statement coverage. An actual
`toas step` with nested fences in a prior YAML plan executed the frontier
`printf` and did not execute the previous file-write plan. The rebuilt
transcript preserved the plan, prior result, and final user turn.
