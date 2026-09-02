# TOAS Help System Design Survey

Status: DRAFT / DESIGN-ONLY
Date: 2026-09-01
Related task: `260901-help-system-design-survey`
Related direction: `260823-projection-discoverability`

## Intent

This note describes the help system as it exists today and sketches a future
user-facing model. It is deliberately not an implementation proposal. In
particular, it does not ask us to build a structured source of truth yet.

The immediate question is: what should a person or model be able to discover,
in what order, and with what distinction between an explanation, an example,
an executable command, and a capability advertisement?

## Existing surfaces

### 1. Top-level CLI help

Defined by `src/toas/cli.py` and reached through `toas help`, `toas --help`,
and `toas -h`.

It currently provides:

- a broad command list;
- the `TOAS_RPC_MODE` environment variable;
- a short explanation of history surfaces.

It covers stepping, async watch/cancel, backend lifecycle, history and
projection inspection, prompts, session continuation, surface binding,
replay scripts, and debug cancellation summaries.

Its shape is primarily a usage index. It does not currently explain command
relationships, common workflows, safety/authority boundaries, or the meaning
of the different history projections.

### 2. In-session slash-command help

Defined primarily in `src/toas/step.py`, dispatched by
`src/toas/runtime/operator_command_config_help.py`.

The compact `/help` view is a quick-start card pointing to six exact topics:

```text
/help full
/help commands
/help tools
/help cli
/help approvals
/help config
```

The full view combines:

- slash-command usage and one-line descriptions;
- the model-callable tool inventory;
- common configuration goals and examples;
- all valid configuration keys.

The topic views add two important semantics:

- `/help commands` marks examples inert so copying the whole result does not
  accidentally execute them;
- `/help approvals` explains replay queues and authorization boundaries.

This is the most operator-oriented surface, but it is also the most crowded.
It mixes discovery, reference material, recipes, policy explanation, and
configuration inventory in one family.

### 3. Tool reference and capability help

There are two related model-facing forms:

- `src/toas/tools_guidance.py` renders a full tool reference for prompt/help
  use;
- `src/toas/tools_cluster/capability_help_ops.py` implements the callable
  `capability_help` operation.

`capability_help` supports topic-oriented lookup (`core`, `editing`, `shell`,
`debug`, `all`) and individual tool names, with fuzzy aliases for likely
misspellings or broad terms. It gives argument shape, selected policy details,
and examples.

This surface is valuable because it supports progressive disclosure during a
run. It is not the same thing as operator help: it explains how a model may
call an explicitly available capability, not everything a human can do with
TOAS.

### 4. Capability advertisements and prompt-library material

`src/toas/capability_prompts.py` and the dynamic capability prompt assets
advertise a runtime-selected subset of tools and protocol constraints.

The current prompt material distinguishes:

- start-here guidance for choosing a first action;
- overview guidance for the current profile and callable shape;
- repo-work guidance for inspect/edit/test workflows;
- explicit capability-help escalation when argument shape is uncertain.

Unlike `/help`, these are contextual prompt inputs. They should be understood
as “what is available and how to behave in this run,” not as a complete product
manual.

### 5. Configuration help

Configuration help appears in several places:

- `/help config` gives command forms, durability, precedence, compatibility
  notes, prompt constraints, and selected examples;
- `/config show` reports effective values and precedence;
- `/config values <key>` reports categorical choices for one key;
- `docs/capabilities.md` documents the broader configuration and runtime model.

This is the strongest existing example of layered help: conceptual guidance,
current state, and a focused query are separate interactions. It is also a
source of duplication, especially around examples and precedence language.

### 6. Product and acceptance documentation

Relevant documentation already includes:

- `docs/capabilities.md` — current operator capability model;
- `docs/acceptance/operator-starter-triad.md` — `/help config` as a seed
  scenario;
- `docs/acceptance/spikes/help-config-*.md` — observed weak-model and operator
  friction around help/config/prompt discovery;
- `tasks/open/260823-projection-discoverability.md` — open design direction for
  prompt and projection discoverability;
- `docs/roadmap.md` — strategic framing for operator-surface clarity.

These documents contain design evidence that is not represented in the live
help output, particularly the distinction between conceptual projections,
executable context, and map-like/history views.

## Confirmed gaps and drift

### A. CLI inventory parity

`/help cli` is a hand-maintained subset of the actual CLI dispatcher. It does
not mention several dispatchable commands, including `watch`, `cancel`,
`backend`, `intents`, `session continue`, `surface`, `ancestry`, `diff`,
`index`, `replay-script`, and debug commands.

The top-level CLI usage is broader, but still does not provide a per-command
explanation or workflow grouping beyond the small history section.

### B. Tool inventory parity

