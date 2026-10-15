import pytest

from toas.runtime import operator_command_parse as parser
from toas.runtime.frontier_resolution import extract_operator_command, extract_operator_commands
from toas.runtime.session_step_edges import extract_operator_command_tail


@pytest.mark.parametrize("command, expected", [
    (r"cd C:\work\target", ["cd", r"C:\work\target"]),
    ('cd "C:\\work space\\target\\"', ["cd", "C:\\work space\\target\\"]),
    (r"workspace add '\\server\share\work space'", ["workspace", "add", r"\\server\share\work space"]),
    (r"workspace remove C:\work\target", ["workspace", "remove", r"C:\work\target"]),
    (r"config load C:\work\policy.toml", ["config", "load", r"C:\work\policy.toml"]),
    (r"config save 'C:\work space\policy.toml'", ["config", "save", r"C:\work space\policy.toml"]),
    ("cd -", ["cd", "-"]),
    ("cd", ["cd"]),
    ("", []),
    (r"env set LABEL hello\ world", ["env", "set", "LABEL", "hello world"]),
])
def test_windows_control_tokens_preserve_paths(monkeypatch, command, expected):
    monkeypatch.setattr(parser, "_WINDOWS", True)
    assert parser.split_operator_command(command) == expected
    if expected:
        control = "/" + command
        pair = (expected[0], expected[1:])
        assert extract_operator_command(control) == pair
        assert extract_operator_commands(control) == [pair]
        assert extract_operator_command_tail(control) == pair


@pytest.mark.parametrize("windows", [False, True])
def test_control_quotes_and_posix_escapes(monkeypatch, windows):
    monkeypatch.setattr(parser, "_WINDOWS", windows)
    assert parser.split_operator_command('cd "/work space/target"') == ["cd", "/work space/target"]
    assert parser.split_operator_command(r"config set prompt.topic hello\ world")[-1] == "hello world"
    if not windows:
        assert parser.split_operator_command(r"cd /work\ space/target") == ["cd", "/work space/target"]
    with pytest.raises(ValueError, match="No closing quotation"):
        parser.split_operator_command("cd 'unterminated")
