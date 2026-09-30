Filed as: 260929-state-sequence-inference-affordance
FKA:
AKA: multi-state inference; whole-sequence state review; state-chain inference
Legacy index:

keywords: runtime, investigation, inception, usability, state-step, transcript

Related: `260927-state-step-alpha-loop`; `260928-state-user-control-turn-lifecycle`

# Add An Affordance For Multi-State Inference

Explore and add an explicit affordance that lets state inference consider an
ordered sequence of state turns and their observations together. This should
let the model reconsider its trajectory using the accumulated context without
requiring the operator to change `STATE` markers to `ASSISTANT` markers.

## Intended Behavior

- Inference can receive multiple consecutive state turns and relevant
  observations as one ordered context.
- The model produces one forward state advancement from that context; prior
  state turns and durable history remain immutable.
- The affordance is explicit and leaves ordinary single-state stepping
  available.

## Open Questions

- How the operator selects or invokes the wider inference context.
- Which state and observation span should be included, and how it is represented
  in the inference packet.
- How broader-context inference interacts with pending tool batches and replay.
