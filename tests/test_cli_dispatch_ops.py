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


def test_parse_step_options_missing_values():
    from toas.cli_dispatch_ops import parse_step_options

    with pytest.raises(SystemExit, match="usage: toas step"):
        parse_step_options(["step", "--session"])
    with pytest.raises(SystemExit, match="usage: toas step"):
        parse_step_options(["step", "--surface"])
    with pytest.raises(SystemExit, match="unknown option"):
        parse_step_options(["step", "--bad"])


def test_parse_step_async_options_missing_values():
    from toas.cli_dispatch_ops import parse_step_async_options

    with pytest.raises(SystemExit, match="step"):
        parse_step_async_options(["step-async", "r1", "--session"])
    with pytest.raises(SystemExit, match="step"):
        parse_step_async_options(["step-async", "r1", "--surface"])
    with pytest.raises(SystemExit, match="unknown option"):
        parse_step_async_options(["step-async", "r1", "--bad"])


def test_parse_surface_options_errors():
    from toas.cli_dispatch_ops import parse_surface_options

    # too few args
    with pytest.raises(SystemExit, match="usage: toas surface"):
        parse_surface_options(["surface"])

    # bind too few args
    with pytest.raises(SystemExit, match="usage: toas surface bind"):
        parse_surface_options(["surface", "bind", "sid"])

    # bind bad arg count
    with pytest.raises(SystemExit, match="usage: toas surface bind"):
        parse_surface_options(["surface", "bind", "sid", "path", "extra"])

    # select too few args
    with pytest.raises(SystemExit, match="usage: toas surface select"):
        parse_surface_options(["surface", "select"])

    # rebind too few args
    with pytest.raises(SystemExit, match="usage: toas surface rebind"):
        parse_surface_options(["surface", "rebind"])

    # rebind unknown option
    with pytest.raises(SystemExit, match="usage: toas surface rebind"):
        parse_surface_options(["surface", "rebind", "sid", "--bad"])

    # rebind missing required
    with pytest.raises(SystemExit, match="usage: toas surface rebind"):
        parse_surface_options(["surface", "rebind", "sid", "--from-head", "h1", "--to-head", "h2"])

    # unknown surface command
    with pytest.raises(SystemExit, match="unknown surface command"):
        parse_surface_options(["surface", "unknown"])


def test_parse_graph_options_errors():
    from toas.cli_dispatch_ops import parse_graph_options

    # missing value
    with pytest.raises(SystemExit, match="usage: toas graph"):
        parse_graph_options(["graph", "--projection"])

    # unknown option
    with pytest.raises(SystemExit, match="unknown option"):
        parse_graph_options(["graph", "--bad"])

    # bad projection
    with pytest.raises(SystemExit, match="usage: toas graph"):
        parse_graph_options(["graph", "--projection", "bad"])
