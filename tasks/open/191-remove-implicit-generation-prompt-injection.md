## Goal

Stop prepending a hidden default generation prompt during ordinary `step` generation.

## Scope

- remove automatic generation prompt injection from runtime generation
- update tests and docs to reflect transcript-first prompting
- preserve explicit prompt-library material without injecting it by default

## Done When

- ordinary generation uses transcript-projected content only
- no hidden default generation prompt remains in the normal runtime path
