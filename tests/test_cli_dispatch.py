from __future__ import annotations

import pytest

from toas.cli_dispatch import DispatchDeps, dispatch_main


def _deps(calls: list[tuple[str, tuple, dict]]):
    def _rec(name):
        return lambda *args, **kwargs: calls.append((name, args, kwargs))

    return DispatchDeps(
        run_help=_rec("help"),
        run_step=_rec("step"),
        run_step_async=_rec("step_async"),
        run_watch=_rec("watch"),
        run_cancel=_rec("cancel"),
        run_backend=_rec("backend"),
        run_heads=_rec("heads"),
        run_intents=_rec("intents"),
        run_graph=_rec("graph"),
        run_transcript=_rec("transcript"),
        run_llm_input=_rec("llm_input"),
        run_prompt=_rec("prompt"),
        run_prompts=_rec("prompts"),
        run_history=_rec("history"),
        run_session_path=_rec("session_path"),
        run_surface=_rec("surface"),
        run_ancestry=_rec("ancestry"),
        run_diff=_rec("diff"),
        run_index_rebuild=_rec("index_rebuild"),
        run_daemon=_rec("daemon"),
        run_host=_rec("host"),
        run_replay_script=_rec("replay_script"),
        run_debug_cancel_latency=_rec("debug_cancel_latency"),
    )


def test_dispatch_defaults_to_step():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main([], deps=_deps(calls))
    assert calls == [("step", (), {})]


def test_dispatch_watch_parses_flags():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main(["watch", "r1", "--offset", "5", "--follow"], deps=_deps(calls))
    assert calls == [("watch", ("r1",), {"offset": 5, "follow": True})]


def test_dispatch_prompt_parses_mode_and_constraints():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main(["prompt", "p/base", "--mode", "mimic", "--constraint", "a", "--constraint", "b"], deps=_deps(calls))
    assert calls == [("prompt", ("p/base",), {"mode": "mimic", "constraints": ["a", "b"]})]


def test_dispatch_ancestry_parses_depth_and_full():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main(["ancestry", "n1", "--depth", "3", "--full"], deps=_deps(calls))
    assert calls == [("ancestry", ("n1",), {"depth": 3, "full": True})]


def test_dispatch_unknown_command_raises():
    with pytest.raises(SystemExit, match="unknown command: nope"):
        dispatch_main(["nope"], deps=_deps([]))


def test_dispatch_help_and_step_async_and_step_unknown_option():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main(["help"], deps=_deps(calls))
    dispatch_main(["step", "--async"], deps=_deps(calls))
    assert calls == [("help", (), {}), ("step_async", (), {})]
    with pytest.raises(SystemExit, match="unknown option: --bad"):
        dispatch_main(["step", "--bad"], deps=_deps([]))


def test_dispatch_step_async_parses_session_override():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main(["step", "--async", "--session", ".toas/session-docs-keeper.md"], deps=_deps(calls))
    assert calls == [("step_async", (), {"session_path": ".toas/session-docs-keeper.md"})]


def test_dispatch_step_async_parses_surface_override():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main(["step", "--async", "--surface", "docs"], deps=_deps(calls))
    assert calls == [("step_async", (), {"surface_id": "docs"})]


def test_dispatch_step_parses_stdin_and_control():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main(["step", "--stdin", "--control", "/session show"], deps=_deps(calls))
    assert calls == [("step", (), {"stdin_mode": True, "control": "/session show", "session_path": None, "surface_id": None})]


def test_dispatch_step_parses_session_override():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main(["step", "--session", ".toas/session-roadmap.md"], deps=_deps(calls))
    assert calls == [("step", (), {"stdin_mode": False, "control": None, "session_path": ".toas/session-roadmap.md", "surface_id": None})]


def test_dispatch_step_parses_surface_override():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main(["step", "--surface", "docs"], deps=_deps(calls))
    assert calls == [("step", (), {"surface_id": "docs"})]


def test_dispatch_step_control_requires_value():
    with pytest.raises(SystemExit, match="usage: toas step \\[--stdin\\] \\[--control <slash_command>\\] \\[--session <transcript_path>\\]"):
        dispatch_main(["step", "--control"], deps=_deps([]))


def test_dispatch_watch_usage_and_validation_errors():
    with pytest.raises(SystemExit, match="usage: toas watch <run_id>"):
        dispatch_main(["watch"], deps=_deps([]))
    with pytest.raises(SystemExit, match="usage: toas watch <run_id>"):
        dispatch_main(["watch", "r1", "--offset"], deps=_deps([]))
    with pytest.raises(SystemExit, match="--offset requires an integer"):
        dispatch_main(["watch", "r1", "--offset", "x"], deps=_deps([]))
    with pytest.raises(SystemExit, match="unknown option: --bad"):
        dispatch_main(["watch", "r1", "--bad"], deps=_deps([]))


