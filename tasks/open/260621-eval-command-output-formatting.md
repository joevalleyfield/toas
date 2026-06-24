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
- List of "High Friction" tools identified.
- Proposed format examples for top 3 candidates.
- Decision made on whether to implement immediately or defer to `search` refactor sprint.