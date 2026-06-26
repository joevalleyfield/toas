from toas.shell_intent import (
    _LOOSE_COMMAND_EXTRACTOR,
    _match_heredoc,
    _scan_shell_line,
    _ShellScanState,
    extract_loose_command,
    extract_user_shell_command_spans,
    extract_user_structured_shell_command,
    extract_user_tail_shell_command,
    extract_yaml_tail,
    has_turn_header_inert_directive,
    project_loose_command_for_user,
    shell_argv_from_command,
    strip_inert_regions,
)


def test_extract_loose_command_single_line_yaml():
    content = "```yaml\ncommand: pwd\n```"
    command, recovered = extract_loose_command(content)
    assert command == "pwd"
    assert recovered is False


def test_extract_loose_command_multiline_yaml_preserves_shape():
    content = "```yaml\ncommand: |\n  echo one\n  echo two\n```"
    command, recovered = extract_loose_command(content)
    assert command == "echo one\necho two"
    assert recovered is False


def test_extract_loose_command_recovery_from_unparseable_yaml():
    content = "```yaml\ncommand: echo '{\"method\": \"status\", \"params\": {}}' | head -1\n```"
    command, recovered = extract_loose_command(content)
    assert command == "echo '{\"method\": \"status\", \"params\": {}}' | head -1"
    assert recovered is True


def test_project_loose_command_for_user_formats_single_line_and_multiline():
    assert project_loose_command_for_user("pwd") == "$ pwd"
    assert project_loose_command_for_user("echo one\necho two") == "echo one\necho two"


def test_extract_user_tail_shell_command_reads_only_trailing_dollar_line():
    assert extract_user_tail_shell_command("## TOAS:USER\n\n$ pwd\n") == "pwd"
    assert extract_user_tail_shell_command("## TOAS:USER\n\npwd\n") is None


def test_extract_user_tail_shell_command_preserves_multiline_quoted_payload():
    content = '## TOAS:USER\n\n$ jj commit -m"subject\n\n- bullet one\n- bullet two"\n'
    assert extract_user_tail_shell_command(content) == 'jj commit -m"subject\n\n- bullet one\n- bullet two"'


def test_extract_user_tail_shell_command_supports_backslash_continuation():
    content = "## TOAS:USER\n\n$ echo one \\\ntwo\n"
    assert extract_user_tail_shell_command(content) == "echo one \\\ntwo"


def test_extract_user_tail_shell_command_supports_heredoc_and_stops_before_prose():
    content = "## TOAS:USER\n\n$ cat <<'EOF'\none\ntwo\nEOF\nplain prose after command\n"
    assert extract_user_tail_shell_command(content) == "cat <<'EOF'\none\ntwo\nEOF"


def test_extract_user_tail_shell_command_preserves_incomplete_multiline_command_at_eof():
    content = '## TOAS:USER\n\n$ echo "one\ntwo\n'
    assert extract_user_tail_shell_command(content) == 'echo "one\ntwo'


def test_extract_user_structured_shell_command_supports_command_and_cmd():
    assert extract_user_structured_shell_command("```yaml\ncommand: pwd\n```") == "pwd"
    assert extract_user_structured_shell_command("```yaml\ncmd: pwd\n```") == "pwd"


def test_shell_argv_from_command_handles_invalid_shell_quoting():
    assert shell_argv_from_command("echo hi") == ["echo", "hi"]
    assert shell_argv_from_command("echo 'unterminated") is None


