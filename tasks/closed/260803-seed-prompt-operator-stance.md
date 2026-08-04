Filed as: 260803-seed-prompt-operator-stance
FKA:
AKA: seed prompt refresh; conversation synthesis execution stance; tool-lane entrainment
Legacy index:

keywords: projection, implementation, historical, contract, prompts, entrainment, tooling, defaults

Related: `182`; `355`; `260727-one-turn-projection-tail-frame`; `260803-first-failure-plan-recovery`; `260803-assistant-execution-authority`; `260803-seed-prompt-composition-study`; `260803-tool-intent-ingress-separation`

# Seed Prompt Operator Stance

## Objective

Refresh the default seed/bootstrap prompt so it teaches TOAS as a deliberate
conversation -> synthesis -> execution operator rather than a chat wrapper
that occasionally emits one tool call.

The refreshed stance should make multi-tool planning feel ordinary, keep the
TOAS callable lane as the preferred local execution surface, and still permit
plain conversational or synthesis turns when execution is not yet warranted.

This is a requirements parent. The first investigation child is
`260803-seed-prompt-composition-study`, which preserves and decomposes an
operator-proven assembled prompt before any default-template rewrite.

## Current Reality

The active entrainment material successfully teaches fenced-YAML TOAS calls
and local-workspace-first behavior, but its examples are almost entirely
single-call protocol demonstrations. Repo-work guidance says to discover,
edit, and test, yet the seed does not clearly explain the higher-level rhythm
between discussing intent, synthesizing a plan or artifact, and executing a
bounded sequence through TOAS.

This leaves weaker models vulnerable to two opposite mistakes:

- staying conversational after enough context exists to act;
- treating every turn as an isolated tool request instead of planning a
  coherent sequence of useful operations.

## Desired Contract

- Conversation is a legitimate mode for resolving intent and uncertainty.
- Synthesis turns consolidate what is known into a decision, plan, or artifact
  without pretending that work has already executed.
- Execution turns use the local TOAS tool lane for workspace-local discovery,
  manipulation, and verification.
- A response may propose multiple ordered tool operations when their
  dependency and failure behavior are clear; multi-tool use should not require
  special pleading in each user prompt.
- The prompt favors direct local action over asking the user to provide files,
  run routine commands, or mediate access already available through TOAS.
- Tool-ingress choice is explicit: reliable native provider calling may be the
  preferred happy path, while blocked-channel profiles use TOAS text lanes.
  Both preserve shared TOAS step/runtime semantics.
- Planning guidance must remain compatible with first-failure recovery rather
  than assuming that every operation in a batch succeeds.

## Investigation And Design Questions

- Which material belongs in the seed/template versus the protocol entrainment
  fragment or capability guidance rendered from the live registry?
- How much multi-tool demonstration is needed before the seed becomes too
  large or encourages speculative batches?
- Should examples show one dependent sequence, one independently parallelizable
  set, or both?
- How should the seed distinguish a useful synthesis turn from an unnecessary
  refusal to execute?
- Does `single_user_blob` need a different rendering of this stance, or can the
  same logical prompt material serve native chat and transcript renderers?
- Which parts of the operator-proven assembled prompt are independently useful,
  which work only through interaction effects, and which should remain
  selectable rather than default?
- Should prompt manifests gain named/typed layer slots, or is the current
  ordered `refs` plus `constraints` model sufficient once the fragments are
  decomposed cleanly?
- How should TOAS evaluate prompt behavior without overfitting to tool-call
  syntax compliance at the expense of useful conversation and synthesis?

## Acceptance Criteria

- [x] The default seed explicitly teaches the conversation -> synthesis ->
  execution stance without forcing every response into execution.
- [x] At least one compact example demonstrates a coherent multi-tool plan and
  explains why the operations belong together.
- [x] Examples prefer TOAS tools for local discovery, editing, and verification
  and do not suggest unavailable provider-native calls.
- [x] The prompt does not duplicate the full live tool registry or freeze
  policy limits that belong in capability guidance.
- [x] Prompt composition tests prove that the default startup path includes the
  refreshed stance and that alternate prompt-library assets remain selectable.
- [x] Focused dogfood evidence compares representative conversation-only,
  synthesis, single-tool, and multi-tool requests on the intended local model.
