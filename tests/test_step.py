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


def test_bind_index_rebases_alignment_from_explicit_log_position():
    transcript = """\
## USER
hello

## ASSISTANT
hi there
"""

    log = [
        {"role": "user", "content": "old intro"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]

    new_nodes, out = step(transcript, log, bind_index=1)

    assert new_nodes == [
        {"role": "assistant", "content": "hi there"},
    ]
    assert out == []


def test_bind_index_changes_working_frontier_for_generation():
    transcript = """\
## USER
continue
"""

    log = [
        {"role": "user", "content": "old intro"},
        {"role": "assistant", "content": "old reply"},
    ]
    seen = {}

    def fake_generate(working):
        seen["working"] = working
        return {"role": "assistant", "content": "new reply"}

    new_nodes, out = step(transcript, log, generate=fake_generate, bind_index=1)

    assert new_nodes == [
        {"role": "user", "content": "continue"},
        {"role": "assistant", "content": "new reply"},
    ]
    assert out == [{"role": "assistant", "content": "new reply"}]
    assert seen["working"] == [
        {"role": "user", "content": "old intro"},
        {"role": "user", "content": "continue"},
    ]


def test_invalid_bind_index_is_rejected():
    transcript = """\
## USER
hello
"""

    with pytest.raises(ValueError, match="bind index out of range: 2"):
        step(transcript, [], bind_index=2)


def test_bind_parent_is_attached_to_first_divergent_node():
    transcript = """\
## USER
hello

## ASSISTANT
alternate
"""

    log = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]

    new_nodes, out = step(
        transcript,
        log,
        bind_index=0,
        bind_parent="n0",
    )

    assert new_nodes == [
        {"role": "assistant", "content": "alternate", "parent": "n0"},
    ]
    assert out == []


def test_bind_parent_is_not_attached_when_continuing_tip():
    transcript = """\
## USER
hello

## ASSISTANT
hi

## USER
next
"""

    log = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]

    new_nodes, out = step(
        transcript,
        log,
        bind_index=0,
        bind_parent="n1",
        storage_tip_parent="n1",
    )

    assert new_nodes == [
        {"role": "user", "content": "next"},
    ]
    assert out == []


def test_selected_non_tip_parent_is_attached_when_continuing_branch():
    transcript = """\
## USER
hello

## ASSISTANT
branch

## USER
next
"""

    log = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "branch"},
    ]

    new_nodes, out = step(
        transcript,
        log,
        bind_parent="n2",
        storage_tip_parent="n1",
    )

    assert new_nodes == [
        {"role": "user", "content": "next", "parent": "n2"},
    ]
    assert out == []


def test_callable_executes_known_tool_through_default_registry():
    transcript = """\
## USER
please run this
```yaml
- tool_name: echo
  args:
    text: hi
```
"""

    new_nodes, out = step(transcript, [])

    assert new_nodes == [
        {
            "role": "user",
            "content": "please run this\n```yaml\n- tool_name: echo\n  args:\n    text: hi\n```",
        },
        {"role": "result", "content": "hi"},
    ]
    assert out == [{"role": "result", "content": "hi"}]


def test_callable_with_unknown_tool_fails_explicitly():
    transcript = """\
## USER
please run this
```yaml
- tool_name: missing
  args: {}
```
"""

    with pytest.raises(RuntimeError, match="unknown tool: missing"):
        step(transcript, [])
