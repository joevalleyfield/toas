Filed as: 260829-markdown-fence-scanner
FKA:
AKA: reusable fence scanner; markdown fence boundaries; fence source spans
Legacy index:

keywords: runtime, implementation, active, correctness, tooling, frontier, provenance

Parent: `260803-language-exec-fenced-block-lane`
Depends on: `260829-action-plan-envelope`
Related: `260803-tool-intent-ingress-separation`

# Reusable Markdown Fence Scanner

Add a shared, inert Markdown fence scanner that reports structural boundaries,
info-string tokens, body text, and source spans without deciding whether a
fence is executable.

## Scope

- recognize supported backtick fence boundaries and matching closing lengths;
- preserve language/info-string tokens and body text;
- report opening/closing offsets and line positions;
- fail closed for unterminated or ambiguous structures;
- respect existing inert-region behavior and keep nested content opaque;
- add focused scanner tests without changing current YAML or shell activation.

## Non-Goals

- activating executable fences;
- selecting interpreters or invoking subprocesses;
- changing YAML compatibility behavior;
- adding JSON or call-expression parsing;
- changing authority, arbitration, or projection semantics.

## Acceptance

- the scanner has one reusable structural result shape;
- existing inert stripping and YAML extraction remain green;
- fence bodies containing shorter inner backtick runs remain intact;
- malformed/unterminated fences do not produce executable candidates;
- completion evidence records the deferred activation decision.

## Outcome

Implemented `scan_markdown_fences()` with a reusable frozen `MarkdownFence`
result carrying info-string tokens, body, offsets, line numbers, and fence
length. Unterminated openings are ignored, and shorter backtick runs inside a
longer fence remain body text. The scanner makes no potency or execution
decision.

Verification:

- `./.codex-local/bin/uvt run pytest tests/test_runtime_markdown_fence.py tests/test_shell_intent.py tests/test_graph.py -q --no-cov` (`177 passed`)
- `./.codex-local/bin/uvt run ruff check src/toas/runtime/markdown_fence.py tests/test_runtime_markdown_fence.py`

Executable activation, lane registration, and routing remain deferred to the
next fence-lane follow-on.
