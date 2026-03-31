import pytest

from toas.step import step


def test_first_run_appends_all():
    transcript = """\
## USER
hello

## ASSISTANT
hi
"""

    log = []

    new_nodes, out = step(transcript, log)

    assert new_nodes == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]
    assert out == []


def test_idempotent_second_run():
    transcript = """\
## USER
hello

## ASSISTANT
hi
"""

    log = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]

    new_nodes, out = step(transcript, log)

    assert new_nodes == []
    assert out == []


def test_edit_causes_tail_append():
    transcript = """\
## USER
hello

## ASSISTANT
hi there
"""

    log = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]

    new_nodes, _ = step(transcript, log)

    assert new_nodes == [
        {"role": "assistant", "content": "hi there"},
    ]


def test_user_tail_triggers_generation():
    transcript = """\
## USER
hello
"""

    log = []

    def fake_generate(_):
        return {"role": "assistant", "content": "hi"}

    new_nodes, out = step(transcript, log, generate=fake_generate)

    assert new_nodes == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]

    assert out == [
        {"role": "assistant", "content": "hi"},
    ]


def test_assistant_tail_does_not_generate():
    transcript = """\
## USER
hello

## ASSISTANT
hi
"""

    log = []

    def fake_generate(_):
        raise AssertionError("should not be called")

    new_nodes, out = step(transcript, log, generate=fake_generate)

    assert out == []


def test_stdout_only_contains_generated():
    transcript = """\
## USER
hello
"""

    log = []

    def fake_generate(_):
        return {"role": "assistant", "content": "hi"}

    new_nodes, out = step(transcript, log, generate=fake_generate)

    # everything appended
    assert new_nodes == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]

    # stdout is only the frontier
    assert out == [
        {"role": "assistant", "content": "hi"},
    ]
