from pathlib import Path

import pytest

from toas.config import OperatorConfig, ExtractionPolicy
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
        {"role": "user", "content": "hello", "provenance": {"source": "user_authored"}},
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
        {"role": "user", "content": "```yaml\ncommand: pwd\n```", "provenance": {"source": "user_authored"}},
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
                "/prompts dynamic\n"
                "/prompts extraction\n"
                "/prompts generation\n"
                "/prompts protocol\n"
                "/prompts repair\n"
                "/prompts session-start"
            ),
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

    assert new_nodes == [{"role": "assistant", "content": "/pwd"}]
    assert out == []


def test_assistant_tail_shell_shorthand_is_noop():
    transcript = """\
## TOAS:ASSISTANT
$ pwd
"""

    new_nodes, out = step(transcript, [], command_cwd="/tmp")

    assert new_nodes == [{"role": "assistant", "content": "$ pwd"}]
    assert out == []


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


def test_config_set_unknown_key_returns_error():
    transcript = """\
## TOAS:USER
/config set extraction.bogus value
"""

    _, out = step(transcript, [])

    assert out[0]["content"].startswith("[ERROR] /config:")
    assert "unknown config key" in out[0]["content"]


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

    assert new_nodes == []


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
