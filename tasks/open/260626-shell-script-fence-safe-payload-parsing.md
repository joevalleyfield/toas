Filed as: 260626-shell-script-fence-safe-payload-parsing
FKA:
AKA: shell_script triple-backtick heredoc bug; markdown fence safe shell payloads; shell_script fenced yaml here-doc truncation
Legacy index:

keywords: tooling, investigation, inception, correctness, shell, projection, boundaries

Parent: `260614-architecture-follow-through-coordination`
Related: `260626-multiline-user-shell-command-spans`; `510`; `660`

# Shell Script Fence-Safe Payload Parsing

## Current Reality

`write_file` can carry literal triple-backtick Markdown content without issue,
but `shell_script` appears to fail when its `script` payload contains a here-doc
body with an inner fenced block such as ````yaml ... ````. The likely failure
is not shell parsing itself, but an earlier framing or projection layer that
mistakes payload-local fences for outer tool-call structure.

## Desired Reality

Once a `shell_script` payload is entered, the script body should remain opaque
to generic Markdown fence recognition. A literal payload line of `````,
````yaml`, or similar must not truncate, reshape, or otherwise perturb the
outer tool call unless it exactly matches the actual tool framing contract.

## Gap Analysis

The nearby multiline user-shell span work hardened user `$ ...` extraction and
heredoc continuation, but assistant-callable `shell_script` likely still has a
distinct seam where script text is treated partly as transcript syntax instead
of pure data. We need to confirm whether the bug lives in frontier candidate
extraction, YAML fence parsing, tool-call projection, transcript rendering, or
roundtrip recovery.

## Known Facts

- `write_file` accepts literal triple-backtick content because file content is a
  structured field.
- `shell_script` accepts a single `script` string argument but appears to
  travel through a more syntax-sensitive extraction path.
- Existing code already contains multiple regex- and fence-based seams for YAML
  block extraction, inert stripping, and frontier candidate resolution.
- The just-closed `260626-multiline-user-shell-command-spans` task suggests a
  recent adjacent change may help localize the ownership boundary.

## Assumptions

- The primary defect is in parsing or projection before shell execution.
- A minimal repro should be possible without invoking external tools or broad
  end-to-end setup.

## Unknowns

- Which exact layer truncates or reshapes the payload first.
- Whether the failure is assistant-only, transport-specific, or transcript
  roundtrip-specific.
- Whether the fix should preserve existing triple-backtick action-lane syntax or
  migrate `shell_script` transport toward a more structured literal-content
  path.

## Investigations

- Reproduce with a minimal assistant `shell_script` plan whose here-doc body
  contains a fenced YAML block.
- Compare behavior across direct tool execution, frontier extraction, and
  transcript/render roundtrip seams.
- Audit regex/fence consumers in `graph.py`, `runtime/intent_arbitration_edges.py`,
  `runtime/operator_command_prompt_workspace.py`, and related frontier helpers
  for non-opaque handling of `script` payload content.

## Models

- `write_file`: content is data.
- `shell_script`: payload may currently be treated as both data and framing
  syntax.

## Forecasts

The likely smallest safe fix is either to tighten the outer action-block parser
so it closes only on the real enclosing fence, or to move `shell_script`
payload handling onto a more explicitly structured literal-string path. The
right seam should become obvious after a focused repro test lands.

## Risks

- A naive fence regex tweak could regress existing action-block extraction.
- Fixing one parser seam without covering transcript/render roundtrip could
  leave transport-specific failures behind.

## Transformations

- Add a targeted failing test that proves a literal fenced here-doc survives
  assistant `shell_script` extraction intact.
- Then repair the narrowest ownership boundary that incorrectly interprets
  payload-local fences.

## Evidence

- User report: `write_file` works with triple backticks; `shell_script` does
  not.
- Nearby historical task: `260626-multiline-user-shell-command-spans`.

## Decisions

- Treat this first as an investigation/inception task, not yet an
  implementation commitment.
- Bias toward a parser/framing fix over instruction-only workarounds such as
  “use `~~~` instead.”

## Open Fronts

- Determine whether existing YAML fence regexes are fundamentally too weak for
  nested-fence payloads.
- Decide whether action-lane syntax needs an explicit stronger framing contract.

## Next Actions

- Write the smallest repro test that differentiates `write_file` from
  `shell_script`.
- Identify the first layer where the script payload loses byte fidelity.
- Split an implementation child task if the fix surface is larger than a narrow
  parser hardening slice.
