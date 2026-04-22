from __future__ import annotations

from toas.runtime.step_runtime import run_step


def test_run_step_generates_on_user_frontier():
    transcript = """\
## TOAS:USER
hello
"""

    generated = {"role": "assistant", "content": "hi"}

    new_nodes, out = run_step(
        transcript,
        [],
        generate=lambda _working: generated,
    )

    assert new_nodes[0]["role"] == "user"
    assert out == [generated]


def test_run_step_flips_on_assistant_frontier_without_callable_intent():
    transcript = """\
## TOAS:USER
hello

## TOAS:ASSISTANT
plain assistant text
"""

    new_nodes, out = run_step(transcript, [])

    assert out == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]
    assert new_nodes[-1] == out[0]
