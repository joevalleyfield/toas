Filed as: 260621-eval-command-output-formatting
FKA:
AKA: command output; token bloat; compact output protocol
Legacy index:

keywords: tooling, investigation, active, usability, projection, output

Related: `260621-compact-search-output`

# Audit and Standardize Command Output Formats

Audit existing tool/command outputs for verbosity and token bloat. Establish a unified "compact output" pattern similar to the proposed `search` format.

## Scope
- **Identify Targets:** `shell`, `code_survey`, `read_file`, `get_structure`, `replace_block`.
- **Problem Statement:** Current tools emit verbose YAML headers, block IDs, and metadata for every chunk of output.
- **Proposed Solution:**
    - Adopt the "File-Grouped, Minimal Metadata" pattern (proven in `search`).
    - Consider a unified block ID system for multi-tool transactions.
    - Define a "compact mode" flag or default behavior for high-frequency tools.

## Tasks
1. **Audit `shell` output:** Analyze verbosity. Propose grouping by file/command if multi-line.
2. **Audit `code_survey` output:** This tool likely lists many files. Grouping/Summarizing is likely needed.
3. **Audit `read_file` output:** Ensure ranges are compact.
4. **Define "Compact Output Protocol":** Write a short RFC/section in AGENTS.md or `docs/runtime-ownership.md` describing the new standard.

## Acceptance Criteria
- [x] List of "High Friction" tools identified.
- [x] Proposed format examples for top 3 candidates.
- [x] Decision made on whether to implement immediately or defer to `search` refactor sprint.

## Progress Notes

- 2026-07-16: Claimed for an evidence-backed audit only. This pass will not
  change unrelated output semantics; it will identify the next bounded
  implementation seam, if one is justified.

## Audit Findings

The original concern about repeated YAML headers is stale: current projections
use inert fenced `toas-output` blocks. The practical compactness question is
therefore whether a tool repeats structurally equivalent records inside its
content, not whether every tool should share one generic renderer.

| Tool | Friction | Proposed compact shape | Decision |
| --- | --- | --- | --- |
| `get_structure` | high at directory scale because every symbol repeats its path | group symbols by relative path | defer a focused renderer slice until an observed consumer need |
| `code_survey` | medium at high `top_n` because ranked categories repeat paths | retain bounded files/functions/classes sections | no change now; `top_n` is already the primary bound |
| `shell` | medium only for large arbitrary streams | separate stdout/stderr blocks | no change; stream distinction is semantic, not noise |
| `read_file` | low | one importable file/range block | no change; metadata supports replay-safe import |
| `replace_block` | low | range summary plus bounded preview | no change; it is already action-oriented |

## Compact Output Protocol

- one outcome line plus the fewest inert content blocks needed to preserve
  distinct semantics
- group repeated paths or records inside a block
- attach stable block IDs only to importable/replay-safe content
- preserve separate output lanes when their distinction is meaningful

The protocol is now recorded in `AGENTS.md`. There is no evidence for a
generic compact-mode flag or a unified transaction-level block ID. The next
implementation work, if real operator evidence warrants it, should be a
focused `get_structure` renderer slice rather than an all-tool refactor.
