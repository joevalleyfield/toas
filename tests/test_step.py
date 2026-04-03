from pathlib import Path

import pytest

from toas.step import step


def test_first_run_appends_all():
    transcript = """\
## TOAS:USER
hello

## TOAS:ASSISTANT
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
## TOAS:USER
hello

## TOAS:ASSISTANT
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
## TOAS:USER
hello

## TOAS:ASSISTANT
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
## TOAS:USER
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
## TOAS:USER
hello

## TOAS:ASSISTANT
hi
"""

    log = []

    def fake_generate(_):
        raise AssertionError("should not be called")

    new_nodes, out = step(transcript, log, generate=fake_generate)

    assert out == []


def test_stdout_only_contains_generated():
    transcript = """\
## TOAS:USER
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
## TOAS:USER
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
## TOAS:USER
hello

## TOAS:ASSISTANT
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


def test_assistant_loose_command_yaml_canonicalizes_to_user_shell_line():
    transcript = """\
## TOAS:USER
Scan dirs

## TOAS:ASSISTANT
```yaml
command: find . -type f | head -5
```
"""
    log = [{"role": "user", "content": "Scan dirs"}]

    def fake_generate(_):
        raise AssertionError("should not be called")

    def fake_execute(_, __):
        raise AssertionError("should not be called")

    new_nodes, out = step(transcript, log, generate=fake_generate, execute=fake_execute)

    assert new_nodes == [
        {
            "role": "assistant",
            "content": "```yaml\ncommand: find . -type f | head -5\n```",
        },
        {"role": "user", "content": "$ find . -type f | head -5"},
    ]
    assert out == [{"role": "user", "content": "$ find . -type f | head -5"}]


def test_assistant_loose_command_falls_back_when_yaml_parse_fails():
    transcript = """\
## TOAS:USER
Check RPC status

## TOAS:ASSISTANT
```yaml
command: echo '{"method": "status", "params": {}}' | nc -U .toas.sock 2>&1 || echo "RPC query failed" && toas status 2>&1
```
"""
    log = [{"role": "user", "content": "Check RPC status"}]

    new_nodes, out = step(transcript, log)

    assert new_nodes == [
        {
            "role": "assistant",
            "content": "```yaml\ncommand: echo '{\"method\": \"status\", \"params\": {}}' | nc -U .toas.sock 2>&1 || echo \"RPC query failed\" && toas status 2>&1\n```",
        },
        {
            "role": "user",
            "content": "[WARN] loose command YAML parse failed; using raw `command:` text as typed.\n\n$ echo '{\"method\": \"status\", \"params\": {}}' | nc -U .toas.sock 2>&1 || echo \"RPC query failed\" && toas status 2>&1",
        },
    ]
    assert out == [new_nodes[-1]]


def test_user_loose_command_yaml_does_not_canonicalize_or_execute():
    transcript = """\
## TOAS:USER
```yaml
command: pwd
```
"""
    log = []

    def fake_generate(_):
        return {"role": "assistant", "content": "ack"}

    def fake_execute(_, __):
        raise AssertionError("should not be called")

    new_nodes, out = step(transcript, log, generate=fake_generate, execute=fake_execute)

    assert new_nodes == [
        {"role": "user", "content": "```yaml\ncommand: pwd\n```"},
        {"role": "assistant", "content": "ack"},
    ]
    assert out == [{"role": "assistant", "content": "ack"}]


def test_user_tail_with_shell_shorthand_executes_result_without_generation():
    transcript = """\
## TOAS:USER
please show me
$ pwd
"""

    log = []

    def fake_generate(_):
        raise AssertionError("should not be called")

    new_nodes, out = step(transcript, log, generate=fake_generate)

    assert new_nodes == [
        {
            "role": "user",
            "content": "please show me\n$ pwd",
        },
        {
            "role": "result",
            "content": f"[OK] shell: exit=0\nstdout:\n{Path.cwd().resolve()}",
            "payload": {
                "tool_name": "shell",
                "ok": True,
                "summary": "exit=0",
                "argv": ["pwd"],
                "cwd": str(Path.cwd().resolve()),
                "exit_code": 0,
                "stdout": str(Path.cwd().resolve()),
                "stderr": "",
                "content": f"exit=0\nstdout:\n{Path.cwd().resolve()}",
            },
        },
    ]
    assert out == [new_nodes[-1]]


def test_assistant_tail_without_callable_is_noop():
    transcript = """\