Tool names are mostly registry-derived in `/help full` and `tools_guidance`,
but topic groupings and descriptions are independently authored. For example,
the capability-prompt core profile includes `capture_task_thread`, while the
`capability_help` core topic does not.

The result is not only maintenance duplication; it changes what a consumer is
told is “core.”

### C. Description and example duplication

Tool summaries, callable examples, shell policy text, newline policy text, and
configuration examples occur in multiple modules and docs. Some are concise
and some are operationally detailed. There is no documented rule for which
surface should be authoritative when they differ.

### D. Human help versus model capability

The current output makes these concepts adjacent enough to be conflated:

- a CLI command the operator can invoke;
- a slash command that changes or inspects transcript state;
- a model-callable tool exposed in the current profile;
- a prompt asset that teaches a protocol or workflow;
- a documentation-only concept or design direction.

The system already has the right semantic distinctions internally, but the
help model does not consistently name them.

### E. Progressive disclosure is uneven

`/help` has compact and topic forms, and `capability_help` has topic/tool forms,
but the CLI and docs do not have equivalent “start here → focused reference →
exact usage” paths. `/prompt` provides a parallel discovery path for prompt
assets, without a documented relationship to `/help`.

### F. Dynamic versus static truth is unclear

Some information is runtime-dependent: visible tools, shell allowlist,
configured backends/models, effective config, selected surfaces, and defaults.
Other information is stable product guidance. The current surfaces expose both
without consistently labeling whether a line is:

- a current runtime fact;
- a general rule;
- an example;
- a compatibility note;
- a design or documentation claim.

## Proposed conceptual model

The future help system should be thought of as a small set of named lenses,
not one giant manual:

```text
start here
  ├─ operate the current session
  │    ├─ slash commands
  │    ├─ approvals / replay
  │    └─ configuration
  ├─ inspect durable state
  │    ├─ heads / history / graph
  │    ├─ transcript / llm-input
  │    └─ ancestry / diff / intents
  ├─ run or connect TOAS
  │    ├─ step / async / watch / cancel
  │    ├─ backend / daemon / host
  │    └─ surfaces / continuation
  ├─ understand callable capabilities
  │    ├─ available now
  │    ├─ tool shape and limits
  │    └─ examples
  └─ explore prompt and projection assets
       ├─ prompt library
       ├─ conceptual projections
       └─ executable-context projections
```

This is a design grouping, not a proposed command syntax. It gives each item a
primary question and makes room for the same item to have multiple views
without pretending those views are identical.

Each help item should eventually distinguish four layers:

1. What is it?
2. When would I use it?
3. What is the exact invocation or callable shape?
4. What limits, authority, durability, or projection semantics matter?

Short help should answer layer 1 and point onward. Focused help should answer
layers 2–4 without reproducing every neighboring topic.

## Design questions to resolve later

- Should `toas help` and `/help` share headings and vocabulary while remaining
  separate surfaces?
- Should CLI help be organized by workflow rather than dispatcher order?
- Is `/help tools` the right home for model-callable tools, or should it be
  explicitly labeled as runtime capability reference?
- Should `/prompt` appear as a help topic, and should prompt assets declare
  whether they are instructional, executable-context, or projection-oriented?
- Which data must be live: visible tool profile, shell grants, config values,
  backend/model choices, selected surface, and history anchor?
- Which examples must be inert by construction, and which should be copyable
  one line at a time?
- How should aliases and compatibility commands be presented without making
  them look like preferred paths?
- What is the smallest “start here” card that works for a new human operator,
  a weak model, and an experienced maintainer?

## Candidate gap list for follow-on tasks

1. Define shared vocabulary for CLI command, slash command, tool capability,
   prompt asset, projection, recipe, and runtime fact.
2. Produce a manually reviewed command/capability matrix across all existing
   help surfaces.
3. Decide the intended audience and primary question for each help topic.
4. Reconcile the meaning of “core” across capability prompts and
   `capability_help`.
5. Identify which duplicated descriptions are policy truth versus examples or
   convenience prose.
6. Design a live-fact versus static-guidance labeling convention.
7. Define the CLI help workflow groupings and the minimum explanation for each
   command family.
8. Define the relationship between `/help`, `/prompt`, and projection
   discovery.
9. Add acceptance scenarios for first-principles discovery, especially the
   existing `/help config` starter triad and a CLI history-inspection path.
10. Only after the above decisions, evaluate whether any structured inventory
    would reduce drift without becoming an unused abstraction.

## Current conclusion

The immediate problem is not that TOAS lacks help text. It has several useful
help mechanisms, each optimized for a different audience or moment. The
problem is that their boundaries and relationships are implicit.

The next useful artifact is therefore a reviewed design matrix and a small set
of audience/workflow scenarios. Implementation should follow those decisions,
not precede them.
