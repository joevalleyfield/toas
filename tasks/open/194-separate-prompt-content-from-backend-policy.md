## Goal

Keep backend flags and backend-adaptive policy separate from prompt content.

## Scope

- clarify what belongs in backend policy versus prompt assets
- ensure awkward-backend adaptations do not quietly become hidden prompt logic
- document the separation clearly

## Done When

- backend policy and prompt content are conceptually and operationally distinct
- future extraction/repair work can build on that separation
