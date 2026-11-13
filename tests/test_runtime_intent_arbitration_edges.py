from __future__ import annotations

from types import SimpleNamespace

import toas.runtime.intent_arbitration_edges as iae
from toas.runtime.intent_arbitration_edges import select_user_intent_candidates


def test_select_user_intent_candidates_orders_by_text_position():
    content = "```yaml\n- operation: echo\n  arguments:\n    text: hi\n```\n/help\n$ echo hi"
    out = select_user_intent_candidates(
        content=content,
        plan=[{"tool_name": "echo", "args": {"text": "hi"}}],
        operator_command=("help", []),
        shell_command="echo hi",
        shell_argv=["echo", "hi"],
        yaml_position="tail",
    )
    assert [item["kind"] for item in out] == ["plan", "operator", "shell"]
    assert [item["intent_id"] for item in out] == ["d1", "d2", "d3"]


def test_select_user_intent_candidates_ignores_yaml_position_for_execution_stream():
    content = (
        "```yaml\n- operation: echo\n  arguments:\n    text: first\n```\n"
        "/help\n"
        "```yaml\n- operation: echo\n  arguments:\n    text: second\n```\n"
    )
    out = select_user_intent_candidates(
        content=content,
        plan=None,
        operator_command=("help", []),
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
    )
    assert [item["kind"] for item in out] == ["plan", "operator", "plan"]
    assert out[0]["value"][0]["args"]["text"] == "first"
    assert out[2]["value"][0]["args"]["text"] == "second"


def test_select_user_intent_candidates_falls_back_to_stable_kind_order_when_positions_unknown():
    out = select_user_intent_candidates(
        content="mixed without markers",
        plan=[{"tool_name": "echo", "args": {"text": "x"}}],
        operator_command=("help", []),
        shell_command="echo hi",
        shell_argv=["echo", "hi"],
        yaml_position="tail",
    )
    assert [item["kind"] for item in out] == ["operator", "plan", "shell"]


def test_select_user_intent_candidates_in_order_includes_multiple_yaml_blocks():
    content = (
        "```yaml\n- operation: echo\n  arguments:\n    text: first\n```\n"
        "/help\n"
        "```yaml\n- operation: echo\n  arguments:\n    text: second\n```\n"
    )
    out = select_user_intent_candidates(
        content=content,
        plan=None,
        operator_command=("help", []),
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
    )
    assert [item["kind"] for item in out] == ["plan", "operator", "plan"]
    assert out[0]["value"][0]["args"]["text"] == "first"
    assert out[2]["value"][0]["args"]["text"] == "second"


def test_select_user_intent_candidates_plan_fallback_when_no_yaml_candidates():
    out = select_user_intent_candidates(
        content="no yaml here",
        plan=[{"tool_name": "echo", "args": {"text": "x"}}],
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
        include_plan_candidates=True,
    )
    assert len(out) == 1
    assert out[0]["kind"] == "plan"


def test_select_user_intent_candidates_any_mode_ignores_ambiguous_multiple_yaml_blocks():
    content = (
        "```yaml\n- operation: echo\n  arguments:\n    text: first\n```\n"
        "```yaml\n- operation: echo\n  arguments:\n    text: second\n```\n"
    )
    out = select_user_intent_candidates(
        content=content,
        plan=[{"tool_name": "echo", "args": {"text": "fallback"}}],
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position="any",
        include_plan_candidates=False,
    )
    assert len(out) == 1
    assert out[0]["value"][0]["args"]["text"] == "fallback"


def test_select_user_intent_candidates_any_mode_ignores_yaml_parse_errors():
    content = "```yaml\n- operation: echo\n  arguments:\n    text: ok\n```\n```yaml\n: bad: [\n```\n"
    out = select_user_intent_candidates(
        content=content,
        plan=None,
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position="any",
    )
    assert len(out) == 1
    assert out[0]["kind"] == "plan"


def test_select_user_intent_candidates_any_mode_plan_position_tolerates_yaml_parse_errors():
    content = "```yaml\n: bad: [\n```\n"
    out = select_user_intent_candidates(
        content=content,
        plan=[{"tool_name": "echo", "args": {"text": "fallback"}}],
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position="any",
        include_plan_candidates=False,
    )
    assert len(out) == 1
    assert out[0]["kind"] == "plan"


