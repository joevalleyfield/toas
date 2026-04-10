from pathlib import Path

import pytest

from toas.config import (
    BackendCatalogEntry,
    OperatorConfig,
    ExtractionPolicy,
    LLMPolicy,
    ModelCatalogEntry,
    ShellPolicy,
    flatten_config,
    valid_config_keys,
)
from toas.tools import REGISTRY as TOOL_REGISTRY, SHELL_ALLOWED
from toas.step import step, SLASH_COMMANDS, render_session_help, resolve_effective_shell_allowed


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
        {"role": "user", "content": "hello", "provenance": {"source": "user_authored"}},
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}},
    ]
    assert out == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]


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

    assert new_nodes == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]
    assert out == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]


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
        {"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}},
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
        {"role": "user", "content": "hello", "provenance": {"source": "user_authored"}},
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

    assert out == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]


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
        {"role": "user", "content": "hello", "provenance": {"source": "user_authored"}},
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
            "provenance": {"source": "user_authored"},
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
            "provenance": {"source": "user_authored"},
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


def test_assistant_shell_block_failure_auto_stages_user_adoption():
    transcript = """\
## TOAS:USER
run shell

## TOAS:ASSISTANT
```yaml
- operation: shell
  arguments:
    argv: ["sh", "-c", "echo hi"]
```
"""
    log = [{"role": "user", "content": "run shell"}]

    new_nodes, out = step(transcript, log)

    assert len(out) == 2
    assert out[0]["role"] == "result"
    assert "tool shell disallows command: sh" in out[0]["content"]
    assert "override needed" in out[0]["content"]
    assert out[1] == {
        "role": "user",
        "content": '```yaml\n- tool_name: shell\n  args:\n    argv:\n    - sh\n    - -c\n    - echo hi\n```',
        "provenance": {"source": "adopted"},
    }
    assert new_nodes[-2:] == out


def test_assistant_shell_block_failure_auto_stages_user_adoption_with_tool_name_shape():
    transcript = """\
## TOAS:USER
run shell

## TOAS:ASSISTANT
```yaml
- tool_name: shell
  args:
    argv: ["sh", "-c", "echo hi"]
```
"""
    log = [{"role": "user", "content": "run shell"}]

    new_nodes, out = step(transcript, log)

    assert len(out) == 2
    assert out[0]["role"] == "result"
    assert "tool shell disallows command: sh" in out[0]["content"]
    assert "override needed" in out[0]["content"]
    assert out[1] == {
        "role": "user",
        "content": '```yaml\n- tool_name: shell\n  args:\n    argv:\n    - sh\n    - -c\n    - echo hi\n```',
        "provenance": {"source": "adopted"},
    }
    assert new_nodes[-2:] == out


def test_assistant_shell_block_failure_manual_staging_does_not_auto_stage():
    transcript = """\
## TOAS:USER
run shell

## TOAS:ASSISTANT
```yaml
- operation: shell
  arguments:
    argv: ["sh", "-c", "echo hi"]
```
"""
    log = [{"role": "user", "content": "run shell"}]

    _, out = step(transcript, log, config=OperatorConfig(extraction=ExtractionPolicy(shell_staging="manual")))

    assert out == [
        {
            "role": "result",
            "content": "[ERROR] shell: tool shell disallows command: sh (override needed; stage in user context to run unbounded)",
            "payload": {
                "tool_name": "shell",
                "ok": False,
                "summary": "tool shell disallows command: sh (override needed; stage in user context to run unbounded)",
                "error": "tool shell disallows command: sh (override needed; stage in user context to run unbounded)",
            },
        }
    ]


def test_resolve_effective_shell_allowed_merges_config_and_transcript():
    config = OperatorConfig(shell=ShellPolicy(allowed_commands=("echo", "pwd")))
    working = [
        {"role": "user", "content": "/shell allow sh"},
        {"role": "user", "content": "/shell deny echo"},
    ]
    assert resolve_effective_shell_allowed(working, config) == ("pwd", "sh")


def test_operator_shell_list_shows_effective_and_baseline():
    transcript = """\
## TOAS:USER
/shell list
"""
    _, out = step(transcript, [])
    content = out[0]["content"]
    assert "effective shell grants:" in content
    assert "config baseline:" in content


def test_assistant_shell_respects_config_shell_allowed_commands():
    allowed = tuple(sorted(set(SHELL_ALLOWED) | {"sh"}))
    config = OperatorConfig(shell=ShellPolicy(allowed_commands=allowed))
    transcript = """\
## TOAS:USER
run shell

## TOAS:ASSISTANT
```yaml
- operation: shell
  arguments:
    argv: ["sh", "-c", "printf hi"]
```
"""
    _, out = step(transcript, [{"role": "user", "content": "run shell"}], config=config)
    assert out == [
        {
            "role": "result",
            "content": "[OK] shell: exit=0\nstdout:\nhi",
            "payload": {
                "tool_name": "shell",
                "ok": True,
                "summary": "exit=0",
                "argv": ["sh", "-c", "printf hi"],
                "cwd": str(__import__("pathlib").Path.cwd().resolve()),
                "exit_code": 0,
                "stdout": "hi",
                "stderr": "",
                "content": "exit=0\nstdout:\nhi",
            },
        }
    ]


def test_assistant_shell_respects_transcript_shell_allow_override():
    transcript = """\
## TOAS:USER
/shell allow sh

## TOAS:ASSISTANT
```yaml
- operation: shell
  arguments:
    argv: ["sh", "-c", "printf hi"]
```
"""
    _, out = step(transcript, [])
    assert out == [
        {
            "role": "result",
            "content": "[OK] shell: exit=0\nstdout:\nhi",
            "payload": {
                "tool_name": "shell",
                "ok": True,
                "summary": "exit=0",
                "argv": ["sh", "-c", "printf hi"],
                "cwd": str(__import__("pathlib").Path.cwd().resolve()),
                "exit_code": 0,
                "stdout": "hi",
                "stderr": "",
                "content": "exit=0\nstdout:\nhi",
            },
        }
    ]


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


