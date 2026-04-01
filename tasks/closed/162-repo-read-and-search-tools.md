## Goal

Add safe repo-native read and search tools for code and text inspection.

## Scope

- Add `read_file`
- Add `search`
- Keep them restricted to repo-local inspection
- Return structured outputs suitable for later rendering

## Behavior

- The operator can inspect repo files without falling back to raw shell for every lookup
- Search results are focused on practical retrieval, not perfect presentation
- Tool outputs remain durable operator facts

## Rules

- File access should stay within the project workspace
- Search should prioritize practical retrieval over elaborate formatting
- Result payloads should be structured enough for later projection

## Non-Goals

- No general filesystem browser
- No dependency on `tree`
- No networked fetch here

## Done When

- `read_file` and `search` exist as registered tools
- They return structured, test-covered outputs
- They materially reduce dependence on shell for common repo inspection
