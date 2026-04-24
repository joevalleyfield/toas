
from toas.runtime import frontier_resolution as step_frontier


def test_render_loose_command_preview_plain_and_multiline():
    assert step_frontier.render_loose_command_preview("echo hi") == "$ echo hi"
    rendered = step_frontier.render_loose_command_preview("echo hi\necho bye")
    assert rendered.startswith("```sh\n")
    assert "echo hi" in rendered


def test_render_plan_as_yaml_preview():
    rendered = step_frontier.render_plan_as_yaml_preview([{"tool_name": "echo", "args": {"text": "hi"}}])
    assert rendered.startswith("```yaml\n")
    assert "tool_name: echo" in rendered


def test_render_plan_as_yaml_preview_compacts_shell_default_and_keeps_verbose_option():
    compact = step_frontier.render_plan_as_yaml_preview([{"tool_name": "shell", "args": {"argv": ["pwd"]}}])
    assert compact == "$ pwd"

    verbose = step_frontier.render_plan_preview(
        [{"tool_name": "shell", "args": {"argv": ["pwd"]}}],
        verbose=True,
    )
    assert verbose.startswith("```yaml\n")
    assert "tool_name: shell" in verbose


def test_render_plan_as_yaml_preview_preserves_multiline_shell_shape():
    rendered = step_frontier.render_plan_as_yaml_preview(
        [{"tool_name": "shell", "args": {"argv": ["sh", "-lc", "cat <<'EOF'\na\nEOF"]}}]
    )
    assert rendered == "cat <<'EOF'\na\nEOF"


def test_assistant_loose_command_projection_recovered_and_not():
    normal = step_frontier.assistant_loose_command_projection("echo hi", recovered=False)
    assert normal == {"role": "user", "content": "$ echo hi"}

    recovered = step_frontier.assistant_loose_command_projection("echo hi", recovered=True)
    assert recovered["role"] == "user"
    assert "[WARN] loose command YAML parse failed" in recovered["content"]


def test_extract_user_shell_argv():
    assert step_frontier.extract_user_shell_argv("echo hi") == ["echo", "hi"]


def test_extract_operator_command_variants():
    assert step_frontier.extract_operator_command("") is None
    assert step_frontier.extract_operator_command("hello") is None
    assert step_frontier.extract_operator_command("/  ") is None
    assert step_frontier.extract_operator_command("/x 'unterminated") is None
    assert step_frontier.extract_operator_command("first\n/config set x y") == ("config", ["set", "x", "y"])


def test_extract_frontier_assistant_candidates_command_and_cmd_paths():
    content = (
        "```yaml\ncommand: echo hi\n```\n"
        "```yaml\ncmd: echo bye\n```\n"
        "```yaml\ncommand: '   '\n```\n"
    )
    candidates, skipped = step_frontier.extract_frontier_assistant_candidates(content)
    assert len(candidates) == 2
    assert candidates[0]["kind"] == "assistant_loose_command"
    assert candidates[1]["kind"] == "assistant_loose_command"
    assert skipped == ["3. callable-looking YAML block did not match supported shapes"]


def test_extract_frontier_assistant_candidates_tool_plan_valid_and_invalid(monkeypatch):
    monkeypatch.setattr(step_frontier, "normalize_tool_plan", lambda parsed: ([{"tool_name": "echo", "args": {"text": "x"}}], None))

    candidates, skipped = step_frontier.extract_frontier_assistant_candidates("```yaml\n- tool_name: echo\n  args:\n    text: x\n```")
    assert candidates[0]["kind"] == "tool_plan"
    assert skipped == []

    monkeypatch.setattr(step_frontier, "validate_call", lambda item: (_ for _ in ()).throw(RuntimeError("bad item")))
    candidates, skipped = step_frontier.extract_frontier_assistant_candidates("```yaml\n- tool_name: echo\n  args:\n    text: x\n```")
    assert candidates == []
    assert skipped == ["1. invalid tool plan item: bad item"]


def test_extract_frontier_assistant_candidates_callable_shape_errors(monkeypatch):
    monkeypatch.setattr(step_frontier, "normalize_tool_plan", lambda parsed: (None, "conflicting callable keys: tool_name and operation"))
    candidates, skipped = step_frontier.extract_frontier_assistant_candidates("```yaml\ntool_name: echo\noperation: shell\n```")
    assert candidates == []
    assert skipped == ["1. invalid callable block: conflicting callable keys: tool_name and operation"]

    monkeypatch.setattr(step_frontier, "normalize_tool_plan", lambda parsed: (None, "not-supported"))
    candidates, skipped = step_frontier.extract_frontier_assistant_candidates("```yaml\noperation: unknown\n```")
    assert candidates == []
    assert skipped == ["1. callable-looking YAML block did not match supported shapes"]


def test_extract_frontier_assistant_candidates_yaml_error_includes_location_and_snippet():
    long = "operation: " + ("x" * 100)
    content = f"```yaml\n{long}\n: bad\n```"
    candidates, skipped = step_frontier.extract_frontier_assistant_candidates(content)
    assert candidates == []
    assert len(skipped) == 1
    assert skipped[0].startswith("1. yaml parse error")
    assert "near `operation:" in skipped[0]


def test_extract_frontier_assistant_candidates_non_callable_yaml_error_is_ignored():
    candidates, skipped = step_frontier.extract_frontier_assistant_candidates("```yaml\n: bad\n```")
    assert candidates == []
    assert skipped == []
