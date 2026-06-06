
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

    forced_yaml = step_frontier.render_plan_preview(
        [{"tool_name": "shell", "args": {"argv": ["pwd"]}}],
        projection_shape="yaml",
    )
    assert forced_yaml.startswith("```yaml\n")

    forced_shell = step_frontier.render_plan_preview(
        [{"tool_name": "shell", "args": {"argv": ["pwd"]}}],
        projection_shape="shell",
    )
    assert forced_shell == "$ pwd"


def test_render_plan_as_yaml_preview_preserves_multiline_shell_shape():
    rendered = step_frontier.render_plan_as_yaml_preview(
        [{"tool_name": "shell", "args": {"argv": ["sh", "-lc", "cat <<'EOF'\na\nEOF"]}}]
    )
    assert rendered == "cat <<'EOF'\na\nEOF"


def test_render_plan_as_yaml_preview_compacts_multi_shell_plan():
    rendered = step_frontier.render_plan_as_yaml_preview(
        [
            {"tool_name": "shell", "args": {"argv": ["pwd"]}},
            {"tool_name": "shell_script", "args": {"script": "printf 'x\\n' | wc -l"}},
        ]
    )
    assert rendered == "$ pwd\n$ printf 'x\\n' | wc -l"


def test_render_compact_plan_preview_rejects_non_dict_and_bad_args():
    assert step_frontier.render_compact_plan_preview([None]) is None
    assert step_frontier.render_compact_plan_preview([{"tool_name": "shell", "args": None}]) is None
    assert step_frontier.render_compact_plan_preview([]) is None
    assert step_frontier.render_compact_plan_preview([{"tool_name": "shell", "args": {"argv": ["", "x"]}}]) is None


def test_render_plan_as_yaml_preview_keeps_yaml_for_mixed_tool_plan():
    rendered = step_frontier.render_plan_as_yaml_preview(
        [
            {"tool_name": "shell", "args": {"argv": ["pwd"]}},
            {"tool_name": "echo", "args": {"text": "hi"}},
        ]
    )
    assert rendered.startswith("```yaml\n")
    assert "tool_name: echo" in rendered

    forced_shell = step_frontier.render_plan_preview(
        [
            {"tool_name": "shell", "args": {"argv": ["pwd"]}},
            {"tool_name": "echo", "args": {"text": "hi"}},
        ],
        projection_shape="shell",
    )
    assert forced_shell.startswith("```yaml\n")


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
    assert step_frontier.extract_operator_command("first\n  /config set x y") is None
    assert step_frontier.extract_operator_command("first\nnote: /config set x y") is None
    assert step_frontier.extract_operator_command("first\n/config set x y") == ("config", ["set", "x", "y"])


def test_extract_operator_commands_collects_all_slash_lines_in_order():
    content = "/help\n/config set extraction.intent_arbitration in_order\nnote\n/config values extraction.intent_arbitration"
    assert step_frontier.extract_operator_commands(content) == [
        ("help", []),
        ("config", ["set", "extraction.intent_arbitration", "in_order"]),
        ("config", ["values", "extraction.intent_arbitration"]),
    ]


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


def test_extract_frontier_assistant_candidates_compact_tool_plan_exposes_verbose_variants(monkeypatch):
    monkeypatch.setattr(
        step_frontier,
        "normalize_tool_plan",
        lambda parsed: (
            [
                {"tool_name": "shell", "args": {"argv": ["pwd"]}},
                {"tool_name": "shell_script", "args": {"script": "echo hi"}},
            ],
            None,
        ),
    )

    candidates, skipped = step_frontier.extract_frontier_assistant_candidates("```yaml\n- tool_name: shell\n```")
    assert skipped == []
    assert candidates[0]["preview"] == "$ pwd\n$ echo hi"
    assert candidates[0]["adopt"] == "$ pwd\n$ echo hi"
    assert candidates[0]["preview_verbose"].startswith("```yaml\n")
    assert candidates[0]["adopt_verbose"].startswith("```yaml\n")

    candidates_yaml, _ = step_frontier.extract_frontier_assistant_candidates(
        "```yaml\n- tool_name: shell\n```",
        projection_shape="yaml",
    )
    assert candidates_yaml[0]["preview"].startswith("```yaml\n")


def test_extract_frontier_assistant_candidates_callable_shape_errors(monkeypatch):
    monkeypatch.setattr(step_frontier, "normalize_tool_plan", lambda parsed: (None, "conflicting callable keys: tool_name and operation"))
    candidates, skipped = step_frontier.extract_frontier_assistant_candidates("```yaml\ntool_name: echo\noperation: shell\n```")
    assert candidates == []
    assert skipped == ["1. invalid callable block: conflicting callable keys: tool_name and operation"]

    monkeypatch.setattr(step_frontier, "normalize_tool_plan", lambda parsed: (None, "not-supported"))
    candidates, skipped = step_frontier.extract_frontier_assistant_candidates("```yaml\noperation: unknown\n```")
    assert candidates == []
    assert skipped == ["1. callable-looking YAML block did not match supported shapes"]


def test_extract_operator_commands_skips_bad_shlex_lines():
    content = "/help\n/x 'unterminated\n/config show"
    assert step_frontier.extract_operator_commands(content) == [("help", []), ("config", ["show"])]


def test_extract_operator_commands_skips_empty_argv_line():
    assert step_frontier.extract_operator_commands("/   \n/help") == [("help", [])]


def test_select_user_intent_candidates_any_yaml_parse_error_path():
    from toas.runtime.intent_arbitration_edges import select_user_intent_candidates

    out = select_user_intent_candidates(
        content="```yaml\n: bad\n```\n```yaml\n- operation: echo\n  arguments:\n    text: ok\n```",
        plan=None,
        operator_command=None,
        shell_command=None,
        shell_argv=None,
        yaml_position="any",
        arbitration_mode="in_order",
    )
    assert len(out) == 1
    assert out[0]["kind"] == "plan"


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


def test_extract_frontier_assistant_candidates_near_miss_argv_hint():
    content = "```yaml\noperation: echo\nargv: [echo, hello]\n  extra: :bad\n```"
    candidates, skipped = step_frontier.extract_frontier_assistant_candidates(content)
    assert candidates == []
    assert len(skipped) == 1
    assert "hint: use block list style for argv" in skipped[0]