def test_assistant_multiline_loose_command_yaml_preserves_multiline_shape():
    transcript = """\
## TOAS:USER
Write a commit message

## TOAS:ASSISTANT
```yaml
command: |
  jj describe -m "feat: Add ctypes wrapper for library

  greatest library in all the land.

  key features:
  - this
  - that
  - the other"
```
"""
    log = [{"role": "user", "content": "Write a commit message"}]

    new_nodes, out = step(transcript, log)

    assert new_nodes == [
        {
            "role": "assistant",
            "content": "```yaml\ncommand: |\n  jj describe -m \"feat: Add ctypes wrapper for library\n\n  greatest library in all the land.\n\n  key features:\n  - this\n  - that\n  - the other\"\n```",
        },
        {
            "role": "user",
            "content": (
                "jj describe -m \"feat: Add ctypes wrapper for library\n\n"
                "greatest library in all the land.\n\n"
                "key features:\n"
                "- this\n"
                "- that\n"
                "- the other\""
            ),
        },
    ]
    assert out == [new_nodes[-1]]


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


def test_user_loose_command_yaml_executes_without_canonicalization():
    transcript = """\
## TOAS:USER
```yaml
command: pwd
```
"""
    log = []

    new_nodes, out = step(transcript, log)

    assert new_nodes[0] == {"role": "user", "content": "```yaml\ncommand: pwd\n```", "provenance": {"source": "user_authored"}}
    assert out and out[0]["role"] == "result"
    assert "[OK] shell: exit=0" in out[0]["content"]


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
            "provenance": {"source": "user_authored"},
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

    assert new_nodes == [{"role": "assistant", "content": "thinking only"}, {"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]
    assert out == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]


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
            "provenance": {"source": "user_authored"},
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
        {"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}},
    ]
    assert out == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]


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
        {"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}},
    ]
    assert out == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]


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
        {"role": "user", "content": "next", "provenance": {"source": "user_authored"}},
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
        {"role": "user", "content": "next", "parent": "n2", "provenance": {"source": "user_authored"}},
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
            "provenance": {"source": "user_authored"},
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
            "provenance": {"source": "user_authored"},
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
            "provenance": {"source": "user_authored"},
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
            "provenance": {"source": "user_authored"},
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


def test_user_callable_shell_with_sh_c_uses_unbounded_user_shell_lane():
    transcript = """\
## TOAS:USER
```yaml
- operation: shell
  arguments:
    argv: ["sh", "-c", "printf hi"]
```
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": "[OK] shell: exit=0\nstdout:\nhi",
            "payload": {
                "tool_name": "shell",
                "ok": True,
                "summary": "exit=0",
                "argv": ["sh", "-c", "printf hi"],
                "cwd": str(__import__('pathlib').Path.cwd().resolve()),
                "exit_code": 0,
                "stdout": "hi",
                "stderr": "",
                "content": "exit=0\nstdout:\nhi",
            },
        }
    ]


def test_user_callable_shell_with_tool_name_shape_uses_unbounded_user_shell_lane():
    transcript = """\
## TOAS:USER
```yaml
- tool_name: shell
  args:
    argv: ["sh", "-c", "printf hi"]
```
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": "[OK] shell: exit=0\nstdout:\nhi",
            "payload": {
                "tool_name": "shell",
                "ok": True,
                "summary": "exit=0",
                "argv": ["sh", "-c", "printf hi"],
                "cwd": str(__import__('pathlib').Path.cwd().resolve()),
                "exit_code": 0,
                "stdout": "hi",
                "stderr": "",
                "content": "exit=0\nstdout:\nhi",
            },
        }
    ]


def test_callable_shell_uses_command_cwd_when_args_omit_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    workdir = tmp_path / "work"
    workdir.mkdir()
    transcript = """\
## TOAS:USER
run this
```yaml
- tool_name: shell
  args:
    argv: ["pwd"]
```
"""

    _, out = step(transcript, [], command_cwd=str(workdir))

    assert out == [
        {
            "role": "result",
            "content": f"[OK] shell: exit=0\nstdout:\n{workdir}",
            "payload": {
                "tool_name": "shell",
                "ok": True,
                "summary": "exit=0",
                "argv": ["pwd"],
                "cwd": str(workdir),
                "exit_code": 0,
                "stdout": str(workdir),
                "stderr": "",
                "content": f"exit=0\nstdout:\n{workdir}",
            },
        }
    ]


def test_operator_prompts_lists_next_command_lines_only():
    transcript = """\
## TOAS:USER
/prompts dynamic/capabilities
"""

    new_nodes, out = step(transcript, [])

    assert new_nodes == [
        {"role": "user", "content": "/prompts dynamic/capabilities", "provenance": {"source": "user_authored"}},
        {
            "role": "result",
            "content": (
                "/prompt dynamic/capabilities/overview_v1\n"
                "/prompt dynamic/capabilities/repo-work_v1\n"
                "/prompt dynamic/capabilities/start-here_v1"
            ),
        },
    ]
    assert out == [
        {
            "role": "result",
            "content": (
                "/prompt dynamic/capabilities/overview_v1\n"
                "/prompt dynamic/capabilities/repo-work_v1\n"
                "/prompt dynamic/capabilities/start-here_v1"
            ),
        }
    ]


def test_operator_prompt_renders_selected_prompt():
    transcript = """\
## TOAS:USER
/prompt dynamic/capabilities/start-here_v1
"""

    new_nodes, out = step(transcript, [])

    assert new_nodes[0] == {"role": "user", "content": "/prompt dynamic/capabilities/start-here_v1", "provenance": {"source": "user_authored"}}
    assert len(new_nodes) == 2
    assert out == [new_nodes[1]]
    assert out[0]["role"] == "result"
    assert "search or read files in the workspace" in out[0]["content"]