def test_dispatch_basic_commands_and_defaults():
    calls: list[tuple[str, tuple, dict]] = []
    deps = _deps(calls)
    dispatch_main(["cancel", "r1"], deps=deps)
    dispatch_main(["backend"], deps=deps)
    dispatch_main(["heads"], deps=deps)
    dispatch_main(["intents"], deps=deps)
    dispatch_main(["transcript"], deps=deps)
    dispatch_main(["llm-input", "n2"], deps=deps)
    dispatch_main(["prompts"], deps=deps)
    dispatch_main(["history"], deps=deps)
    dispatch_main(["session-path"], deps=deps)
    dispatch_main(["daemon"], deps=deps)
    dispatch_main(["surface", "list"], deps=deps)
    dispatch_main(["host", "serve", "--owner-pid", "1"], deps=deps)
    assert calls == [
        ("cancel", ("r1",), {}),
        ("backend", ("status",), {}),
        ("heads", (), {}),
        ("intents", (), {}),
        ("transcript", (None,), {}),
        ("llm_input", ("n2",), {"envelope": False}),
        ("prompts", (None,), {}),
        ("history", (10,), {}),
        ("session_path", (), {}),
        ("daemon", ("status",), {}),
        ("surface", ("list",), {}),
        ("host", (["serve", "--owner-pid", "1"],), {}),
    ]


def test_dispatch_llm_input_envelope_flag():
    calls: list[tuple[str, tuple, dict]] = []
    deps = _deps(calls)
    dispatch_main(["llm-input", "--envelope"], deps=deps)
    dispatch_main(["llm-input", "n2", "--envelope"], deps=deps)
    assert calls == [
        ("llm_input", (None,), {"envelope": True}),
        ("llm_input", ("n2",), {"envelope": True}),
    ]


def test_dispatch_heads_help_raises_usage():
    with pytest.raises(
        SystemExit,
        match="usage: toas heads[\\s\\S]*selected history graph leaf set[\\s\\S]*compact branch-tip view",
    ):
        dispatch_main(["heads", "--help"], deps=_deps([]))


def test_dispatch_heads_parses_sources():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main(["heads", "--sources", "segments", "hot"], deps=_deps(calls))
    assert calls == [("heads", (), {"source_tokens": ["segments", "hot"]})]


def test_dispatch_history_help_and_invalid_limit_raise_usage():
    with pytest.raises(
        SystemExit,
        match="usage: toas history \\[limit\\][\\s\\S]*show the current root-to-head lineage as a bounded readable window",
    ):
        dispatch_main(["history", "--help"], deps=_deps([]))
    with pytest.raises(
        SystemExit,
        match="usage: toas history \\[limit\\][\\s\\S]*show the current root-to-head lineage as a bounded readable window",
    ):
        dispatch_main(["history", "bogus"], deps=_deps([]))


def test_dispatch_graph_help_raises_usage():
    with pytest.raises(
        SystemExit,
        match="usage: toas graph \\[anchor\\] \\[-N\\] \\[\\+N\\] \\[--projection temporal\\|consequence\\][\\s\\S]*hot history by default",
    ):
        dispatch_main(["graph", "--help"], deps=_deps([]))


def test_dispatch_graph_parses_sources_and_stitch_diagnostics():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main(
        ["graph", "--sources", "segments", "hot", "--stitch-diagnostics"],
        deps=_deps(calls),
    )
    assert calls == [
        (
            "graph",
            ("temporal",),
            {"source_tokens": ["segments", "hot"], "stitch_diagnostics": True},
        )
    ]


def test_dispatch_graph_parses_local_neighborhood():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main(["graph", "n42", "-3", "+2"], deps=_deps(calls))
    assert calls == [
        (
            "graph",
            ("temporal",),
            {"anchor_id": "n42", "before": 3, "after": 2},
        )
    ]


def test_dispatch_debug_cancel_latency():
    calls: list[tuple[str, tuple, dict]] = []
    deps = _deps(calls)
    dispatch_main(["debug", "cancel-latency", ".toas/host-stream-debug.jsonl"], deps=deps)
    assert calls == [("debug_cancel_latency", (".toas/host-stream-debug.jsonl",), {})]


