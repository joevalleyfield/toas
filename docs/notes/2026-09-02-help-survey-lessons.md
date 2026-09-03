# Help Survey Lessons and Light Critique

Status: working note; retrospective guidance, not a collection schema
Date: 2026-09-02
Related task: `260901-help-system-design-survey`

This note holds observations about the survey procedure that should inform
future execution without becoming instructions to chase the latest critique.
The task and design note should contain the current gates; this note records
why those gates exist and which concerns remain provisional.

## Product-surface lessons

- A help topic and the executable command family it links to may be related
  without being one item. Audience, disclosure role, and state effect are
  useful separators.
- Executable behavior and conceptual documentation should be compared, not
  merged. Runtime evidence establishes what happens; existing help establishes
  what the product currently exposes or claims.
- A callable item can have several disclosure levels without becoming several
  identities. Profile visibility is exposure evidence, not proof of priority.
- Prompts, activation commands, generated projections, durable records, and
  recovery handoffs may form one workflow while remaining distinct items.
- The history and recovery families are better represented as directed
  workflows than as single broad items. Selection, transformation, execution,
  authorization, and continuation have different user intents and authority.
- Terms such as `projection`, `view`, `diagnostic`, `recovery`, `replay`, and
  `run` currently overlap. Preserve the overlap as divergence until product
  vocabulary is deliberately chosen.
- Runtime ownership, state effect, and non-generation safety discriminate
  better than command grouping alone.

## Procedure lessons

- The four axes—item, surface, audience, and intent—must remain separate
  structures. Multiplicity belongs in sequences or nested objects, not joined
  labels.
- Subdivision is valid during initial scoping or as a later state transition.
  The parent must retain its reason, child list, and coverage claim.
- Structural closure and semantic review are different gates. Parseability,
  source closure, candidate adjudication, and reference integrity must not be
  confused with product agreement.
- Typed evidence prevents an existing help statement from being mistaken for
  runtime behavior. Inferences need their own evidence type.
- Self-review is useful for throughput but must not be presented as
  independent validation.
- Repeating a full source ledger for every small slice preserves provenance but
  becomes expensive when sources are shared. This is a future ergonomics
  concern, not permission to omit source accounting.
- A runtime probe and an acceptance test may overlap in method while serving
  different evidentiary purposes. Keep that distinction explicit until it is
  intentionally simplified.

## Meta-turn warning

The validator-oriented batch was a legitimate calibration pass, but it arrived
before product coverage had been declared complete. The repeated additions of
operation-specific provenance and neighboring-boundary fields show how a
productive schema-discovery technique can become a meta-loop.

Future runs should classify their track before collection. A `product` run
discovers help content and behavior. A `process` run evaluates the collection
method, schema, or validator. Process runs are held until the product phase
gate is satisfied, except for a narrowly recorded blocking probe needed to
make that gate executable.

## Retired critiques

These concerns have been preserved for context but should not automatically
generate more slices:

- repeated five-source ledgers are costly;
- duplicate YAML keys need a deterministic policy;
- workflow references and coverage dimensions need typed references;
- exit-status precedence needs to distinguish open questions from conflicts;
- independent-review thresholds remain a product/process decision.

They become actionable only when a current phase gate, observed failure, or
explicit design decision requires them.