def test_operator_prompts_supports_top_level_browse():
    transcript = """\
## TOAS:USER
/prompts
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": (
                "/prompt dynamic\n"
                "/prompt extraction\n"
                "/prompt generation\n"
                "/prompt protocol\n"
                "/prompt repair\n"
                "/prompt session-start"
            ),
        }
    ]


def test_operator_prompt_without_args_browses_top_level():
    transcript = """\
## TOAS:USER
/prompt
"""

    _, out = step(transcript, [])
    assert out and out[0]["role"] == "result"
    assert "/prompt protocol" in out[0]["content"]


def test_operator_model_lists_available_models(monkeypatch):
    monkeypatch.setenv("TOAS_AVAILABLE_MODELS", "alpha,beta")
    transcript = """\
## TOAS:USER
/model
"""
    _, out = step(transcript, [])
    assert out == [{"role": "result", "content": "available models:\n/model alpha\n/model beta"}]


def test_operator_model_unavailable_guidance(monkeypatch):
    monkeypatch.setenv("TOAS_AVAILABLE_MODELS", "alpha,beta")
    transcript = """\
## TOAS:USER
/model missing
"""
    _, out = step(transcript, [])
    assert "chosen model unavailable" in out[0]["content"]
    assert "/model alpha" in out[0]["content"]


def test_operator_model_lists_catalog_models_in_order():
    config = OperatorConfig(
        llm=LLMPolicy(
            model="fallback",
            models=(
                ModelCatalogEntry(id="beta", label="Beta"),
                ModelCatalogEntry(id="alpha", label="Alpha"),
            ),
        )
    )
    transcript = """\
## TOAS:USER
/model
"""
    _, out = step(transcript, [], config=config)
    assert out == [{"role": "result", "content": "available models:\n/model beta\n/model alpha\n/model fallback"}]


def test_operator_backend_lists_available_backends():
    config = OperatorConfig(
        llm=LLMPolicy(
            backends=(
                BackendCatalogEntry(id="local", base_url="http://localhost:8080/v1"),
                BackendCatalogEntry(id="openrouter", base_url="https://openrouter.ai/api/v1"),
            )
        )
    )
    transcript = """\
## TOAS:USER
/backend
"""
    _, out = step(transcript, [], config=config)
    assert out == [{"role": "result", "content": "available backends:\n/backend local\n/backend openrouter"}]


def test_operator_model_list_scoped_to_selected_backend():
    config = OperatorConfig(
        llm=LLMPolicy(
            backends=(
                BackendCatalogEntry(
                    id="local",
                    base_url="http://localhost:8080/v1",
                    model="qwen",
                    models=("qwen", "gemma"),
                ),
            )
        )
    )
    transcript = """\
## TOAS:USER
/backend local

## TOAS:USER
/model
"""
    _, out = step(transcript, [], config=config)
    assert out == [{"role": "result", "content": "available models:\n/model qwen\n/model gemma"}]


def test_user_tail_with_multiline_shell_block_does_not_execute(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    transcript = """\
## TOAS:USER
$ cat <<'EOF'
alpha
EOF
"""
    def fake_generate(_):
        return {"role": "assistant", "content": "ack"}

    _, out = step(transcript, [], generate=fake_generate)
    assert out == [{"role": "assistant", "content": "ack"}]


def test_assistant_frontier_without_executable_content_auto_flips_to_user():
    transcript = """\
## TOAS:USER
hello

## TOAS:ASSISTANT
just narrative
"""
    log = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "just narrative"},
    ]
    _, out = step(transcript, log)
    assert out == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]


def test_user_tail_yaml_multiline_command_executes(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    transcript = """\
## TOAS:USER
```yaml
command: |
  cat <<'EOF'
  alpha
  EOF
```
"""
    _, out = step(transcript, [])
    assert out and out[0]["role"] == "result"
    assert "alpha" in out[0]["content"]


def test_user_shell_respects_transcript_env_modifiers(monkeypatch):
    monkeypatch.setenv("TOAS_ENV_TEST", "from-env")
    transcript = """\
## TOAS:USER
/env set TOAS_ENV_TEST from-transcript

## TOAS:USER
$ sh -lc 'printf %s \"$TOAS_ENV_TEST\"'
"""
    _, out = step(transcript, [])
    assert out[0]["role"] == "result"
    assert "from-transcript" in out[0]["content"]


def test_generation_frontier_returns_model_unavailable_continuation(monkeypatch):
    monkeypatch.setenv("TOAS_AVAILABLE_MODELS", "alpha,beta")
    transcript = """\
## TOAS:USER
/model missing

## TOAS:USER
please answer
"""

    def fake_generate(_):
        raise AssertionError("should not be called")

    _, out = step(transcript, [], generate=fake_generate)
    assert out == [
        {
                "role": "result",
                "content": "chosen model unavailable: missing\npick one of:\n/model alpha\n/model beta",
            }
        ]


def test_generation_frontier_returns_catalog_model_continuation():
    config = OperatorConfig(
        llm=LLMPolicy(
            models=(
                ModelCatalogEntry(id="catalog-a"),
                ModelCatalogEntry(id="catalog-b"),
            )
        )
    )
    transcript = """\
## TOAS:USER
/model missing

## TOAS:USER
please answer
"""

    def fake_generate(_):
        raise AssertionError("should not be called")

    _, out = step(transcript, [], config=config, generate=fake_generate)
    assert out == [
        {
            "role": "result",
            "content": "chosen model unavailable: missing\npick one of:\n/model catalog-a\n/model catalog-b",
        }
    ]


def test_generation_frontier_returns_backend_unavailable_continuation():
    config = OperatorConfig(
        llm=LLMPolicy(
            backends=(
                BackendCatalogEntry(id="local", base_url="http://localhost:8080/v1"),
                BackendCatalogEntry(id="openrouter", base_url="https://openrouter.ai/api/v1"),
            )
        )
    )
    transcript = """\
## TOAS:USER
/backend missing

## TOAS:USER
please answer
"""

    def fake_generate(_):
        raise AssertionError("should not be called")

    _, out = step(transcript, [], config=config, generate=fake_generate)
    assert out == [
        {
            "role": "result",
            "content": "chosen backend unavailable: missing\npick one of:\n/backend local\n/backend openrouter",
        }
    ]


def test_operator_pwd_uses_command_cwd():
    transcript = """\