def test_extract_loose_command_handles_missing_yaml_and_cmd_recovery():
    command, recovered = extract_loose_command("plain text")
    assert command is None
    assert recovered is False

    content = "```yaml\ncmd: echo one | head -1\n```"
    command, recovered = extract_loose_command(content)
    assert command == "echo one | head -1"
    assert recovered is False

    malformed = "```yaml\ncmd: echo '{\"method\": \"status\"}' | head -1\n```"
    command, recovered = extract_loose_command(malformed)
    assert command == "echo '{\"method\": \"status\"}' | head -1"
    assert recovered is True

    malformed_with_blank = (
        "```yaml\n\ncmd: echo '{\"method\": \"status\", \"params\": {}}' | head -1\n```"
    )
    command, recovered = extract_loose_command(malformed_with_blank)
    assert command == "echo '{\"method\": \"status\", \"params\": {}}' | head -1"
    assert recovered is True


def test_extract_user_tail_and_structured_shell_command_edge_cases():
    assert extract_user_tail_shell_command("") is None
    assert extract_user_tail_shell_command("## TOAS:USER\n\n$   \n") is None
    assert extract_user_shell_command_spans("") == []

    assert extract_user_structured_shell_command("```yaml\ncommand: 123\n```") is None
    assert extract_user_structured_shell_command("```yaml\ncommand: |\n  echo one\n  echo two\n```") == "echo one\necho two"


def test_extract_user_tail_shell_command_does_not_start_from_non_prompt_continuation_line():
    content = "## TOAS:USER\n\nintro\ncontinued\n"
    assert extract_user_tail_shell_command(content) is None


def test_extract_user_shell_command_spans_skips_blank_prompt_and_tracks_positions():
    content = "intro\n$   \n$ echo one\n/help\n$ echo \"two\nthree\"\n"
    assert extract_user_shell_command_spans(content) == [
        ("echo one", True, len("intro\n$   \n")),
        ('echo "two\nthree"', True, len("intro\n$   \n$ echo one\n/help\n")),
    ]


def test_scan_shell_line_tracks_quote_escape_transitions():
    state = _scan_shell_line('"a\\"b"', _ShellScanState())
    assert state.quote is None
    assert state.escape is False

    state = _scan_shell_line("'ab'", _ShellScanState())
    assert state.quote is None

    state = _scan_shell_line("echo \\$HOME", _ShellScanState())
    assert state.quote is None


def test_scan_shell_line_ignores_non_heredoc_angle_brackets():
    state = _scan_shell_line("cat < file", _ShellScanState())
    assert state.heredoc is None

    state = _scan_shell_line("cat <<$", _ShellScanState())
    assert state.heredoc is None


def test_match_heredoc_covers_tab_strip_spaces_and_invalid_shapes():
    heredoc, next_index = _match_heredoc("cat <<-  EOF", 4)
    assert heredoc is not None
    assert heredoc.delimiter == "EOF"
    assert heredoc.strip_tabs is True
    assert next_index == len("cat <<-  EOF")

    heredoc, next_index = _match_heredoc("cat <<   ", 4)
    assert heredoc is None
    assert next_index == len("cat <<   ")

    heredoc, next_index = _match_heredoc("cat <<'EOF", 4)
    assert heredoc is None
    assert next_index == len("cat <<'EOF")

    heredoc, next_index = _match_heredoc("cat <<$", 4)
    assert heredoc is None
    assert next_index == len("cat <<") + 1

    heredoc, next_index = _match_heredoc("cat <<EOF", 4)
    assert heredoc is not None
    assert heredoc.delimiter == "EOF"
    assert heredoc.strip_tabs is False
    assert next_index == len("cat <<EOF")


def test_extract_loose_command_non_dict_paths_and_missing_command_keys():
    # Non-dict parsed YAML with a leading blank line exercises blank-line skip and no-command fallback.
    command, recovered = extract_loose_command("```yaml\n\n- item\n```")
    assert command is None
    assert recovered is False

    # Parsed dict with non-string command/cmd values returns no command.
    command, recovered = extract_loose_command("```yaml\ncommand: 123\ncmd: 456\n```")
    assert command is None
    assert recovered is False

    # Structured extractor returns None when parsed tail is not a dict.
    assert extract_user_structured_shell_command("```yaml\n- item\n```") is None


