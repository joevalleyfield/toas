## Goal
keywords: exploration, explore, parked, research, json, callable, lane, parser, policy

Define a separate JSON-callable lane with explicit parser, extraction semantics, and policy behavior, without coupling it to the current fenced-YAML callable lane.

## Status Note

Deferred/parked. Keep this task open until explicitly reprioritized.

## Why Now

Prompt-library text previously implied JSON action objects as if they were equivalent to current callable extraction, which created operator confusion. Current lane remains fenced YAML; JSON callable support should be an explicit future arc.

## Scope

- define whether JSON callable input is fenced-only, unfenced, or both
- define extraction boundary rules and conflict handling with existing YAML extraction
- define policy/authorization behavior parity with existing callable execution
- define transcript projection/adoption UX for JSON callable content
- add tests and docs only after lane semantics are concrete

## Intended Behavior

- JSON callable support (if enabled) is explicit, deterministic, and independently testable
- no implied JSON executability in prompt assets unless the lane is implemented
- YAML callable lane remains stable until JSON lane is deliberately introduced

## Constraints

- no hidden protocol fork
- preserve direct user intent vs model-addressable capability split
- avoid ambiguous mixed-shape extraction at frontier

## Priority

- low priority / parked until explicitly pulled into active sequencing

## Done When

- parser/extractor semantics are implemented and test-covered
- authorization/execution semantics are parity-aligned with existing callable model
- prompt/docs language reflects implemented JSON lane behavior without ambiguity