def test_select_user_intent_candidates_in_order_includes_multiple_shell_lines():
    content = "$ echo one\n/help\n$ echo two\n"
    out = select_user_intent_candidates(
        content=content,
        plan=None,
        operator_command=("help", []),
        shell_command="echo two",
        shell_argv=["echo", "two"],
        yaml_position="tail",
    )
    assert [item["kind"] for item in out] == ["shell", "operator", "shell"]
    assert out[0]["value"]["command"] == "echo one"
    assert out[2]["value"]["command"] == "echo two"


def test_select_user_intent_candidates_keeps_shell_after_inert_result():
    content = (
        "## RESULT\n\n"
        "[OK] python_script: exit=0\n"
        "```text toas-output kind=stdout source=tool.python_script potency=inert\n"
        "output\n"
        "```\n\n"
        "## TOAS:USER\n\n"
        "$ find . -name \"README.md\"\n"
    )

    out = select_user_intent_candidates(
        content=content,
        plan=None,
        operator_command=None,
        shell_command='find . -name "README.md"',
        shell_argv=["find", ".", "-name", "README.md"],
        yaml_position="tail",
    )

    assert [item["kind"] for item in out] == ["shell"]
    assert out[0]["value"]["command"] == 'find . -name "README.md"'
    assert out[0]["position"] == content.index("$ find")


def test_select_user_intent_candidates_ignores_quoted_yaml_block():
    content = (
        "> ```yaml\n"
        "> - operation: shell\n"
        ">   arguments:\n"
        ">     argv: [\"echo\", \"hi mom\"]\n"
        "> ```\n"
    )
    out = select_user_intent_candidates(
        content=content,
        plan=None,
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
    )
    assert out == []


def test_select_user_intent_candidates_interleaves_all_operator_commands_with_plans():
    content = (
        "/config set extraction.yaml_position any\n"
        "```yaml\n- operation: echo\n  arguments: {text: one}\n```\n"
        "/config show\n"
        "```yaml\n- operation: echo\n  arguments: {text: two}\n```"
    )
    out = select_user_intent_candidates(
        content=content,
        plan=None,
        operator_command=("config", ["show"]),
        operator_commands=[
            ("config", ["set", "extraction.yaml_position", "any"]),
            ("config", ["show"]),
        ],
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
    )

    assert [item["kind"] for item in out] == ["operator", "plan", "operator", "plan"]
    assert [item["value"][1] for item in out if item["kind"] == "operator"] == [
        ["set", "extraction.yaml_position", "any"],
        ["show"],
    ]


def test_select_user_intent_candidates_does_not_duplicate_prompted_bash_fence_as_shell():
    content = "```bash exec\n$ echo one\n$ echo two\n```"
    out = select_user_intent_candidates(
        content=content,
        plan=None,
        operator_command=None,
        shell_command="echo two",
        shell_argv=["echo", "two"],
        yaml_position="tail",
    )

    assert [item["kind"] for item in out] == ["plan"]
    assert out[0]["value"] == [{"tool_name": "shell_script", "args": {"script": "echo one\necho two"}}]


def test_select_user_intent_candidates_interleaves_yaml_and_json_plans():
    content = (
        "```json exec\n"
        '{"tool_name":"echo","args":{"text":"json"}}\n'
        "```\n"
        "```yaml\n"
        "- tool_name: echo\n"
        "  args: {text: yaml}\n"
        "```"
    )

    out = select_user_intent_candidates(
        content=content,
        plan=None,
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
    )

    assert [item["value"][0]["args"]["text"] for item in out] == ["json", "yaml"]


def test_select_user_intent_candidates_rejects_unknown_yaml_toolset():
    out = select_user_intent_candidates(
        content="```yaml exec toolset=other\n- tool_name: echo\n  args: {text: no}\n```",
        plan=None,
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
    )

    assert out[0]["kind"] == "unsupported_exec"
    assert out[0]["value"]["reason"] == "toolset is not registered"


def test_plan_candidates_skip_unsupported_yaml_activation(monkeypatch):
    monkeypatch.setattr(
        iae,
        "scan_markdown_fences",
        lambda _content: [SimpleNamespace(opening_offset=0)],
    )
    monkeypatch.setattr(
        iae,
        "classify_fence_activation",
        lambda _fence: SimpleNamespace(language="yaml", status="unsupported"),
    )

    assert iae._plan_candidates_from_content(
        "```yaml\n- tool_name: echo\n  args: {text: no}\n```"
    ) == []