## TOAS:USER
/pwd
"""

    resolved_tmp = str(Path("/tmp").resolve())
    _, out = step(transcript, [], command_cwd="/tmp")

    assert out == [{"role": "result", "content": resolved_tmp}]


def test_operator_cd_sets_context_update():
    transcript = """\
## TOAS:USER
/cd /tmp
"""

    resolved_tmp = str(Path("/tmp").resolve())
    _, out = step(transcript, [], command_cwd=".", workspace_mode="unbounded")

    assert out == [
        {
            "role": "result",
            "content": resolved_tmp,
            "context_update": {
                "cwd": resolved_tmp,
                "previous_cwd": str(Path.cwd().resolve()),
            },
        }
    ]


def test_operator_cd_dash_uses_previous_command_cwd():
    transcript = """\
## TOAS:USER
/cd -
"""

    resolved_tmp = str(Path("/tmp").resolve())
    _, out = step(transcript, [], command_cwd="/tmp", previous_command_cwd="/", workspace_mode="unbounded")

    assert out == [
        {
            "role": "result",
            "content": "/",
            "context_update": {
                "cwd": "/",
                "previous_cwd": resolved_tmp,
            },
        }
    ]


def test_assistant_tail_operator_command_is_noop():
    transcript = """\
## TOAS:ASSISTANT
/pwd
"""

    new_nodes, out = step(transcript, [], command_cwd="/tmp")

    assert new_nodes == [{"role": "assistant", "content": "/pwd"}, {"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]
    assert out == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]


def test_assistant_tail_shell_shorthand_is_noop():
    transcript = """\
## TOAS:ASSISTANT
$ pwd
"""

    new_nodes, out = step(transcript, [], command_cwd="/tmp")

    assert new_nodes == [{"role": "assistant", "content": "$ pwd"}, {"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]
    assert out == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]


def test_operator_workspace_add_emits_workspace_update(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    subdir = tmp_path / "extra"
    subdir.mkdir()
    transcript = f"""\
## TOAS:USER
/workspace add {subdir}
"""

    _, out = step(transcript, [], workspace_roots=[str(tmp_path)], workspace_mode="strict")

    assert out == [
        {
            "role": "result",
            "content": f"{tmp_path}\n{subdir}",
            "workspace_update": {"mode": "strict", "roots": [str(tmp_path), str(subdir)]},
        }
    ]


def test_operator_workspace_mode_unbounded_updates_mode(tmp_path):
    transcript = """\
## TOAS:USER
/workspace mode unbounded
"""

    _, out = step(transcript, [], workspace_roots=[str(tmp_path)], workspace_mode="strict")
    assert out == [
        {
            "role": "result",
            "content": "mode=unbounded",
            "workspace_update": {"mode": "unbounded", "roots": [str(tmp_path)]},
        }
    ]


def test_operator_cd_rejects_target_outside_strict_workspace(tmp_path):
    transcript = """\
## TOAS:USER
/cd /
"""
    _, out = step(transcript, [], workspace_roots=[str(tmp_path)], workspace_mode="strict", command_cwd=str(tmp_path))
    assert out == [{"role": "result", "content": "[ERROR] /cd: cwd outside allowed workspace roots"}]


def test_operator_workspace_lists_command_menu(tmp_path):
    transcript = """\
## TOAS:USER
/workspace
"""
    _, out = step(transcript, [], workspace_roots=[str(tmp_path)], workspace_mode="strict")
    assert out == [
        {
            "role": "result",
            "content": (
                "/workspace\n"
                "/workspace mode strict\n"
                "/workspace mode unbounded\n"
                "/workspace add <path>\n"
                "/workspace remove <path>\n"
                "/workspace reset\n"
                f"/workspace remove {tmp_path}\n"
                "/workspace mode strict"
            ),
        }
    ]


def test_operator_workspace_lists_command_menu_in_unbounded_mode(tmp_path):
    transcript = """\
## TOAS:USER
/workspace
"""
    _, out = step(transcript, [], workspace_roots=[str(tmp_path)], workspace_mode="unbounded")
    assert out == [
        {
            "role": "result",
            "content": (
                "/workspace\n"
                "/workspace mode strict\n"
                "/workspace mode unbounded\n"
                "/workspace add <path>\n"
                "/workspace remove <path>\n"
                "/workspace reset\n"
                f"/workspace remove {tmp_path}\n"
                "/workspace mode unbounded"
            ),
        }
    ]


def test_operator_extract_preview_targets_latest_assistant_callable():
    transcript = """\
## TOAS:ASSISTANT
I can run this:
```yaml
- tool_name: echo
  args:
    text: hi
```

## TOAS:USER
/extract
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": (
                "extract candidates from latest assistant message:\n"
                "1. tool_plan\n"
                "```yaml\n"
                "- tool_name: echo\n"
                "  args:\n"
                "    text: hi\n"
                "```"
            ),
        }
    ]


def test_operator_extract_preview_ignores_older_assistant_when_latest_has_callable():
    transcript = """\
## TOAS:ASSISTANT
old
```yaml
- tool_name: echo
  args:
    text: one
```

## TOAS:ASSISTANT
new
```yaml
- tool_name: echo
  args:
    text: two
```

## TOAS:USER
/extract
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": (
                "extract candidates from latest assistant message:\n"
                "1. tool_plan\n"
                "```yaml\n"
                "- tool_name: echo\n"
                "  args:\n"
                "    text: two\n"
                "```"
            ),
        }
    ]


def test_operator_extract_preview_errors_without_prior_assistant():
    transcript = """\
## TOAS:USER
/extract
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": "[ERROR] /extract: no prior assistant message available for /extract",
        }
    ]


def test_operator_extract_preview_errors_when_no_candidates():
    transcript = """\
## TOAS:ASSISTANT
hello there

## TOAS:USER
/extract
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": "[ERROR] /extract: latest assistant message has no extractable callable intent",
        }
    ]


def test_operator_extract_selection_adopts_tool_plan_as_user_message():
    transcript = """\
