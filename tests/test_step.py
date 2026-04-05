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
        {"role": "user", "content": "/prompts dynamic/capabilities"},
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

    assert new_nodes[0] == {"role": "user", "content": "/prompt dynamic/capabilities/start-here_v1"}
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


def test_operator_extract_dry_run_selects_single_candidate():
    transcript = """\
## TOAS:USER
please run this
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
            "content": (
                "extract dry-run target=1/1\n"
                "message=1 role=user\n"
                "kind=tool_plan\n"
                "summary=1 tool call(s)"
            ),
        }
    ]


def test_operator_extract_dry_run_reports_ambiguity_without_index():
    transcript = """\
## TOAS:USER
first
```yaml
- tool_name: echo
  args:
    text: one
```

## TOAS:USER
second
```yaml
- tool_name: echo
  args:
    text: two
```

## TOAS:USER
/extract --dry-run
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": (
                "[ERROR] /extract: ambiguous extract target; rerun with /extract --dry-run --index <n>\n"
                "1. message=1 role=user kind=tool_plan summary=1 tool call(s)\n"
                "2. message=2 role=user kind=tool_plan summary=1 tool call(s)"
            ),
        }
    ]


def test_operator_extract_dry_run_can_select_ambiguous_candidate_by_index():
    transcript = """\
## TOAS:USER
first
```yaml
- tool_name: echo
  args:
    text: one
```

## TOAS:USER
second
```yaml
- tool_name: echo
  args:
    text: two
```

## TOAS:USER
/extract --dry-run --index 2
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": (
                "extract dry-run target=2/2\n"
                "message=2 role=user\n"
                "kind=tool_plan\n"
                "summary=1 tool call(s)"
            ),
        }
    ]


def test_operator_extract_dry_run_errors_when_no_candidates():
    transcript = """\
## TOAS:USER
hello

## TOAS:USER
/extract --dry-run
"""

    _, out = step(transcript, [])

    assert out == [
        {
            "role": "result",
            "content": "[ERROR] /extract: no extractable callable messages found",
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