## TOAS:USER
hello

## TOAS:ASSISTANT
thinking only
"""

    log = [{"role": "user", "content": "hello"}]

    new_nodes, out = step(transcript, log)

    assert new_nodes == [{"role": "assistant", "content": "thinking only"}]
    assert out == []


def test_malformed_yaml_does_not_become_callable():
    transcript = """\
## TOAS:USER
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
## TOAS:USER
hello

## TOAS:ASSISTANT
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
## TOAS:USER
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
## TOAS:USER
hello
"""

    with pytest.raises(ValueError, match="bind index out of range: 2"):
        step(transcript, [], bind_index=2)


def test_bind_parent_is_attached_to_first_divergent_node():
    transcript = """\
## TOAS:USER
hello

## TOAS:ASSISTANT
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
## TOAS:USER
hello

## TOAS:ASSISTANT
hi

## TOAS:USER
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
## TOAS:USER
hello

## TOAS:ASSISTANT
branch

## TOAS:USER
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
## TOAS:USER
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
        {"role": "result", "content": "[OK] echo: hi", "payload": {"tool_name": "echo", "ok": True, "summary": "hi", "text": "hi"}},
    ]
    assert out == [{"role": "result", "content": "[OK] echo: hi", "payload": {"tool_name": "echo", "ok": True, "summary": "hi", "text": "hi"}}]


def test_callable_with_unknown_tool_shapes_error_result():
    transcript = """\
## TOAS:USER
please run this
```yaml
- tool_name: missing
  args: {}
```
"""

    new_nodes, out = step(transcript, [])

    assert new_nodes == [
        {
            "role": "user",
            "content": "please run this\n```yaml\n- tool_name: missing\n  args: {}\n```",
        },
        {"role": "result", "content": "[ERROR] missing: unknown tool: missing", "payload": {"tool_name": "missing", "ok": False, "summary": "unknown tool: missing", "error": "unknown tool: missing"}},
    ]
    assert out == [{"role": "result", "content": "[ERROR] missing: unknown tool: missing", "payload": {"tool_name": "missing", "ok": False, "summary": "unknown tool: missing", "error": "unknown tool: missing"}}]


def test_callable_with_missing_required_args_shapes_error_result():
    transcript = """\
## TOAS:USER
please run this
```yaml
- tool_name: echo
  args: {}
```
"""

    new_nodes, out = step(transcript, [])

    assert new_nodes == [
        {
            "role": "user",
            "content": "please run this\n```yaml\n- tool_name: echo\n  args: {}\n```",
        },
        {"role": "result", "content": "[ERROR] echo: invalid arguments for tool echo: missing text", "payload": {"tool_name": "echo", "ok": False, "summary": "invalid arguments for tool echo: missing text", "error": "invalid arguments for tool echo: missing text"}},
    ]
    assert out == [{"role": "result", "content": "[ERROR] echo: invalid arguments for tool echo: missing text", "payload": {"tool_name": "echo", "ok": False, "summary": "invalid arguments for tool echo: missing text", "error": "invalid arguments for tool echo: missing text"}}]


def test_callable_executes_bounded_shell_tool():
    transcript = """\
## TOAS:USER
run this
```yaml
- tool_name: shell
  args:
    argv: ["echo", "hi"]
```
"""

    new_nodes, out = step(transcript, [])

    assert new_nodes == [
        {
            "role": "user",
            "content": 'run this\n```yaml\n- tool_name: shell\n  args:\n    argv: ["echo", "hi"]\n```',
        },
        {
            "role": "result",
            "content": "[OK] shell: exit=0\nstdout:\nhi",
            "payload": {
                "tool_name": "shell",
                "ok": True,
                "summary": "exit=0",
                "argv": ["echo", "hi"],
                "cwd": str(__import__('pathlib').Path.cwd().resolve()),
                "exit_code": 0,
                "stdout": "hi",
                "stderr": "",
                "content": "exit=0\nstdout:\nhi",
            },
        },
    ]
    assert out == [
        {
            "role": "result",
            "content": "[OK] shell: exit=0\nstdout:\nhi",
            "payload": {
                "tool_name": "shell",
                "ok": True,
                "summary": "exit=0",
                "argv": ["echo", "hi"],
                "cwd": str(__import__('pathlib').Path.cwd().resolve()),
                "exit_code": 0,
                "stdout": "hi",
                "stderr": "",
                "content": "exit=0\nstdout:\nhi",
            },
        }
    ]
