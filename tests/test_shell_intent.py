from toas.shell_intent import (
    _LOOSE_COMMAND_EXTRACTOR,
    extract_loose_command,
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

    assert extract_user_structured_shell_command("```yaml\ncommand: 123\n```") is None
    assert extract_user_structured_shell_command("```yaml\ncommand: |\n  echo one\n  echo two\n```") == "echo one\necho two"


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


def test_has_turn_header_inert_directive_first_non_empty_line_only():
    assert has_turn_header_inert_directive("!inert\n/help\n")
    assert has_turn_header_inert_directive("\n  !inert\n/help\n")
    assert not has_turn_header_inert_directive("hello\n!inert\n/help\n")
    assert not has_turn_header_inert_directive("!inert later\n/help\n")
