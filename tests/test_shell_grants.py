import pytest

from toas.shell_grants import (
    normalize_shell_grants,
    shell_command_allowed,
    shell_script_segment_commands,
)


def test_normalize_shell_grants_supports_exact_prefix_and_glob():
    assert normalize_shell_grants(("echo", "prefix:py", "glob:git*")) == ("echo", "prefix:py", "glob:git*")


def test_shell_command_allowed_matches_prefix_and_glob():
    grants = ("prefix:py", "glob:git*")
    assert shell_command_allowed("python", grants) is True
    assert shell_command_allowed("git", grants) is True
    assert shell_command_allowed("gitk", grants) is True
    assert shell_command_allowed("rg", grants) is False


def test_shell_script_segment_commands_extracts_pipeline_leaders():
    assert shell_script_segment_commands("echo hi | head -1 && wc -c") == ["echo", "head", "wc"]


def test_normalize_shell_grants_rejects_invalid_entry():
    with pytest.raises(ValueError, match="invalid exact grant"):
        normalize_shell_grants(("bad grant",))