## TOAS:ASSISTANT
please run this
```yaml
- tool_name: echo
  args:
    text: hi
```

## TOAS:USER
/extract 1
"""

    _, out = step(transcript, [])

    assert len(out) == 1
    assert out[0]["role"] == "user"
    assert out[0]["content"] == "```yaml\n- tool_name: echo\n  args:\n    text: hi\n```"


def test_operator_extract_preview_lists_candidates_with_concrete_content():
    transcript = """\
## TOAS:ASSISTANT
please run this
```yaml
- tool_name: echo
  args:
    text: hi
```
```yaml
command: pwd
```

## TOAS:USER
/extract
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": (
                "extract candidates from latest assistant message:\n"
                "1. tool_plan\n"
                "```yaml\n"
                "- tool_name: echo\n"
                "  args:\n"
                "    text: hi\n"
                "```\n"
                "2. assistant_loose_command\n"
                "$ pwd"
            ),
        }
    ]


def test_operator_extract_selection_adopts_loose_command_as_user_shell_line():
    transcript = """\
## TOAS:ASSISTANT
```yaml
command: find . -type f | head -5
```

## TOAS:USER
/extract 1
"""

    _, out = step(transcript, [])

    assert len(out) == 1
    assert out[0] == {"role": "user", "content": "$ find . -type f | head -5", "provenance": {"source": "adopted"}}


def test_operator_extract_lists_multiline_loose_command_as_shell_block_preview():
    transcript = """\
## TOAS:ASSISTANT
```yaml
command: |
  echo one
  echo two
```

## TOAS:USER
/extract
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": (
                "extract candidates from latest assistant message:\n"
                "1. assistant_loose_command\n"
                "```sh\n"
                "echo one\n"
                "echo two\n"
                "```"
            ),
        }
    ]


def test_operator_extract_selection_adopts_multiline_loose_command_verbatim():
    transcript = """\
## TOAS:ASSISTANT
```yaml
command: |
  echo alpha
  echo beta
```

## TOAS:USER
/extract 1
"""

    _, out = step(transcript, [])

    assert len(out) == 1
    assert out[0] == {
        "role": "user",
        "content": "echo alpha\necho beta",
        "provenance": {"source": "adopted"},
    }


def test_operator_extract_selection_adopts_multi_tool_list_verbatim():
    transcript = """\
## TOAS:ASSISTANT
```yaml
- operation: echo
  arguments:
    text: alpha
- operation: echo
  arguments:
    text: beta
```

## TOAS:USER
/extract 1
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "user",
            "content": (
                "```yaml\n"
                "- operation: echo\n"
                "  arguments:\n"
                "    text: alpha\n"
                "- operation: echo\n"
                "  arguments:\n"
                "    text: beta\n"
                "```"
            ),
            "provenance": {"source": "adopted"},
        }
    ]


def test_user_tail_multi_tool_list_executes_all_operations():
    transcript = """\
## TOAS:USER
```yaml
- operation: echo
  arguments:
    text: alpha
- operation: echo
  arguments:
    text: beta
```
"""
    _, out = step(transcript, [])
    assert out == [
        {"role": "result", "content": "[OK] echo: alpha", "payload": {"tool_name": "echo", "ok": True, "summary": "alpha", "text": "alpha"}},
        {"role": "result", "content": "[OK] echo: beta", "payload": {"tool_name": "echo", "ok": True, "summary": "beta", "text": "beta"}},
    ]


def test_operator_extract_rejects_out_of_range_index():
    transcript = """\
## TOAS:ASSISTANT
```yaml
- tool_name: echo
  args:
    text: hi
```

## TOAS:USER
/extract 2
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": "[ERROR] /extract: index out of range: 2",
        }
    ]


def test_operator_extract_rejects_legacy_flags_after_pivot():
    transcript = """\
## TOAS:ASSISTANT
```yaml
- tool_name: echo
  args:
    text: hi
```

## TOAS:USER
/extract --dry-run
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": "[ERROR] /extract: usage: /extract [index]",
        }
    ]


def test_operator_outline_lists_messages_with_annotations():
    transcript = """\
## TOAS:USER
run this
```yaml
- tool_name: echo
  args:
    text: hi
```

## TOAS:ASSISTANT
```yaml
command: pwd
```

## TOAS:USER
/outline
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": (
                "1. USER: run this [tool_plan]\n"
                "2. ASSISTANT: ```yaml [loose_command]\n"
                "3. USER: /outline [/outline]"
            ),
        }
    ]


def test_operator_outline_errors_with_args():
    transcript = """\
## TOAS:USER
/outline now
"""

    _, out = step(transcript, [])

    assert out == [{"role": "result", "content": "[ERROR] /outline: usage: /outline"}]


def test_operator_compact_dry_run_reports_matching_blocks():
    transcript = """\
## TOAS:ASSISTANT
here

## RESULT

123456

## TOAS:USER
/compact --dry-run --threshold 5
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": "compact dry-run: 1 RESULT block(s) above threshold=5\n1. 6 chars",
        }
    ]


def test_operator_compact_emits_session_update_and_is_idempotent():
    transcript = """\
## TOAS:ASSISTANT
here

## RESULT

abcdef

## TOAS:USER
/compact --threshold 5
"""

    _, out = step(transcript, [])

    assert out[0]["role"] == "result"
    assert out[0]["content"] == "compact: collapsed 1 RESULT block(s) above threshold=5"
    assert out[0]["session_update"] == {
        "transcript": (
            "## TOAS:ASSISTANT\n"
            "here\n"
            "\n"
            "## RESULT\n"
            "\n"
            "[RESULT: 6 chars, collapsed]\n"
            "## TOAS:USER\n"
            "/compact --threshold 5\n"
        )
    }

    _, out2 = step(out[0]["session_update"]["transcript"], [])
    assert out2 == [{"role": "result", "content": "compact: no RESULT blocks above threshold=5"}]


