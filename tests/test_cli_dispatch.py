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
        run_transcript=_rec("transcript"),
        run_llm_input=_rec("llm_input"),
        run_prompt=_rec("prompt"),
        run_prompts=_rec("prompts"),
        run_history=_rec("history"),
        run_rebuild=_rec("rebuild"),
        run_ancestry=_rec("ancestry"),
        run_diff=_rec("diff"),
        run_index_rebuild=_rec("index_rebuild"),
        run_daemon=_rec("daemon"),
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