- [x] The prompt/task notes record any operator-supplied examples or artifacts
  used to choose the final wording.
- [x] The assembled reference prompt is mapped to current repo assets and gaps,
  decomposed into recomposable layers, and expressed as a concrete target
  manifest before the default changes.

## Non-Goals

- Replacing runtime tool authority with prompt prose.
- Making the seed responsible for execution scheduling or failure recovery.
- Requiring multi-tool output when a single operation or conversational answer
  is sufficient.
- Broad model benchmarking before representative TOAS dogfood cases exist.

## Allowed Write Surfaces

- prompt assets under `src/toas/prompts/`
- prompt composition in `src/toas/prompts.py` only where required
- prompt profile defaults in `src/toas/config.py` and bootstrap/prompt API
  threading where required for explicit ingress and output-profile selection
- config parsing and runtime/operator prompt-loading seams required to carry
  those profile selections without hidden composition policy
- dynamic capability rendering in `src/toas/capability_prompts.py` and
  registry argument metadata in `src/toas/tools.py` where required for an
  accurate composed tool-definition block
- focused prompt and request-shape tests under `tests/`
- this task file and mechanically generated `tasks/WORKBOARD.md` sections

## Required Completion Evidence

- before/after rendered default seed;
- focused prompt-composition test results;
- dogfood transcripts covering the four response modes above;
- default suite result.

## Operator Input Welcome

Useful additions include successful or failed seed variants, transcripts where
the model stayed conversational too long, examples of good multi-tool planning,
and wording that best captures the conversation/synthesis/execution stance.

## Artifact Intake: 2026-08-03

The operator supplied a Gemini-refined, assembled prompt that has already shown
good qualitative behavior: it keeps TOAS-local tool use correct while moving
seamlessly between action and conversation instead of forcing a tool call on
every turn.

The artifact combines role framing, tool definitions, callable schema,
Gather/Synthesize/Execute phases, bounded multi-tool batching, indent-safe edit
guidance, three phase-specific few-shots, and an intention tail. It is preserved
verbatim, traced against current repo assets, and mapped into a target manifest
in child task
`260803-seed-prompt-composition-study`.

## Child Study Result: 2026-08-03

The child completed the repo-evidence pass. The current composer can express
the stable text-lane recomposition with ordinary role/protocol leaves, and
bootstrap already threads capability profile and hidden-tool inputs. It also
confirmed one bounded implementation gap: dynamic capability renderers filter
visibility, while the registry-derived `tools-guidance-*` constraint does not.
Keep native/text/no-tool tail selection as a separate composer/profile
follow-on, and leave the six model-level behavior scenarios open before
finalizing default wording.

The operator subsequently chose to carry the work through to an exact final
composed prompt and called out the opacity of trailing constraints and implicit
one-to-many ref expansion. The child now recommends an explicit ordered-block
v2 projection, with the existing composer retained for compatibility. The
golden rendered prompt should lead the implementation: dynamic tool definitions
occupy their intended section, lane-specific groups are conditional, and every
included block has an inspectable source and rendered range.

## Completion Summary: 2026-08-03

`pragmatic-default_v2` is now the bootstrap default. It uses an explicit
ordered-block manifest, an effective registry-rendered tool-definition block,
canonical `arguments`, selectable ingress/output profiles, and a byte-for-byte
golden projection. The stable document includes the thinking-partner stance,
conversation/synthesis/execution modes, bounded multi-operation guidance,
indent-safe editing guidance, three representative examples, and the
intention-tail contract.

Focused local-model dogfood covered all six study scenarios:

- conversation-only answered without an action and included an intention tail;
- synthesis recommended append-only events without issuing an action;
- bounded Gather stayed in the TOAS YAML lane with two read-only searches;
- approved Execute emitted one exact `replace_block` and staged testing after
  success;
- strict YAML emitted one canonical `read_file` operation;
- provider-native temptation was explicitly redirected into a TOAS-local
  `read_file` operation.

Verification: 64 focused prompt tests passed with 100% targeted coverage for
`toas.prompts` and `toas.capability_prompts`; the complete suite passed with
2,729 tests and 100% repository coverage (9 deselected).