def test_extract_loose_command_recovery_skips_blank_lines_and_extract_yaml_tail_none():
    # Direct helper call guarantees leading-blank recovery path coverage.
    assert _LOOSE_COMMAND_EXTRACTOR._recover_from_text("\ncmd: pwd") == "pwd"

    # Tail extractor no-block path.
    assert extract_yaml_tail("no yaml block here") is None


def test_strip_inert_regions_and_extractors_ignore_inert_content():
    content = (
        "[[inert]]\n"
        "$ pwd\n"
        "```yaml\ncommand: echo hidden\n```\n"
        "[[/inert]]\n"
        "$ echo visible\n"
    )
    stripped = strip_inert_regions(content)
    assert "$ pwd" not in stripped
    assert "hidden" not in stripped
    assert "$ echo visible" in stripped
    assert extract_user_tail_shell_command(content) == "echo visible"


def test_strip_inert_regions_supports_markdown_inert_fence():
    content = (
        "```inert\n"
        "/help\n"
        "$ pwd\n"
        "```yaml\ncommand: echo hidden\n```\n"
        "```\n"
        "$ echo visible\n"
    )
    stripped = strip_inert_regions(content)
    assert "/help" not in stripped
    assert "$ pwd" not in stripped
    assert "hidden" not in stripped
    assert "$ echo visible" in stripped
    assert extract_user_tail_shell_command(content) == "echo visible"


def test_strip_inert_regions_supports_nested_same_tick_fence_inside_inert_fence():
    content = (
        "```inert\n"
        "/help\n"
        "```yaml\n"
        "- operation: echo\n"
        "```\n"
        "$ pwd\n"
        "```\n"
        "$ echo visible\n"
    )
    stripped = strip_inert_regions(content)
    assert "/help" not in stripped
    assert "- operation: echo" not in stripped
    assert "$ pwd" not in stripped
    assert "$ echo visible" in stripped
    assert extract_user_tail_shell_command(content) == "echo visible"


def test_strip_inert_regions_supports_inert_alias_info_string():
    content = (
        "```text (inert response)\n"
        "/help\n"
        "$ pwd\n"
        "```\n"
        "$ echo visible\n"
    )
    stripped = strip_inert_regions(content)
    assert "/help" not in stripped
    assert "$ pwd" not in stripped
    assert "$ echo visible" in stripped
    assert extract_user_tail_shell_command(content) == "echo visible"


def test_has_turn_header_inert_directive_first_non_empty_line_only():
    assert has_turn_header_inert_directive("!inert\n/help\n")
    assert has_turn_header_inert_directive("\n  !inert\n/help\n")
    assert not has_turn_header_inert_directive("hello\n!inert\n/help\n")
    assert not has_turn_header_inert_directive("!inert later\n/help\n")
    assert not has_turn_header_inert_directive("")


def test_strip_inert_regions_supports_toas_output_and_potency_active():
    # 1. toas-output block is stripped by default
    content1 = (
        "```text toas-output kind=stdout source=tool.shell\n"
        "$ pwd\n"
        "```\n"
        "$ echo visible\n"
    )
    assert "$ pwd" not in strip_inert_regions(content1)
    assert "$ echo visible" in strip_inert_regions(content1)

    # 2. toas-output with potency=active is NOT stripped
    content2 = (
        "```text toas-output kind=stdout source=tool.shell potency=active\n"
        "$ pwd\n"
        "```\n"
    )
    assert "$ pwd" in strip_inert_regions(content2)

    # 3. Nested code fences with different backticks length inside an inert fence
    content3 = (
        "````text toas-output kind=stdout source=tool.shell\n"
        "```python\n"
        "print('hello')\n"
        "```\n"
        "````\n"
        "$ echo visible\n"
    )
    stripped3 = strip_inert_regions(content3)
    assert "print('hello')" not in stripped3
    assert "$ echo visible" in stripped3