def test_select_user_intent_candidates_captures_python_exec_language():
    out = select_user_intent_candidates(
        content='```python exec\nprint("Hi Mom!")\n```',
        plan=None,
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
    )

    assert out[0]["kind"] == "plan"
    assert out[0]["value"] == [{"tool_name": "python_script", "args": {"script": 'print("Hi Mom!")'}}]


def test_select_user_intent_candidates_captures_powershell_exec_language():
    out = select_user_intent_candidates(
        content='```powershell exec\nWrite-Output "Hi Mom!"\n```',
        plan=None,
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
    )

    assert out[0]["value"] == [{
        "tool_name": "powershell_script",
        "args": {"script": 'Write-Output "Hi Mom!"'},
    }]


def test_select_user_intent_candidates_captures_explicit_runtime_for_unknown_language():
    out = select_user_intent_candidates(
        content="```bc exec runtime=bc\n1 / 3\n```",
        plan=None,
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
    )

    assert out[0]["value"][0]["tool_name"] == "interpreter_script"


def test_shell_candidates_from_content_skips_incomplete_span():
    assert iae._shell_candidates_from_content('$ echo "one\ntwo\n') == []


def test_shell_candidates_from_content_skips_parse_failure(monkeypatch):
    monkeypatch.setattr(iae, "shell_argv_from_command", lambda _command: None)
    assert iae._shell_candidates_from_content("$ echo hi\n") == []


def test_select_user_intent_candidates_captures_write_fence_plan():
    content = "```python write path=src/example.py\nprint('hello world')\n```"
    out = select_user_intent_candidates(
        content=content,
        plan=None,
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
    )

    assert len(out) == 1
    assert out[0]["kind"] == "plan"
    assert out[0]["value"] == [
        {"tool_name": "write_file", "args": {"path": "src/example.py", "content": "print('hello world')\n"}}
    ]


def test_select_user_intent_candidates_captures_write_fence_with_yaml_block():
    content = (
        "```yaml\n- operation: echo\n  arguments:\n    text: preamble\n```\n"
        "```text write path=data.txt\nalpha\n```"
    )
    out = select_user_intent_candidates(
        content=content,
        plan=None,
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
    )

    assert len(out) == 2
    assert out[0]["kind"] == "plan"
    assert out[0]["value"][0]["tool_name"] == "echo"
    assert out[1]["kind"] == "plan"
    assert out[1]["value"][0]["tool_name"] == "write_file"


def test_select_user_intent_candidates_reports_unsupported_write_fence():
    content = "```python write\nprint('missing path')\n```"
    out = select_user_intent_candidates(
        content=content,
        plan=None,
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position="tail",
    )

    assert len(out) == 1
    assert out[0]["kind"] == "unsupported_exec"
    assert "write fence requires path attribute" in out[0]["value"]["reason"]


def test_intent_arbitration_edges_branch_coverage():
    # Line 31: empty content for _last_prefixed_line_position
    assert iae._last_prefixed_line_position("", prefix="/") is None

    # Line 59: yaml_position == "first"
    content_two = (
        "```yaml\n- operation: echo\n  arguments:\n    text: first\n```\n"
        "```yaml\n- operation: echo\n  arguments:\n    text: second\n```\n"
    )
    pos_first = iae._plan_position(content_two, plan=[{"tool_name": "echo", "args": {"text": "first"}}], yaml_position="first")
    assert pos_first == content_two.index("```yaml")

    # Line 71: yaml_position == "any" with one valid plan
    content_any = (
        "```yaml\ninvalid: structure\n```\n"
        "```yaml\n- operation: echo\n  arguments:\n    text: valid\n```\n"
    )
    pos_any = iae._plan_position(content_any, plan=[{"tool_name": "echo", "args": {"text": "valid"}}], yaml_position="any")
    assert pos_any == content_any.index("```yaml\n- operation: echo")

    # Line 84: raw plan without fences
    raw_plan_content = "- operation: echo\n  arguments:\n    text: raw\n"
    candidates = iae._plan_candidates_from_content(raw_plan_content)
    assert any(c[0][0]["tool_name"] == "echo" for c in candidates)

    # Line 113: yaml block with non-plan content skipped
    content_non_plan = (
        "```yaml\nfoo: bar\n```\n"
        "```yaml\n- operation: echo\n  arguments:\n    text: ok\n```\n"
    )
    candidates_non_plan = iae._plan_candidates_from_content(content_non_plan)
    assert len(candidates_non_plan) == 1
    assert candidates_non_plan[0][0][0]["tool_name"] == "echo"