def test_step_frontier_plan_respects_yaml_position_first():
    transcript = """\
## TOAS:USER
```yaml
- tool_name: echo
  args:
    text: first
```
```yaml
not_a_plan: true
```
"""

    _, out = step(
        transcript,
        [],
        config=OperatorConfig(extraction=ExtractionPolicy(yaml_position="first")),
    )

    assert out == [
        {
            "role": "result",
            "content": "[OK] echo: first",
            "payload": {"tool_name": "echo", "ok": True, "summary": "first", "text": "first"},
        }
    ]


def test_step_frontier_plan_respects_yaml_position_any_unique():
    transcript = """\
## TOAS:USER
```yaml
not_a_plan: true
```
```yaml
- tool_name: echo
  args:
    text: picked
```
"""

    _, out = step(
        transcript,
        [],
        config=OperatorConfig(extraction=ExtractionPolicy(yaml_position="any")),
    )

    assert out == [
        {
            "role": "result",
            "content": "[OK] echo: picked",
            "payload": {"tool_name": "echo", "ok": True, "summary": "picked", "text": "picked"},
        }
    ]


def test_operator_extract_preview_reports_no_candidates_for_latest_assistant():
    transcript = """\
## TOAS:ASSISTANT
hello there

## TOAS:USER
/extract
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": "[ERROR] /extract: latest assistant message has no extractable callable intent",
        }
    ]


def test_operator_extract_preview_reports_skipped_callable_looking_invalid_block():
    transcript = """\
## TOAS:ASSISTANT
```yaml
tool_name: list_files
args:
  text: *
```

## TOAS:USER
/extract
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": "[ERROR] /extract: latest assistant message has no extractable callable intent\n"
            "skipped callable-looking blocks:\n"
            "1. yaml parse error at line 3, column 10 near `tool_name: list_files`",
        }
    ]


def test_operator_extract_preview_accepts_operation_alias_shape():
    transcript = """\
## TOAS:ASSISTANT
```yaml
operation: echo
arguments:
  text: hi
```

## TOAS:USER
/extract 1
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "user",
            "content": "```yaml\noperation: echo\narguments:\n  text: hi\n```",
            "provenance": {"source": "adopted"},
        }
    ]


def test_operator_extract_preview_reports_conflicting_callable_keys():
    transcript = """\
## TOAS:ASSISTANT
```yaml
tool_name: echo
operation: search
args:
  text: hi
```

## TOAS:USER
/extract
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": "[ERROR] /extract: latest assistant message has no extractable callable intent\n"
            "skipped callable-looking blocks:\n"
            "1. invalid callable block: conflicting callable keys: tool_name and operation",
        }
    ]


def test_operator_replay_lists_candidates():
    transcript = """\
## TOAS:ASSISTANT
```yaml
- tool_name: echo
  args:
    text: hi
```

## TOAS:USER
/replay
"""
    _, out = step(transcript, [])
    assert "replay candidate: 1 found" in out[0]["content"]
    assert "confirm with: /replay --index 1" in out[0]["content"]


def test_operator_replay_executes_selected_candidate():
    transcript = """\
## TOAS:ASSISTANT
```yaml
- tool_name: echo
  args:
    text: hi
```

## TOAS:USER
/replay --index 1
"""

    def fake_execute(working, plan):
        assert plan == [{"tool_name": "echo", "args": {"text": "hi"}}]
        return {"role": "result", "content": "ran replay"}

    _, out = step(transcript, [], execute=fake_execute)
    assert out[0]["content"] == "ran replay"
    assert out[0]["replay_execution"]["target_message_index"] == 1


def test_operator_replay_rejects_already_executed_without_force():
    transcript = """\
## TOAS:ASSISTANT
```yaml
- tool_name: echo
  args:
    text: hi
```

## TOAS:USER
/replay --index 1
"""
    _, out = step(transcript, [], already_executed_indices={1})
    assert "target already has tool_request records" in out[0]["content"]


def test_config_show_returns_flat_keys():
    transcript = """\
## TOAS:USER
/config show
"""

    _, out = step(transcript, [])

    assert len(out) == 1
    content = out[0]["content"]
    assert "extraction.yaml_position = tail" in content
    assert "extraction.user_shell = True" in content
    assert "generation.thinking_mode = disabled" in content
    assert "generation.avoid_terms = ('tool', 'tool-call', 'function', 'function-call')" in content
    assert "generation.transport_mode = chat_messages" in content
    assert "llm.base_url = " in content


def test_config_show_no_args_same_as_explicit_show():
    transcript = """\
## TOAS:USER
/config
"""

    _, out = step(transcript, [])

    assert len(out) == 1
    assert "extraction.yaml_position" in out[0]["content"]


def test_config_set_returns_config_update_payload():
    transcript = """\
## TOAS:USER
/config set extraction.yaml_position any
"""

    _, out = step(transcript, [])

    assert len(out) == 1
    assert out[0].get("config_update") == {"extraction": {"yaml_position": "any"}}


def test_config_set_bool_false():
    transcript = """\
## TOAS:USER
/config set extraction.user_shell false
"""

    _, out = step(transcript, [])

    assert len(out) == 1
    assert out[0]["config_update"] == {"extraction": {"user_shell": False}}


def test_config_set_generation_avoid_terms_parses_comma_list():
    transcript = """\
## TOAS:USER
/config set generation.avoid_terms alpha,beta
"""

    _, out = step(transcript, [])

    assert len(out) == 1
    assert out[0]["config_update"] == {"generation": {"avoid_terms": ("alpha", "beta")}}


def test_config_set_llm_model():
    transcript = """\
## TOAS:USER
/config set llm.model local-model
"""
    _, out = step(transcript, [])
    assert out[0]["config_update"] == {"llm": {"model": "local-model"}}


def test_config_set_runtime_toggle():
    transcript = """\
## TOAS:USER
/config set runtime.streaming_mode disabled
"""
    _, out = step(transcript, [])
    assert out[0]["config_update"] == {"runtime": {"streaming_mode": "disabled"}}


