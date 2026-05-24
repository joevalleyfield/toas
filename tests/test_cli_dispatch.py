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
        run_jump=_rec("jump"),
        run_head=_rec("head"),
        run_heads=_rec("heads"),
        run_intents=_rec("intents"),
        run_transcript=_rec("transcript"),
        run_llm_input=_rec("llm_input"),
        run_prompt=_rec("prompt"),
        run_prompts=_rec("prompts"),
        run_history=_rec("history"),
        run_rebuild=_rec("rebuild"),
        run_session_path=_rec("session_path"),
        run_ancestry=_rec("ancestry"),
        run_diff=_rec("diff"),
        run_index_rebuild=_rec("index_rebuild"),
        run_daemon=_rec("daemon"),
        run_host=_rec("host"),
        run_replay_script=_rec("replay_script"),
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


def test_dispatch_step_parses_stdin_and_control():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main(["step", "--stdin", "--control", "/session show"], deps=_deps(calls))
    assert calls == [("step", (), {"stdin_mode": True, "control": "/session show", "session_path": None})]


def test_dispatch_step_parses_session_override():
    calls: list[tuple[str, tuple, dict]] = []
    dispatch_main(["step", "--session", ".toas/session-roadmap.md"], deps=_deps(calls))
    assert calls == [("step", (), {"stdin_mode": False, "control": None, "session_path": ".toas/session-roadmap.md"})]


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
    dispatch_main(["jump", "7"], deps=deps)
    dispatch_main(["head", "n1"], deps=deps)
    dispatch_main(["heads"], deps=deps)
    dispatch_main(["intents"], deps=deps)
    dispatch_main(["transcript"], deps=deps)
    dispatch_main(["llm-input", "n2"], deps=deps)
    dispatch_main(["prompts"], deps=deps)
    dispatch_main(["history"], deps=deps)
    dispatch_main(["rebuild", "h1"], deps=deps)
    dispatch_main(["session-path"], deps=deps)
    dispatch_main(["daemon"], deps=deps)
    dispatch_main(["host", "serve", "--owner-pid", "1"], deps=deps)
    assert calls == [
        ("cancel", ("r1",), {}),
        ("backend", ("status",), {}),
        ("jump", (7,), {}),
        ("head", ("n1",), {}),
        ("heads", (), {}),
        ("intents", (), {}),
        ("transcript", (None,), {}),
        ("llm_input", ("n2",), {}),
        ("prompts", (None,), {}),
        ("history", (10,), {}),
        ("rebuild", ("h1",), {}),
        ("session_path", (), {}),
        ("daemon", ("status",), {}),
        ("host", (["serve", "--owner-pid", "1"],), {}),
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
