import pytest

from toas.cli_dispatch_ops import parse_ancestry_options, parse_prompt_options, parse_watch_options


def test_parse_watch_options():
    assert parse_watch_options(["watch", "r1", "--offset", "3", "--follow"]) == (3, True)
    with pytest.raises(SystemExit, match="--offset requires an integer"):
        parse_watch_options(["watch", "r1", "--offset", "x"])


def test_parse_prompt_options():
    assert parse_prompt_options(["prompt", "p/base", "--mode", "mimic", "--constraint", "a"]) == ("mimic", ["a"])
    with pytest.raises(SystemExit, match="unknown option: --bad"):
        parse_prompt_options(["prompt", "p/base", "--bad"])


def test_parse_ancestry_options():
    assert parse_ancestry_options(["ancestry", "n1", "--depth", "2", "--full"]) == (2, True)
    with pytest.raises(SystemExit, match="usage: toas ancestry <message_id>"):
        parse_ancestry_options(["ancestry", "n1", "--depth"])
