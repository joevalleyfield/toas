import pytest

from toas.shell_grants import (
    ShellGrantParser,
    ShellScriptCommandSegmenter,
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


def test_parse_and_normalize_shell_grants_cover_edge_branches():
    # parse_shell_grant empty text branch
    with pytest.raises(ValueError, match="empty grant"):
        normalize_shell_grants(("   ",))

    # invalid prefix/glob branches
    with pytest.raises(ValueError, match="invalid prefix grant"):
        normalize_shell_grants(("prefix:bad token",))
    with pytest.raises(ValueError, match="invalid glob grant"):
        normalize_shell_grants(("glob:   ",))

    # normalization skips non-string entries and de-dupes
    out = normalize_shell_grants(("echo", "echo", 123, "prefix:py"))  # type: ignore[arg-type]
    assert out == ("echo", "prefix:py")


def test_shell_command_allowed_exact_branch_and_script_empty_branches():
    grants = ("echo",)
    assert shell_command_allowed("echo", grants) is True
    assert shell_command_allowed("echox", grants) is False

    assert shell_script_segment_commands("   ") == []
    assert shell_script_segment_commands("# comment only") == []


def test_shell_grant_parser_functor_matches_existing_parse_behavior():
    parser = ShellGrantParser()
    grant = parser(" prefix:py ")
    assert grant.kind == "prefix"
    assert grant.raw == "prefix:py"


def test_shell_script_command_segmenter_functor_extracts_pipeline_leaders():
    segmenter = ShellScriptCommandSegmenter()
    assert segmenter("echo hi | head -1 && wc -c") == ["echo", "head", "wc"]
