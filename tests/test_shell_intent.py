from toas.shell_intent import (
    extract_loose_command,
    extract_user_structured_shell_command,
    extract_user_tail_shell_command,
    project_loose_command_for_user,
    shell_argv_from_command,
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
