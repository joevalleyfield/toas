Filed as: 260831-language-write-materialization-fences
FKA:
AKA: language write fences; materializing fences; source artifact write blocks; python write
Legacy index:

keywords: runtime, projection, decomp, inception, correctness, usability, transcript, tooling, language, provenance

Parent: `260803-language-exec-fenced-block-lane`
Related: `260831-transcript-source-reference-operations`; `260829-generic-interpreter-runtime-lane`; `260829-canonical-action-ingress-contract`

# Language-Native Write Materialization Fences

## Intent

Define a non-executing materialization lane for language-native fenced source.
The authored artifact should remain a language block with a declared write
destination, rather than forcing the model or operator to express file content
as a YAML `write_file` tool call.

Illustrative syntax only:

````markdown
```python write path=src/example.py
print("hello")
```
````

The source is Python. `write` declares a transformation to a file artifact; it
does not make the body executable Python or a direct tool call.

## Confirmed design truth

- `<language> write path=...` is a language/source block, not a tool-block
  alias and not an `exec` fence.
- Its body is preserved as authored source. A later materialization derives
  a `write_file` request, but that request is a declared projection, never the
  replacement authority for the fence source.
- Write materialization can be open over language labels: unlike `exec`, it
  need not know how to resolve or authorize a language runtime in order to
  preserve body text and write it to a declared path.
- Materialization is not execution. It participates through an explicit
  staging/reference transition rather than turning a present fence into an
  immediate filesystem mutation by default.
- Composable verbs: `write` and `exec` can combine on a single fence:
  - `<lang> write path=...`: pure materialization (derives `write_file`).
  - `<lang> exec`: pure execution (runs in temp/memory without persistent workspace mutation).
  - `<lang> write path=... exec` (or `<lang> exec write path=...`): composite action that materializes the source to `path` AND executes it in sequence.
- Source referencing:
  - `ref=<path-or-block-id>` allows `exec` or `write` to reference previously authored or stored source without duplicating code in the fence body.
  - `<lang> exec ref=<path-or-block-id>` executes the referenced source.
  - `<lang> write path=<dest> ref=<block-id>` materializes a durable/scratch block to a persistent workspace path.
- Projection selection retains source and derivation provenance at all times.

## Relationship to executable fences

The existing executable-fence pattern generalizes into composable verbs:

```text
python exec                           -> python_script (temporary execution)
bc exec runtime=bc                    -> interpreter_script
python write path=src/foo.py          -> write_file materialization projection
python write path=scripts/run.py exec -> write_file then python_script execution
python exec ref=scripts/run.py        -> python_script execution of referenced path
```

`exec` is open-ish only through an explicitly declared/runtime-resolved lane.
`write` is broader because it requires no language runtime, but it still
needs explicit destination, workspace/write policy, and provenance semantics.

## Non-goals

- Turning arbitrary language labels into host executable names.
- Auto-writing every `write` fence merely because it appears in an assistant
  turn.
- Defining a general artifact build system, template language, or recursive
  fence semantics.
- Choosing the final fence-info grammar or claiming a `write` keyword before
  transcript examples validate it.

## Elaboration questions

- Does `write` become an ordinary in-order materialization candidate, or only
  become available through source-reference staging?
- Which destination attributes are minimally required beyond `path`?
- When explicitly materialized, should the default working projection be an
  editable `write_file` call, a reference-preserving write frontier, or a
  selected configurable shape?
- How should multiline source, newline policy, overwrite behavior, and write
  authority be surfaced without leaking tool-call ceremony into the authored
  language block?

## Exit evidence

This task should split into implementation only after examples establish a
stable materialization transition and projection shape. A resulting slice must
show source fidelity, explicit non-execution before materialization,
workspace/write-policy enforcement, and durable derivation provenance.

## Resolution

- Implemented language-native write materialization fences in `src/toas/runtime/fence_activation.py`:
  - Recognizes `write`, `exec`, and combined `write exec` (or `exec write`) verbs in fence info tokens.
  - Recognizes `path=...` and `ref=...` attributes, along with write options (`overwrite`, `force`, `append`, `mode`).
  - Pure `write` is open across all language labels without requiring an executable runtime.
- Implemented write fence parsing and composite execution plan extraction in `src/toas/runtime/executable_fence_lanes.py`:
  - `parse_write_fence` generates `write_file` tool call plan with path, content, and write flags.
  - Supports composite `write exec`: sequences `write_file` followed immediately by the appropriate language execution tool (`python_script`, `shell_script`, `powershell_script`, or `interpreter_script`).
  - Supports source referencing via `ref=<path-or-block-id>` for empty-bodied fences, resolving workspace files and `.toas/scratch/<id>.txt` artifacts.
- Integrated write fence candidate plan extraction into `src/toas/runtime/intent_arbitration_edges.py`.
- Verified 100.00% statement coverage across all 160 test suites and full pass of `./scripts/check.sh`.
