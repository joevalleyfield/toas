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


def test_user_tail_with_callable_executes_result_without_generation():
    transcript = """\
## USER
please run this
```yaml
- tool_name: echo
  args:
    text: hi
```
"""

    log = []
    calls = {}

    def fake_generate(_):
        raise AssertionError("should not be called")

    def fake_execute(working, plan):
        calls["working"] = working
        calls["plan"] = plan
        return {"role": "result", "content": "ran echo"}

    new_nodes, out = step(transcript, log, generate=fake_generate, execute=fake_execute)

    assert new_nodes == [
        {
            "role": "user",
            "content": "please run this\n```yaml\n- tool_name: echo\n  args:\n    text: hi\n```",
        },
        {"role": "result", "content": "ran echo"},
    ]
    assert out == [
        {"role": "result", "content": "ran echo"},
    ]
    assert calls["plan"] == [{"tool_name": "echo", "args": {"text": "hi"}}]
    assert calls["working"] == [
        {
            "role": "user",
            "content": "please run this\n```yaml\n- tool_name: echo\n  args:\n    text: hi\n```",
        }
    ]


def test_assistant_tail_with_callable_executes_result():
    transcript = """\
## USER
hello

## ASSISTANT
I will do it.
```yaml
- tool_name: echo
  args:
    text: hi
```
"""

    log = [{"role": "user", "content": "hello"}]

    def fake_execute(working, plan):
        assert working == [
            {"role": "user", "content": "hello"},
            {
                "role": "assistant",
                "content": "I will do it.\n```yaml\n- tool_name: echo\n  args:\n    text: hi\n```",
            },
        ]
        assert plan == [{"tool_name": "echo", "args": {"text": "hi"}}]
        return {"role": "result", "content": "done"}

    new_nodes, out = step(transcript, log, execute=fake_execute)

    assert new_nodes == [
        {
            "role": "assistant",
            "content": "I will do it.\n```yaml\n- tool_name: echo\n  args:\n    text: hi\n```",
        },
        {"role": "result", "content": "done"},
    ]
    assert out == [{"role": "result", "content": "done"}]


def test_assistant_tail_without_callable_is_noop():
    transcript = """\
## USER
hello

## ASSISTANT
thinking only
"""

    log = [{"role": "user", "content": "hello"}]

    new_nodes, out = step(transcript, log)

    assert new_nodes == [{"role": "assistant", "content": "thinking only"}]
    assert out == []


def test_malformed_yaml_does_not_become_callable():
    transcript = """\
## USER
hello
```yaml
- tool_name: echo
  args: [oops
```
"""

    log = []

    def fake_generate(_):
        return {"role": "assistant", "content": "fallback"}

    new_nodes, out = step(transcript, log, generate=fake_generate)

    assert new_nodes == [
        {
            "role": "user",
            "content": "hello\n```yaml\n- tool_name: echo\n  args: [oops\n```",
        },
        {"role": "assistant", "content": "fallback"},
    ]
    assert out == [{"role": "assistant", "content": "fallback"}]