def test_config_set_backend_mode():
    transcript = """\
## TOAS:USER
/config set backend.mode managed-local
"""
    _, out = step(transcript, [])
    assert out[0]["config_update"] == {"backend": {"mode": "managed-local"}}


def test_config_backend_add_and_set():
    transcript = """\
## TOAS:USER
/config backend add local http://localhost:8080/v1
"""
    _, out = step(transcript, [])
    backends = out[0]["config_update"]["llm"]["backends"]
    assert backends[0]["id"] == "local"
    assert backends[0]["base_url"] == "http://localhost:8080/v1"


def test_config_show_labels_runtime_vs_startup_only():
    transcript = """\
## TOAS:USER
/config show
"""
    _, out = step(transcript, [])
    content = out[0]["content"]
    assert "runtime-adjustable by TOAS:" in content
    assert "backend startup-only constraints:" in content


def test_config_show_sources():
    transcript = """\
## TOAS:USER
/config show --sources
"""
    _, out = step(transcript, [], config_sources={"llm.model": "session_override"})
    content = out[0]["content"]
    assert "llm.model" in content
    assert "[source=session_override]" in content


def test_config_secret_set_llm_api_key_non_durable_signal():
    transcript = """\
## TOAS:USER
/config secret set llm_api_key supersecret
"""
    _, out = step(transcript, [])
    assert "supersecret" not in out[0]["content"]
    assert out[0]["secret_update"] == {"action": "set", "key": "llm_api_key", "value": "supersecret"}


def test_config_secret_unset_llm_api_key():
    transcript = """\
## TOAS:USER
/config secret unset llm_api_key
"""
    _, out = step(transcript, [])
    assert out[0]["secret_update"] == {"action": "unset", "key": "llm_api_key"}


def test_config_set_unknown_key_returns_error():
    transcript = """\
## TOAS:USER
/config set extraction.bogus value
"""

    _, out = step(transcript, [])

    assert out[0]["content"].startswith("[ERROR] /config:")
    assert "unknown config key" in out[0]["content"]
    assert "try: /config show" in out[0]["content"]


def test_config_unset_key_returns_config_update_op():
    transcript = """\
## TOAS:USER
/config unset llm.model
"""
    _, out = step(transcript, [])
    assert out[0]["config_update"] == {"__op__": "unset", "key": "llm.model"}


def test_config_restore_returns_config_update_op():
    transcript = """\
## TOAS:USER
/config restore
"""
    _, out = step(transcript, [])
    assert out[0]["config_update"] == {"__op__": "restore"}


def test_config_load_returns_nested_config_update(tmp_path):
    cfg = tmp_path / "alt.toml"
    cfg.write_text('[generation]\nmax_retries = 3\n', encoding="utf-8")
    transcript = f"""\
## TOAS:USER
/config load {cfg}
"""
    _, out = step(transcript, [], command_cwd=str(tmp_path))
    assert out[0]["config_update"] == {"generation": {"max_retries": 3}}


def test_config_save_returns_save_payload():
    transcript = """\
## TOAS:USER
/config save custom.toml
"""
    _, out = step(transcript, [])
    assert out[0]["config_save"] == {"path": "custom.toml", "flat": flatten_config(OperatorConfig())}


def test_config_set_wrong_arg_count_returns_error():
    transcript = """\
## TOAS:USER
/config set extraction.user_shell
"""

    _, out = step(transcript, [])

    assert out[0]["content"].startswith("[ERROR] /config:")


def test_step_respects_user_shell_disabled():
    config = OperatorConfig(extraction=ExtractionPolicy(user_shell=False))
    transcript = """\
## TOAS:USER
$ echo hello
"""

    _, out = step(transcript, [], config=config)

    # With user_shell disabled, no shell execution — falls through to generate
    assert out == []


def test_step_respects_operator_command_disabled():
    config = OperatorConfig(extraction=ExtractionPolicy(operator_command=False))
    transcript = """\
## TOAS:USER
/config show
"""

    _, out = step(transcript, [], config=config)

    # With operator_command disabled, /config is not recognized — falls through to generate
    assert out == []


def test_step_default_config_unchanged_behavior():
    # Default config must not change observable behavior from before config existed
    transcript = """\
## TOAS:USER
hello
"""

    _, out_default = step(transcript, [])
    _, out_explicit = step(transcript, [], config=OperatorConfig())

    assert out_default == out_explicit


def test_user_authored_provenance_on_transcript_user_nodes():
    transcript = """\
## TOAS:USER
hello
"""

    new_nodes, _ = step(transcript, [])

    user_nodes = [n for n in new_nodes if n.get("role") == "user"]
    for node in user_nodes:
        assert node.get("provenance") == {"source": "user_authored"}


def test_user_authored_provenance_not_on_assistant_nodes():
    transcript = """\
## TOAS:USER
hello

## TOAS:ASSISTANT
hi
"""

    new_nodes, _ = step(transcript, [])

    assistant_nodes = [n for n in new_nodes if n.get("role") == "assistant"]
    for node in assistant_nodes:
        assert "provenance" not in node


def test_adopted_provenance_on_extract_selection():
    transcript = """\
## TOAS:ASSISTANT
```yaml
- tool_name: echo
  args:
    text: hi
```

## TOAS:USER
/extract 1
"""

    _, out = step(transcript, [])

    assert len(out) == 1
    assert out[0]["role"] == "user"
    assert out[0].get("provenance") == {"source": "adopted"}


def test_no_provenance_on_nodes_already_in_log():
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

    new_nodes, _ = step(transcript, log)

    assert new_nodes == [{"role": "user", "content": "", "metadata": {"transient_projection": "frontier_flip"}}]


def test_user_correction_provenance_when_user_node_replaces_llm_generated():
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "hello", "provenance": {"source": "user_authored"}},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "original", "provenance": {"source": "llm_generated"}},
    ]
    transcript = """\
## TOAS:USER
hello

## TOAS:USER
my correction
"""

    new_nodes, _ = step(transcript, log)

    assert len(new_nodes) == 1
    assert new_nodes[0]["role"] == "user"
    assert new_nodes[0]["content"] == "my correction"
    assert new_nodes[0]["provenance"] == {"source": "user_correction", "corrects": "n1"}