def test_dispatch_surface_bind_and_select_variants():
    calls: list[tuple[str, tuple, dict]] = []
    deps = _deps(calls)
    dispatch_main(["surface", "bind", "docs", ".toas/session-docs.md"], deps=deps)
    dispatch_main(["surface", "bind", "docs", ".toas/session-docs.md", "--reason", "seed"], deps=deps)
    dispatch_main(["surface", "select", "docs"], deps=deps)
    dispatch_main(
        ["surface", "rebind", "docs", "--from-head", "n1", "--to-head", "n9", "--reason", "manual repair"],
        deps=deps,
    )
    assert calls == [
        ("surface", ("bind", "docs", ".toas/session-docs.md"), {"reason": None}),
        ("surface", ("bind", "docs", ".toas/session-docs.md"), {"reason": "seed"}),
        ("surface", ("select", "docs"), {}),
        ("surface", ("rebind", "docs", "n1", "n9"), {"reason": "manual repair"}),
    ]


def test_dispatch_prompt_and_ancestry_usage_errors():
    with pytest.raises(SystemExit, match="usage: toas prompt <ref>"):
        dispatch_main(["prompt"], deps=_deps([]))
    with pytest.raises(SystemExit, match="usage: toas prompt <ref>"):
        dispatch_main(["prompt", "p/base", "--mode"], deps=_deps([]))
    with pytest.raises(SystemExit, match="usage: toas prompt <ref>"):
        dispatch_main(["prompt", "p/base", "--constraint"], deps=_deps([]))
    with pytest.raises(SystemExit, match="usage: toas ancestry <message_id>"):
        dispatch_main(["ancestry"], deps=_deps([]))
    with pytest.raises(SystemExit, match="usage: toas ancestry <message_id>"):
        dispatch_main(["ancestry", "n1", "--depth"], deps=_deps([]))
    with pytest.raises(SystemExit, match="--depth requires an integer"):
        dispatch_main(["ancestry", "n1", "--depth", "x"], deps=_deps([]))
    with pytest.raises(SystemExit, match="unknown option: --bad"):
        dispatch_main(["ancestry", "n1", "--bad"], deps=_deps([]))


def test_dispatch_diff_and_index_variants():
    calls: list[tuple[str, tuple, dict]] = []
    deps = _deps(calls)
    dispatch_main(["diff", "a", "b"], deps=deps)
    dispatch_main(["diff", "a", "b", "--full"], deps=deps)
    dispatch_main(["index"], deps=deps)
    assert calls == [
        ("diff", ("a", "b"), {"full": False}),
        ("diff", ("a", "b"), {"full": True}),
        ("index_rebuild", (), {}),
    ]
    with pytest.raises(SystemExit, match="usage: toas diff <head_a> <head_b>"):
        dispatch_main(["diff", "a"], deps=_deps([]))
    with pytest.raises(SystemExit, match="unknown index command: bad"):
        dispatch_main(["index", "bad"], deps=_deps([]))


def test_dispatch_replay_script_variants():
    calls: list[tuple[str, tuple, dict]] = []
    deps = _deps(calls)
    dispatch_main(["replay-script", "fixtures/replay.yaml"], deps=deps)
    dispatch_main(["replay-script", "fixtures/replay.yaml", "--output", "out.json", "--dry-run"], deps=deps)
    assert calls == [
        ("replay_script", ("fixtures/replay.yaml",), {"output_path": None, "dry_run": False}),
        ("replay_script", ("fixtures/replay.yaml",), {"output_path": "out.json", "dry_run": True}),
    ]
    with pytest.raises(SystemExit, match="usage: toas replay-script"):
        dispatch_main(["replay-script"], deps=_deps([]))
    with pytest.raises(SystemExit, match="usage: toas replay-script"):
        dispatch_main(["replay-script", "fixtures/replay.yaml", "--output"], deps=_deps([]))
    with pytest.raises(SystemExit, match="unknown option: --bad"):
        dispatch_main(["replay-script", "fixtures/replay.yaml", "--bad"], deps=_deps([]))


def test_dispatch_step_async_rejects_both_session_and_surface():
    with pytest.raises(SystemExit, match="step --async accepts only one"):
        dispatch_main(["step", "--async", "--session", "x.md", "--surface", "s1"], deps=_deps([]))


def test_dispatch_step_rejects_both_session_and_surface():
    with pytest.raises(SystemExit, match="step accepts only one"):
        dispatch_main(["step", "--session", "x.md", "--surface", "s1"], deps=_deps([]))


def test_dispatch_debug_unknown_subcommand():
    with pytest.raises(SystemExit, match="unknown debug command"):
        dispatch_main(["debug", "unknown", "path.jsonl"], deps=_deps([]))


def test_dispatch_surface_with_reason_non_bind(monkeypatch):
    calls = []
    deps = _deps(calls)
    # Force a reason to be returned for a non-bind/rebind subcommand to exercise line 122
    monkeypatch.setattr(
        "toas.cli_dispatch.parse_surface_options",
        lambda argv: ("select", ("s1",), "forced-reason"),
    )
    dispatch_main(["surface", "select", "s1"], deps=deps)
    assert calls == [("surface", ("select", "s1"), {"reason": "forced-reason"})]
