import pytest

from toas.cli_dispatch_ops import (
    parse_ancestry_options,
    parse_history_options,
    parse_llm_input_options,
    parse_prompt_options,
    parse_transcript_options,
    parse_watch_options,
)


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


def test_parse_graph_options_accepts_sources_and_stitch_diagnostics():
    from toas.cli_dispatch_ops import parse_graph_options, parse_heads_options

    assert parse_heads_options(["heads"]) is None
    assert parse_heads_options(["heads", "--sources", "segments", "hot"]) == ["segments", "hot"]
    with pytest.raises(SystemExit, match="usage: toas heads"):
        parse_heads_options(["heads", "--sources"])

    assert parse_graph_options(["graph"]) == ("temporal", None, False, None, None, None)
    assert parse_graph_options(["graph", "--stitch-diagnostics"]) == (
        "temporal",
        None,
        True,
        None,
        None,
        None,
    )
    assert parse_graph_options(["graph", "--sources", "segments", "hot", "--stitch-diagnostics"]) == (
        "temporal",
        ["segments", "hot"],
        True,
        None,
        None,
        None,
    )
    assert parse_graph_options(["graph", "n42", "-3", "+2"]) == (
        "temporal",
        None,
        False,
        "n42",
        3,
        2,
    )
    assert parse_graph_options(["graph", "n2", "-0", "+0", "--sources", "segments", "hot"]) == (
        "temporal",
        ["segments", "hot"],
        False,
        "n2",
        0,
        0,
    )


def test_parse_history_options_accepts_limit_and_sources():
    assert parse_history_options(["history"]) == (10, None, None)
    assert parse_history_options(["history", "5"]) == (5, None, None)
    assert parse_history_options(["history", "hot:n2"]) == (10, None, "hot:n2")
    assert parse_history_options(["history", "--sources", "segments", "hot"]) == (10, ["segments", "hot"], None)
    assert parse_history_options(["history", "5", "--sources", "segments", "hot"]) == (5, ["segments", "hot"], None)
    assert parse_history_options(["history", "5", "hot:n2", "--sources", "segments", "hot"]) == (
        5,
        ["segments", "hot"],
        "hot:n2",
    )
    assert parse_history_options(["history", "5", "6"]) == (5, None, "6")


def test_parse_history_options_errors():
    with pytest.raises(SystemExit, match="usage: toas history"):
        parse_history_options(["history", "--sources"])
    with pytest.raises(SystemExit, match="usage: toas history"):
        parse_history_options(["history", "--sources", "--bad"])
    with pytest.raises(SystemExit, match="unknown option: --bad"):
        parse_history_options(["history", "--bad"])
    with pytest.raises(SystemExit, match="usage: toas history"):
        parse_history_options(["history", "bogus", "n2"])
    with pytest.raises(SystemExit, match="usage: toas history"):
        parse_history_options(["history", "5", "n2", "extra"])


def test_parse_transcript_and_llm_input_options_accept_anchor_sources_and_envelope():
    assert parse_transcript_options(["transcript"]) == (None, None)
    assert parse_transcript_options(["transcript", "hot:n2", "--sources", "segments", "hot"]) == (
        "hot:n2",
        ["segments", "hot"],
    )
    assert parse_llm_input_options(["llm-input"]) == (None, None, False)
    assert parse_llm_input_options(["llm-input", "--envelope"]) == (None, None, True)
    assert parse_llm_input_options(["llm-input", "hot:n2", "--sources", "segments", "hot", "--envelope"]) == (
        "hot:n2",
        ["segments", "hot"],
        True,
    )


def test_parse_transcript_and_llm_input_options_errors():
    with pytest.raises(SystemExit, match="usage: toas transcript"):
        parse_transcript_options(["transcript", "--sources"])
    with pytest.raises(SystemExit, match="unknown option: --envelope"):
        parse_transcript_options(["transcript", "--envelope"])
    with pytest.raises(SystemExit, match="usage: toas transcript"):
        parse_transcript_options(["transcript", "n1", "n2"])
    with pytest.raises(SystemExit, match="usage: toas llm-input"):
        parse_llm_input_options(["llm-input", "--sources", "--envelope"])
    with pytest.raises(SystemExit, match="unknown option: --bad"):
        parse_llm_input_options(["llm-input", "--bad"])


def test_parse_heads_options_errors():
    from toas.cli_dispatch_ops import parse_heads_options

    with pytest.raises(SystemExit, match="usage: toas heads"):
        parse_heads_options(["heads", "--sources", "--another"])
    with pytest.raises(SystemExit, match="unknown option"):
        parse_heads_options(["heads", "--bad-option"])


def test_parse_graph_options_more_errors():
    from toas.cli_dispatch_ops import parse_graph_options

    # --sources at the end of argv
    with pytest.raises(SystemExit, match="usage: toas graph"):
        parse_graph_options(["graph", "--sources"])

    # --sources with no following values (followed by another option)
    with pytest.raises(SystemExit, match="usage: toas graph"):
        parse_graph_options(["graph", "--sources", "--stitch-diagnostics"])

    # multiple anchor IDs
    with pytest.raises(SystemExit, match="usage: toas graph"):
        parse_graph_options(["graph", "n1", "n2"])

    # before/after without anchor ID
    with pytest.raises(SystemExit, match="usage: toas graph"):
        parse_graph_options(["graph", "-3"])