def test_user_correction_corrects_pointer_matches_original_id():
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "hello", "provenance": {"source": "user_authored"}},
        {"id": "n5", "parent": "n0", "role": "assistant", "content": "generated", "provenance": {"source": "llm_generated"}},
    ]
    transcript = """\
## TOAS:USER
hello

## TOAS:USER
fix
"""

    new_nodes, _ = step(transcript, log)

    assert new_nodes[0]["provenance"]["corrects"] == "n5"


def test_no_correction_provenance_when_prior_node_has_no_provenance():
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "hello", "metadata": {}},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "original", "metadata": {}},
    ]
    transcript = """\
## TOAS:USER
hello

## TOAS:USER
my text
"""

    new_nodes, _ = step(transcript, log)

    assert len(new_nodes) == 1
    # no provenance — pre-provenance message, cannot confirm correction
    assert "provenance" not in new_nodes[0]


def test_no_correction_provenance_when_prior_node_is_user_authored():
    log = [
        {"id": "n0", "parent": None, "role": "user", "content": "hello", "provenance": {"source": "user_authored"}},
        {"id": "n1", "parent": "n0", "role": "user", "content": "original", "provenance": {"source": "user_authored"}},
    ]
    transcript = """\
## TOAS:USER
hello

## TOAS:USER
edited
"""

    new_nodes, _ = step(transcript, log)

    assert new_nodes[0]["provenance"] == {"source": "user_authored"}


def test_user_authored_when_no_prior_log_position_at_divergence():
    transcript = """\
## TOAS:USER
new message
"""

    new_nodes, _ = step(transcript, [])

    assert new_nodes[0]["provenance"] == {"source": "user_authored"}


def test_user_authored_provenance_not_set_on_node_that_already_has_provenance():
    transcript = """\
## TOAS:USER
hello
"""

    # simulate a node with pre-existing provenance passing through
    # (e.g., from a future source not covered by this task)
    nodes = [{"role": "user", "content": "hello", "provenance": {"source": "adopted"}}]
    from toas.step import _annotate_branch_parent
    annotated = _annotate_branch_parent(nodes, continuation_parent=None, storage_tip_parent=None)
    result = [
        {**node, "provenance": {"source": "user_authored"}}
        if node.get("role") == "user" and "provenance" not in node
        else node
        for node in annotated
    ]

    assert result[0]["provenance"] == {"source": "adopted"}


# --- slash command registry and /help ---

def test_slash_commands_registry_is_non_empty():
    assert len(SLASH_COMMANDS) > 0


def test_slash_commands_registry_includes_known_commands():
    names = {name for name, _, _ in SLASH_COMMANDS}
    for expected in ("help", "config", "extract", "compact", "outline", "cd", "pwd"):
        assert expected in names, f"expected {expected!r} in SLASH_COMMANDS"


def test_render_session_help_includes_all_slash_commands():
    out = render_session_help()
    for name, usage, _ in SLASH_COMMANDS:
        assert usage in out, f"expected usage {usage!r} in render_session_help output"


def test_render_session_help_includes_all_tools():
    out = render_session_help()
    for name in TOOL_REGISTRY:
        assert name in out


def test_render_session_help_includes_shell_allowlist():
    out = render_session_help()
    for cmd in SHELL_ALLOWED:
        assert cmd in out


def test_render_session_help_includes_all_config_keys():
    out = render_session_help()
    for key in valid_config_keys():
        assert key in out


def _make_help_transcript():
    return """\
## TOAS:SYSTEM
system
## TOAS:USER
/help
"""


def test_slash_help_returns_result_node():
    _, consequences = step(_make_help_transcript(), [])
    assert consequences[0]["role"] == "result"


def test_slash_help_result_contains_slash_commands():
    _, consequences = step(_make_help_transcript(), [])
    content = consequences[0]["content"]
    assert "/extract" in content
    assert "/config" in content


def test_slash_help_result_contains_tools():
    _, consequences = step(_make_help_transcript(), [])
    content = consequences[0]["content"]
    assert "shell" in content
    assert "read_file" in content


def test_slash_help_result_contains_config_keys():
    _, consequences = step(_make_help_transcript(), [])
    content = consequences[0]["content"]
    assert "generation.thinking_mode" in content


def test_slash_help_includes_common_goals_guidance():
    _, consequences = step(_make_help_transcript(), [])
    content = consequences[0]["content"]
    assert "Common goals:" in content
    assert "/config set generation.thinking_mode enabled" in content
    assert "/config set llm.model qwen3.5-35b-a3b" in content


def test_config_show_includes_quick_edit_examples():
    transcript = """\
## TOAS:USER
/config show
"""
    _, out = step(transcript, [])
    content = out[0]["content"]
    assert "Quick edits:" in content
    assert "/config set generation.retry_delay_s 0.25" in content


def test_config_set_generation_thinking_mode_error_includes_example():
    transcript = """\
## TOAS:USER
/config set generation.thinking_mode nope
"""
    _, out = step(transcript, [])
    content = out[0]["content"]
    assert "expected disabled|enabled" in content
    assert "example: /config set generation.thinking_mode enabled" in content


def test_config_set_generation_transport_mode_error_includes_example():
    transcript = """\
## TOAS:USER
/config set generation.transport_mode nope
"""
    _, out = step(transcript, [])
    content = out[0]["content"]
    assert "expected chat_messages|single_user_blob" in content
    assert "example: /config set generation.transport_mode single_user_blob" in content


def test_config_set_success_includes_session_scope_and_revert_hint():
    transcript = """\
## TOAS:USER
/config set generation.thinking_mode enabled
"""
    _, out = step(transcript, [])
    content = out[0]["content"]
    assert "Updated generation.thinking_mode for this session." in content
    assert "Persist in project defaults by editing toas.toml." in content
    assert "Revert in-session with: /config set generation.thinking_mode disabled" in content
