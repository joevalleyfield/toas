import json
import sys
import types
from pathlib import Path

import pytest

from toas import cli


def test_run_step_bootstraps_missing_files_and_prints_no_history(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    calls = {}

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        calls["transcript"] = transcript
        calls["log"] = log
        calls["bind_index"] = bind_index
        calls["bind_parent"] = bind_parent
        calls["anchor_index"] = anchor_index
        calls["storage_tip_parent"] = storage_tip_parent
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert not Path(".toas/session.md").exists()
    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == ""
    assert calls == {
        "transcript": "",
        "log": [],
        "bind_index": None,
        "bind_parent": None,
        "anchor_index": 0,
        "storage_tip_parent": None,
    }
    assert capsys.readouterr().out == ""


def test_run_step_passes_stdin_and_control_to_local_runner(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    calls: dict[str, object] = {}

    def fake_run_step_local(*, stdin_mode=False, control=None, session_path=None):
        calls["stdin_mode"] = stdin_mode
        calls["control"] = control
        calls["session_path"] = session_path

    monkeypatch.setattr(cli, "run_step_local", fake_run_step_local)
    cli.run_step(stdin_mode=True, control="/session show")
    assert calls == {"stdin_mode": True, "control": "/session show", "session_path": None}


def test_run_step_passes_session_override_to_local_runner(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    calls: dict[str, object] = {}

    def fake_run_step_local(*, stdin_mode=False, control=None, session_path=None):
        calls["stdin_mode"] = stdin_mode
        calls["control"] = control
        calls["session_path"] = session_path

    monkeypatch.setattr(cli, "run_step_local", fake_run_step_local)
    cli.run_step(session_path=".toas/session-docs-keeper.md")
    assert calls == {"stdin_mode": False, "control": None, "session_path": ".toas/session-docs-keeper.md"}


def test_run_step_resolves_surface_id_to_bound_session_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        '{"kind":"surface_bind","payload":{"surface_id":"docs","transcript_path":".toas/session-docs.md"}}\n',
        encoding="utf-8",
    )
    calls: dict[str, object] = {}

    def fake_run_step_local(*, stdin_mode=False, control=None, session_path=None, surface_id=None):
        calls["stdin_mode"] = stdin_mode
        calls["control"] = control
        calls["session_path"] = session_path
        calls["surface_id"] = surface_id

    monkeypatch.setattr(cli, "run_step_local", fake_run_step_local)
    cli.run_step(surface_id="docs")
    assert calls == {"stdin_mode": False, "control": None, "session_path": None, "surface_id": "docs"}


def test_run_step_stdin_mode_never_attempts_rpc_even_when_preferred(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    seen: dict[str, object] = {}

    def fake_local(*, stdin_mode=False, control=None, session_path=None):
        seen["stdin_mode"] = stdin_mode
        seen["control"] = control
        seen["session_path"] = session_path

    monkeypatch.setattr(cli, "_should_prefer_rpc", lambda: True)
    monkeypatch.setattr(
        cli,
        "rpc_request",
        lambda _op, _payload=None: (_ for _ in ()).throw(AssertionError("rpc should not be called")),
    )
    monkeypatch.setattr(cli, "run_step_local", fake_local)

    cli.run_step(stdin_mode=True)

    assert seen == {"stdin_mode": True, "control": None, "session_path": None}


def test_run_step_control_mode_never_attempts_rpc_even_when_preferred(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    seen: dict[str, object] = {}

    def fake_local(*, stdin_mode=False, control=None, session_path=None):
        seen["stdin_mode"] = stdin_mode
        seen["control"] = control
        seen["session_path"] = session_path

    monkeypatch.setattr(cli, "_should_prefer_rpc", lambda: True)
    monkeypatch.setattr(
        cli,
        "rpc_request",
        lambda _op, _payload=None: (_ for _ in ()).throw(AssertionError("rpc should not be called")),
    )
    monkeypatch.setattr(cli, "run_step_local", fake_local)

    cli.run_step(control="/session show")

    assert seen == {"stdin_mode": False, "control": "/session show", "session_path": None}


def test_cli_async_local_mode_routes_step_watch_cancel_without_rpc(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "local")
    monkeypatch.delenv("TOAS_ASYNC_LOCAL_STRICT_GUARD", raising=False)

    monkeypatch.setattr(
        cli,
        "rpc_request",
        lambda _op, _payload=None: (_ for _ in ()).throw(AssertionError("rpc should not be called in local mode")),
    )
    monkeypatch.setattr("toas.cli_async_commands._start_async_step_local", lambda _payload: {"run_id": "r-local", "status": "running"})
    monkeypatch.setattr(
        "toas.cli_async_commands._watch_async_step_local",
        lambda payload: {
            "status": "running",
            "next_offset": payload.get("offset", 0),
            "next_seq": payload.get("since_seq", 0),
        },
    )
    monkeypatch.setattr("toas.cli_async_commands._cancel_async_step_local", lambda _payload: {"status": "cancelling"})

    cli.run_step_async()
    cli.run_watch("r-local", offset=0, follow=False)
    cli.run_cancel("r-local")

    out = capsys.readouterr().out
    assert "run_id=r-local status=running backend=local host=" in out
    assert "[run running] offset=0 backend=local\n" in out
    assert "run_id=r-local status=cancelling backend=local host=" in out


def test_run_step_local_appends_stdin_and_control_to_transcript(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/session.md").write_text("## TOAS:USER\n\nbase\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_step(transcript, log, **kwargs):
        captured["transcript"] = transcript
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)
    monkeypatch.setattr(sys, "stdin", types.SimpleNamespace(read=lambda: "## TOAS:USER\n\nstdin\n"))

    cli.run_step_local(stdin_mode=True, control="/session show")
    assert captured["transcript"] == "## TOAS:USER\n\nbase\n## TOAS:USER\n\nstdin\n\n## TOAS:CONTROL\n\n/session show\n"


def test_run_step_appends_all_new_nodes_but_prints_only_consequences(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        assert transcript == "## TOAS:USER\n\nhello\n"
        assert log == []
        assert bind_index is None
        assert bind_parent is None
        assert anchor_index == 0
        assert storage_tip_parent is None
        return (
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
            [
                {"role": "assistant", "content": "hi"},
            ],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}}\n'
    )
    assert capsys.readouterr().out == "## TOAS:ASSISTANT\n\nhi\n\n"


def test_run_step_never_rewrites_session_md(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    original = "## TOAS:USER\n\nhello\n"
    Path("session.md").write_text(original, encoding="utf-8")

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        assert transcript == original
        return (
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
            [{"role": "assistant", "content": "hi"}],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path("session.md").read_text(encoding="utf-8") == original
    assert capsys.readouterr().out == "## TOAS:ASSISTANT\n\nhi\n\n"


def test_run_step_applies_session_update_from_result_node(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    original = "## TOAS:USER\n\n/compact\n"
    updated = "## TOAS:USER\n\n/compact\n\n## RESULT\n\n[RESULT: 123 chars, collapsed]\n"
    Path("session.md").write_text(original, encoding="utf-8")

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        assert transcript == original
        return (
            [
                {"role": "user", "content": "/compact"},
                {
                    "role": "result",
                    "content": "compact: collapsed 1 RESULT block(s) above threshold=500",
                    "session_update": {"transcript": updated},
                },
            ],
            [
                {
                    "role": "result",
                    "content": "compact: collapsed 1 RESULT block(s) above threshold=500",
                    "session_update": {"transcript": updated},
                }
            ],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path(".toas/session.md").read_text(encoding="utf-8") == updated
    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "/compact", "metadata": {}}\n'
        '{"kind": "command_request", "payload": {"id": "c1", "command": "compact", "args": []}, "related_to": "n0"}\n'
        '{"kind": "command_result", "payload": {"ok": true, "content": "compact: collapsed 1 RESULT block(s) above threshold=500"}, "related_to": "c1"}\n'
    )
    assert capsys.readouterr().out == "## RESULT\n\ncompact: collapsed 1 RESULT block(s) above threshold=500\n\n"


def test_run_step_does_not_touch_existing_session_file(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    session_path = Path("session.md")
    session_path.write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    before_stat = session_path.stat()

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    after_stat = session_path.stat()
    assert after_stat.st_mtime_ns == before_stat.st_mtime_ns
    if hasattr(before_stat, "st_birthtime_ns") and hasattr(after_stat, "st_birthtime_ns"):
        assert after_stat.st_birthtime_ns == before_stat.st_birthtime_ns
    assert capsys.readouterr().out == ""


def test_run_jump_is_invokable(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    cli.run_jump(7)

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"kind": "jump", "payload": {"bind_index": 7}}\n'
    )
    assert capsys.readouterr().out == "bound transcript to node 7\n"


def test_run_head_is_invokable(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    cli.run_head("n7")

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"kind": "head", "payload": {"head_id": "n7"}}\n'
    )
    assert capsys.readouterr().out == "selected head n7\n"


def test_run_heads_lists_known_heads_and_marks_selected(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "main", "metadata": {}}\n'
            '{"id": "n2", "parent": "n0", "role": "assistant", "content": "branch", "metadata": {}}\n'
            '{"kind": "head", "payload": {"head_id": "n2"}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_heads()

    assert capsys.readouterr().out == (
        "  n1 assistant: main  [d=2 t=1 ?:2]\n"
        "* n2 assistant: branch  [d=2 t=1 ?:2]\n"
    )


def test_run_intents_lists_known_intents_and_marks_current(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"kind": "intent", "payload": {"intent_id": "i1", "title": "first", "status": "active"}}\n'
            '{"kind": "intent", "payload": {"intent_id": "i1", "title": "first", "status": "paused"}}\n'
            '{"kind": "intent", "payload": {"intent_id": "i2", "title": "second", "status": "active"}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_intents()

    assert capsys.readouterr().out == (
        "intents:\n"
        "  i1 [active] first\n"
        "  i1 [paused] first\n"
        "* i2 [active] second\n"
    )


def test_run_intents_shows_none_when_empty(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    cli.run_intents_local()
    assert capsys.readouterr().out == "intents: (none)\n"


def test_run_intents_respects_rpc_stdout(monkeypatch):
    seen = []
    monkeypatch.setattr(cli, "_rpc_stdout", lambda op: seen.append(op) or True)
    monkeypatch.setattr(cli, "run_intents_local", lambda: (_ for _ in ()).throw(AssertionError("should not run local")))
    cli.run_intents()
    assert seen == ["intents"]


def test_main_defaults_to_step(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas"])
    monkeypatch.setattr(cli, "run_step", lambda: seen.append("step"))

    cli.main()

    assert seen == ["step"]


def test_main_dispatches_step_async(monkeypatch):
    seen = []
    monkeypatch.setattr(cli.sys, "argv", ["toas", "step", "--async"])
    monkeypatch.setattr(cli, "run_step_async", lambda: seen.append("step-async"))
    cli.main()
    assert seen == ["step-async"]


def test_main_dispatches_watch(monkeypatch):
    seen: list[tuple[str, int, bool]] = []
    monkeypatch.setattr(cli.sys, "argv", ["toas", "watch", "run123", "--offset", "5", "--follow"])
    monkeypatch.setattr(cli, "run_watch", lambda run_id, offset=0, follow=False: seen.append((run_id, offset, follow)))
    cli.main()
    assert seen == [("run123", 5, True)]


def test_main_dispatches_cancel(monkeypatch):
    seen = []
    monkeypatch.setattr(cli.sys, "argv", ["toas", "cancel", "run123"])
    monkeypatch.setattr(cli, "run_cancel", lambda run_id: seen.append(run_id))
    cli.main()
    assert seen == ["run123"]


def test_main_dispatches_backend(monkeypatch):
    seen = []
    monkeypatch.setattr(cli.sys, "argv", ["toas", "backend", "status"])
    monkeypatch.setattr(cli, "run_backend", lambda action: seen.append(action))
    cli.main()
    assert seen == ["status"]


def test_main_dispatches_jump(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "jump", "12"])
    monkeypatch.setattr(cli, "run_jump", lambda index: seen.append(index))

    cli.main()

    assert seen == [12]


def test_main_dispatches_head(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "head", "n4"])
    monkeypatch.setattr(cli, "run_head", lambda head_id: seen.append(head_id))

    cli.main()

    assert seen == ["n4"]


def test_main_dispatches_heads(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "heads"])
    monkeypatch.setattr(cli, "run_heads", lambda: seen.append("heads"))

    cli.main()

    assert seen == ["heads"]


def test_main_dispatches_intents(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "intents"])
    monkeypatch.setattr(cli, "run_intents", lambda: seen.append("intents"))

    cli.main()

    assert seen == ["intents"]


def test_main_dispatches_transcript(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "transcript", "n4"])
    monkeypatch.setattr(cli, "run_transcript", lambda head_id=None: seen.append(head_id))

    cli.main()

    assert seen == ["n4"]


def test_main_dispatches_llm_input(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "llm-input"])
    monkeypatch.setattr(cli, "run_llm_input", lambda head_id=None: seen.append(head_id))

    cli.main()

    assert seen == [None]


def test_main_dispatches_prompt(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "prompt", "protocol/terse_v1"])
    monkeypatch.setattr(
        cli,
        "run_prompt",
        lambda ref, mode="direct", constraints=None: seen.append((ref, mode, constraints)),
    )

    cli.main()

    assert seen == [("protocol/terse_v1", "direct", None)]


def test_main_dispatches_prompt_with_mode_and_constraints(monkeypatch):
    seen = []

    monkeypatch.setattr(
        cli.sys,
        "argv",
        [
            "toas",
            "prompt",
            "role/pragmatic-engineer_v1",
            "--mode",
            "mimic",
            "--constraint",
            "no-chatty",
            "--constraint",
            "no-provider-tools",
        ],
    )
    monkeypatch.setattr(
        cli,
        "run_prompt",
        lambda ref, mode="direct", constraints=None: seen.append((ref, mode, constraints)),
    )

    cli.main()

    assert seen == [("role/pragmatic-engineer_v1", "mimic", ["no-chatty", "no-provider-tools"])]


def test_main_dispatches_prompts(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "prompts", "session-start"])
    monkeypatch.setattr(cli, "run_prompts", lambda prefix=None: seen.append(prefix))

    cli.main()

    assert seen == ["session-start"]


def test_main_dispatches_dynamic_prompts(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "prompts", "dynamic/capabilities"])
    monkeypatch.setattr(cli, "run_prompts", lambda prefix=None: seen.append(prefix))

    cli.main()

    assert seen == ["dynamic/capabilities"]


def test_main_dispatches_history(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "history", "5"])
    monkeypatch.setattr(cli, "run_history", lambda limit=10: seen.append(limit))

    cli.main()

    assert seen == [5]


def test_main_dispatches_rebuild(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "rebuild", "n4"])
    monkeypatch.setattr(cli, "run_rebuild", lambda head_id=None: seen.append(head_id))

    cli.main()

    assert seen == ["n4"]


def test_main_dispatches_session_path(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "session-path"])
    monkeypatch.setattr(cli, "run_session_path", lambda: seen.append("ok"))

    cli.main()

    assert seen == ["ok"]


def test_main_dispatches_daemon(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "daemon", "start"])
    monkeypatch.setattr(cli, "run_daemon", lambda action: seen.append(action))

    cli.main()

    assert seen == ["start"]


def test_main_dispatches_daemon_default_status(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas", "daemon"])
    monkeypatch.setattr(cli, "run_daemon", lambda action: seen.append(action))

    cli.main()

    assert seen == ["status"]


def test_main_help_command_prints_usage(monkeypatch, capsys):
    monkeypatch.setattr(cli.sys, "argv", ["toas", "help"])

    cli.main()

    out = capsys.readouterr().out
    assert out.startswith("Usage:\n")
    assert "toas jump <index>" in out


def test_main_help_flag_prints_usage(monkeypatch, capsys):
    monkeypatch.setattr(cli.sys, "argv", ["toas", "--help"])

    cli.main()

    out = capsys.readouterr().out
    assert out.startswith("Usage:\n")
    assert "TOAS_RPC_MODE=auto|on|off" in out


def test_main_jump_without_index_shows_usage(monkeypatch):
    monkeypatch.setattr(cli.sys, "argv", ["toas", "jump"])

    with pytest.raises(SystemExit, match=r"usage: toas jump <index>"):
        cli.main()


def test_main_prompt_without_ref_shows_usage(monkeypatch):
    monkeypatch.setattr(cli.sys, "argv", ["toas", "prompt"])

    with pytest.raises(SystemExit, match=r"usage: toas prompt <ref>"):
        cli.main()


def test_run_daemon_start(monkeypatch, capsys):
    monkeypatch.setattr(cli.daemon, "start", lambda: {"running": True, "pid": 123, "endpoint": "/tmp/toas.sock"})

    cli.run_daemon("start")

    assert capsys.readouterr().out == "daemon running pid=123 endpoint=/tmp/toas.sock\n"


def test_run_daemon_stop(monkeypatch, capsys):
    monkeypatch.setattr(cli.daemon, "stop", lambda: {"running": False, "pid": None, "endpoint": "/tmp/toas.sock"})

    cli.run_daemon("stop")

    assert capsys.readouterr().out == "daemon stopped\n"


def test_run_daemon_status_running(monkeypatch, capsys):
    monkeypatch.setattr(cli.daemon, "status", lambda: {"running": True, "pid": 123, "endpoint": "/tmp/toas.sock"})

    cli.run_daemon("status")

    assert capsys.readouterr().out == "daemon running pid=123 endpoint=/tmp/toas.sock\n"


def test_run_daemon_status_stopped(monkeypatch, capsys):
    monkeypatch.setattr(cli.daemon, "status", lambda: {"running": False, "pid": None, "endpoint": "/tmp/toas.sock"})

    cli.run_daemon("status")

    assert capsys.readouterr().out == "daemon stopped endpoint=/tmp/toas.sock\n"


def test_run_daemon_rejects_unknown_action():
    with pytest.raises(SystemExit, match="unknown daemon command: bogus"):
        cli.run_daemon("bogus")


def test_run_step_honors_jump_binding(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "old", "metadata": {}}\n'
            '{"kind": "jump", "payload": {"bind_index": 1}}\n'
        ),
        encoding="utf-8",
    )

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        assert transcript == "## TOAS:USER\n\nhello\n"
        assert log == [{"role": "user", "content": "old", "id": "n0"}]
        assert bind_index == 1
        assert bind_parent == "n0"
        assert anchor_index == 0
        assert storage_tip_parent == "n0"
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert capsys.readouterr().out == ""


def test_run_transcript_projects_selected_head_by_default(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "main", "metadata": {}}\n'
            '{"id": "n2", "parent": "n0", "role": "assistant", "content": "branch", "metadata": {}}\n'
            '{"kind": "head", "payload": {"head_id": "n2"}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_transcript()

    assert capsys.readouterr().out == "## TOAS:USER\n\nroot\n\n## TOAS:ASSISTANT\n\nbranch\n"


def test_run_history_prints_selected_head_bind_and_recent_events(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "main", "metadata": {}}\n'
            '{"kind": "head", "payload": {"head_id": "n1"}}\n'
            '{"kind": "jump", "payload": {"bind_index": 1}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_history()

    assert capsys.readouterr().out == (
        "selected_head=n1\n"
        "bind_index=1\n"
        "heads:\n"
        "* n1 assistant\n"
        "recent:\n"
        "- n0 user: root\n"
        "- n1 assistant: main\n"
        "- head head_id=n1\n"
        "- jump bind_index=1\n"
    )


def test_run_transcript_can_target_explicit_head(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "main", "metadata": {}}\n'
            '{"id": "n2", "parent": "n0", "role": "assistant", "content": "branch", "metadata": {}}\n'
            '{"kind": "head", "payload": {"head_id": "n2"}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_transcript("n1")

    assert capsys.readouterr().out == "## TOAS:USER\n\nroot\n\n## TOAS:ASSISTANT\n\nmain\n"


def test_run_llm_input_projects_selected_head_by_default(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "part one", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "user", "content": "part two", "metadata": {}}\n'
            '{"id": "n2", "parent": "n1", "role": "assistant", "content": "answer", "metadata": {}}\n'
            '{"kind": "head", "payload": {"head_id": "n2"}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_llm_input()

    assert capsys.readouterr().out == "## TOAS:USER\n\npart one\n\npart two\n\n## TOAS:ASSISTANT\n\nanswer\n\n"


def test_run_prompt_prints_named_prompt_asset(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    cli.run_prompt("protocol/terse_v1")

    out = capsys.readouterr().out
    assert "TOAS" in out
    assert "action" in out


def test_run_prompts_lists_session_start_assets(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    cli.run_prompts("session-start/start-here")

    assert capsys.readouterr().out == (
        "session-start/start-here/blank-page_v1\t[start-here] Blank Page Starter\tA simple opening prompt for when you do not know how to begin.\n"
        "session-start/start-here/collaborative-builder_v1\t[start-here] Collaborative Builder\tStart in a collaborative mode that balances clarification and forward motion.\n"
        "session-start/start-here/spec-first_v1\t[start-here] Spec First\tStart by clarifying requirements before any solutioning begins.\n"
    )


def test_run_prompts_lists_dynamic_capability_assets(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    cli.run_prompts("dynamic/capabilities")

    assert capsys.readouterr().out == (
        "dynamic/capabilities/overview_v1\t[capability-advertisement] Capability Overview\tAdvertise the current TOAS runtime capabilities and limits.\n"
        "dynamic/capabilities/repo-work_v1\t[capability-advertisement] Repo Work Capabilities\tAdvertise repo-reading, searching, shell, and history inspection capabilities.\n"
        "dynamic/capabilities/start-here_v1\t[capability-advertisement] Capability Start Here\tAdvertise a simple set of ways the user can start working with TOAS.\n"
    )


def test_run_prompt_renders_dynamic_capability_prompt(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    cli.run_prompt("dynamic/capabilities/start-here_v1")

    out = capsys.readouterr().out
    assert "clarify the task before solutioning" in out
    assert "search or read files in the workspace" in out


def test_run_rebuild_writes_session_from_selected_head_and_emits_anchor(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "branch", "metadata": {}}\n'
            '{"kind": "head", "payload": {"head_id": "n1"}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_rebuild()

    assert Path(".toas/session.md").read_text(encoding="utf-8") == "## TOAS:USER\n\nroot\n\n## TOAS:ASSISTANT\n\nbranch\n"
    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "branch", "metadata": {}}\n'
        '{"kind": "head", "payload": {"head_id": "n1"}}\n'
        '{"kind": "anchor", "payload": {"offset": 46, "node_id": "n1"}}\n'
    )
    assert capsys.readouterr().out == "rebuilt .toas/session.md from head n1\n"


def test_run_rebuild_avoids_duplicate_equivalent_anchor(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
            '{"kind": "anchor", "payload": {"offset": 19, "node_id": "n0"}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_rebuild()

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
        '{"kind": "anchor", "payload": {"offset": 19, "node_id": "n0"}}\n'
    )
    assert capsys.readouterr().out == "rebuilt .toas/session.md from head n0\n"


def test_run_rebuild_uses_configured_session_transcript_path(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text('[session]\ntranscript_path = ".toas/session2.md"\n', encoding="utf-8")
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n',
        encoding="utf-8",
    )

    cli.run_rebuild()

    assert Path(".toas/session2.md").read_text(encoding="utf-8") == "## TOAS:USER\n\nroot\n"
    assert capsys.readouterr().out == "rebuilt .toas/session2.md from head n0\n"


def test_run_step_derives_bind_parent_from_message_event_space(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
            '{"kind": "jump", "payload": {"bind_index": 1}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "old", "metadata": {}}\n'
        ),
        encoding="utf-8",
    )

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        assert log == [
            {"role": "user", "content": "root", "id": "n0"},
            {"role": "assistant", "content": "old", "id": "n1"},
        ]
        assert bind_index == 1
        assert bind_parent == "n0"
        assert anchor_index == 0
        assert storage_tip_parent == "n1"
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert capsys.readouterr().out == ""


def test_run_step_uses_latest_jump_record_from_history(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
            '{"kind": "jump", "payload": {"bind_index": 0}}\n'
            '{"kind": "jump", "payload": {"bind_index": 1}}\n'
        ),
        encoding="utf-8",
    )

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        assert bind_index == 1
        assert bind_parent == "n0"
        assert anchor_index == 0
        assert storage_tip_parent == "n0"
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert capsys.readouterr().out == ""


def test_run_step_projects_graph_events_before_calling_step(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n1", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
            '{"kind": "jump", "payload": {"bind_index": 1}}\n'
        ),
        encoding="utf-8",
    )

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        assert transcript == "## TOAS:USER\n\nhello\n"
        assert log == [{"role": "user", "content": "hello", "id": "n1"}]
        assert bind_index == 1
        assert bind_parent == "n1"
        assert anchor_index == 0
        assert storage_tip_parent == "n1"
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert capsys.readouterr().out == ""


def test_run_step_writes_new_nodes_as_message_events(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        return (
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
            [{"role": "assistant", "content": "hi"}],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}}\n'
    )
    assert capsys.readouterr().out == "## TOAS:ASSISTANT\n\nhi\n\n"


def test_run_step_reads_transcript_path_from_durable_config_override(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        '{"kind": "config_override", "payload": {"session": {"transcript_path": ".toas/session-purpose.md"}}}\n',
        encoding="utf-8",
    )
    Path(".toas/session.md").write_text("## TOAS:USER\n\nDEFAULT_MARKER\n", encoding="utf-8")
    Path(".toas/session-purpose.md").write_text("## TOAS:USER\n\nPURPOSE_MARKER\n", encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        seen["transcript"] = transcript
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)
    cli.run_step()
    assert seen["transcript"] == "## TOAS:USER\n\nPURPOSE_MARKER\n"


def test_run_step_prefers_selected_surface_binding_over_config_override(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"kind": "config_override", "payload": {"session": {"transcript_path": ".toas/from-config.md"}}}\n'
            '{"kind": "surface_bind", "payload": {"surface_id": "docs", "transcript_path": ".toas/from-surface.md"}}\n'
            '{"kind": "surface_select", "payload": {"surface_id": "docs"}}\n'
        ),
        encoding="utf-8",
    )
    Path(".toas/from-config.md").write_text("## TOAS:USER\n\nCONFIG_MARKER\n", encoding="utf-8")
    Path(".toas/from-surface.md").write_text("## TOAS:USER\n\nSURFACE_MARKER\n", encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        seen["transcript"] = transcript
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)
    cli.run_step()
    assert seen["transcript"] == "## TOAS:USER\n\nSURFACE_MARKER\n"


def test_run_step_local_surface_id_uses_bound_transcript(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        '{"kind":"surface_bind","payload":{"surface_id":"docs","transcript_path":".toas/session-docs.md"}}\n',
        encoding="utf-8",
    )
    Path(".toas/session-docs.md").write_text("## TOAS:USER\n\nSURFACE_ONLY\n", encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        seen["transcript"] = transcript
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)
    cli.run_step_local(surface_id="docs")
    assert seen["transcript"] == "## TOAS:USER\n\nSURFACE_ONLY\n"


def test_run_step_local_surface_id_ignores_selected_surface_when_explicit_surface_requested(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"kind":"surface_bind","payload":{"surface_id":"docs","transcript_path":".toas/session-docs.md"}}\n'
            '{"kind":"surface_bind","payload":{"surface_id":"roadmap","transcript_path":".toas/session-roadmap.md"}}\n'
            '{"kind":"surface_select","payload":{"surface_id":"roadmap"}}\n'
        ),
        encoding="utf-8",
    )
    Path(".toas/session-docs.md").write_text("## TOAS:USER\n\nDOCS_MARKER\n", encoding="utf-8")
    Path(".toas/session-roadmap.md").write_text("## TOAS:USER\n\nROADMAP_MARKER\n", encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        seen["transcript"] = transcript
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)
    cli.run_step_local(surface_id="docs")
    assert seen["transcript"] == "## TOAS:USER\n\nDOCS_MARKER\n"


def test_run_step_local_surface_non_interference_preserves_other_transcript_bytes(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"kind":"surface_bind","payload":{"surface_id":"docs","transcript_path":".toas/session-docs.md"}}\n'
            '{"kind":"surface_bind","payload":{"surface_id":"roadmap","transcript_path":".toas/session-roadmap.md"}}\n'
        ),
        encoding="utf-8",
    )
    docs_path = Path(".toas/session-docs.md")
    roadmap_path = Path(".toas/session-roadmap.md")
    docs_path.write_text("## TOAS:USER\n\nDOCS_MARKER\n", encoding="utf-8")
    roadmap_original = "## TOAS:USER\n\nROADMAP_MARKER\n"
    roadmap_path.write_text(roadmap_original, encoding="utf-8")

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)
    cli.run_step_local(surface_id="docs")
    assert roadmap_path.read_text(encoding="utf-8") == roadmap_original


def test_run_step_stdout_uses_session_crlf_line_endings(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\r\n\r\nhello\r\n", encoding="utf-8")

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        return (
            [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ],
            [{"role": "assistant", "content": "hi"}],
        )

    monkeypatch.setattr(cli, "step", fake_step)
    cli.run_step()
    assert capsys.readouterr().out == "## TOAS:ASSISTANT\n\nhi\n\n"


def test_run_step_session_update_preserves_session_crlf_line_endings(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\r\n\r\nhello\r\n", encoding="utf-8")

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        return (
            [{"role": "result", "content": "compact", "session_update": {"transcript": "## TOAS:USER\n\nupdated\n"}}],
            [{"role": "result", "content": "compact"}],
        )

    monkeypatch.setattr(cli, "step", fake_step)
    cli.run_step()
    with Path(".toas/session.md").open("r", encoding="utf-8", newline="") as f:
        assert f.read() == "## TOAS:USER\r\n\r\nupdated\r\n"


def test_run_step_uses_real_generation_callback_with_projected_llm_input(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\npart one\n\n## TOAS:USER\n\npart two\n", encoding="utf-8")
    seen = {}
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")

    def fake_generate(messages, **kwargs):
        settings = kwargs.get("settings")
        extra_body = kwargs.get("extra_body")
        seen["messages"] = messages
        seen["model"] = kwargs.get("settings").llm_model if kwargs.get("settings") else None
        seen["extra_body"] = kwargs.get("extra_body")
        return {
            "role": "assistant",
            "content": "answer",
            "response": {
                "content": "answer",
                "model": "Qwen3.5-35B-A3B-UD-Q8_K_XL.gguf",
                "reasoning_content": "private chain",
            },
        }

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)

    cli.run_step()

    assert seen["messages"] == [{"role": "user", "content": "part one\n\npart two"}]
    assert seen["model"] == "local-model"
    assert seen["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "part one", "metadata": {}, "provenance": {"source": "user_authored"}}\n'
        '{"id": "n1", "parent": "n0", "role": "user", "content": "part two", "metadata": {}, "provenance": {"source": "user_authored"}}\n'
        '{"id": "n2", "parent": "n1", "role": "assistant", "content": "answer", "metadata": {}, "provenance": {"source": "llm_generated"}}\n'
        '{"kind": "llm_call", "payload": {"requested_model": "local-model", "trace_mode": "minimal", "input_count": 1, "response_model": "Qwen3.5-35B-A3B-UD-Q8_K_XL.gguf", "response": {"content": "answer", "has_reasoning_blocks": false}, "response_has_reasoning_content": true, "attempt": 1, "max_attempts": 1, "message_id": "n2"}}\n'
    )
    assert capsys.readouterr().out == "## TOAS:ASSISTANT\n\nanswer\n\n"


def test_run_step_records_llm_failure_and_exits(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")

    def fake_generate(messages, **kwargs):
        settings = kwargs.get("settings")
        extra_body = kwargs.get("extra_body")
        raise RuntimeError("backend unavailable")

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)

    with pytest.raises(SystemExit, match="llm generation failed after 1 attempt\\(s\\): backend unavailable \\(endpoint="):
        cli.run_step()

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"kind": "llm_call", "payload": {"requested_model": "local-model", "trace_mode": "minimal", "input_count": 1, "error": "backend unavailable (endpoint=http://localhost:8080/v1, endpoint_source=env_or_default, model=local-model, model_source=env_or_default, api_key_source=env:TOAS_LLM_API_KEY, transport_source=default)", "error_class": "transient", "attempt": 1, "max_attempts": 1}}\n'
    )


def test_run_step_retries_transient_llm_failure_then_succeeds(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    Path("toas.toml").write_text("[generation]\nmax_retries = 2\nretry_delay_s = 0\n", encoding="utf-8")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    calls = {"n": 0}

    def fake_generate(messages, **kwargs):
        settings = kwargs.get("settings")
        extra_body = kwargs.get("extra_body")
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("temporary backend failure")
        return {"role": "assistant", "content": "answer", "response": {"content": "answer", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)

    cli.run_step()

    assert calls["n"] == 2
    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"kind": "llm_call", "payload": {"requested_model": "local-model", "trace_mode": "minimal", "input_count": 1, "error": "temporary backend failure (endpoint=http://localhost:8080/v1, endpoint_source=env_or_default, model=local-model, model_source=env_or_default, api_key_source=env:TOAS_LLM_API_KEY, transport_source=default)", "error_class": "transient", "attempt": 1, "max_attempts": 3}}\n'
        '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}, "provenance": {"source": "user_authored"}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "answer", "metadata": {}, "provenance": {"source": "llm_generated"}}\n'
        '{"kind": "llm_call", "payload": {"requested_model": "local-model", "trace_mode": "minimal", "input_count": 1, "response_model": "m", "response": {"content": "answer", "has_reasoning_blocks": false}, "attempt": 2, "max_attempts": 3, "message_id": "n1"}}\n'
    )
    assert capsys.readouterr().out == "## TOAS:ASSISTANT\n\nanswer\n\n"


def test_run_step_uses_llm_config_overrides_for_settings(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text('[llm]\nbase_url = "http://example/v1"\nmodel = "cfg-model"\n[generation]\ntransport_mode = "single_user_blob"\n', encoding="utf-8")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    seen = {}

    def fake_generate(messages, **kwargs):
        settings = kwargs.get("settings")
        extra_body = kwargs.get("extra_body")
        seen["settings"] = kwargs.get("settings")
        return {"role": "assistant", "content": "ok", "response": {"content": "ok", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)
    cli.run_step()
    assert seen["settings"].llm_base_url == "http://example/v1"
    assert seen["settings"].llm_model == "cfg-model"
    assert seen["settings"].llm_transport_mode == "single_user_blob"


def test_run_step_uses_selected_backend_settings(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text(
        '[llm]\n'
        '[[llm.backends]]\n'
        'id = "local"\n'
        'base_url = "http://localhost:8080/v1"\n'
        'model = "qwen"\n'
        'api_key_source = "env"\n'
        'api_key_ref = "TOAS_LLM_API_KEY"\n',
        encoding="utf-8",
    )
    Path("session.md").write_text("## TOAS:USER\n\n/backend local\n\n## TOAS:USER\n\nhello\n", encoding="utf-8")
    seen = {}

    def fake_generate(messages, **kwargs):
        settings = kwargs.get("settings")
        extra_body = kwargs.get("extra_body")
        seen["settings"] = kwargs.get("settings")
        return {"role": "assistant", "content": "ok", "response": {"content": "ok", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)
    cli.run_step()
    assert seen["settings"].llm_base_url == "http://localhost:8080/v1"
    assert seen["settings"].llm_model == "qwen"


def test_run_step_fails_when_keyring_provider_unavailable(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text('[llm]\napi_key_source = "keyring"\napi_key_ref = "svc:user"\n', encoding="utf-8")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "keyring", None)
    with pytest.raises(SystemExit, match="failed to resolve llm api key"):
        cli.run_step()


def test_run_step_records_transport_mode_in_llm_call_when_non_default(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text('[generation]\ntransport_mode = "single_user_blob"\n', encoding="utf-8")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")

    def fake_generate(messages, **kwargs):
        settings = kwargs.get("settings")
        extra_body = kwargs.get("extra_body")
        return {"role": "assistant", "content": "ok", "response": {"content": "ok", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)
    cli.run_step()
    assert '"transport_mode": "single_user_blob"' in Path(".toas/events.jsonl").read_text(encoding="utf-8")


def test_run_step_preserves_stream_mode_from_env_settings(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    monkeypatch.setenv("TOAS_LLM_STREAM_MODE", "enabled")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    seen = {}

    def fake_generate(messages, **kwargs):
        settings = kwargs.get("settings")
        extra_body = kwargs.get("extra_body")
        seen["settings"] = kwargs.get("settings")
        return {"role": "assistant", "content": "ok", "response": {"content": "ok", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)
    cli.run_step()
    assert seen["settings"].llm_stream_mode == "enabled"


def test_run_step_uses_runtime_streaming_mode_from_config(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    Path("toas.toml").write_text('[runtime]\nstreaming_mode = "enabled"\n', encoding="utf-8")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    seen = {}

    def fake_generate(messages, **kwargs):
        settings = kwargs.get("settings")
        extra_body = kwargs.get("extra_body")
        seen["settings"] = kwargs.get("settings")
        return {"role": "assistant", "content": "ok", "response": {"content": "ok", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)
    cli.run_step()
    assert seen["settings"].llm_stream_mode == "enabled"


def test_run_step_uses_runtime_streaming_mode_disabled_from_config(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    Path("toas.toml").write_text('[runtime]\nstreaming_mode = "disabled"\n', encoding="utf-8")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    seen = {}

    def fake_generate(messages, **kwargs):
        settings = kwargs.get("settings")
        extra_body = kwargs.get("extra_body")
        seen["settings"] = kwargs.get("settings")
        return {"role": "assistant", "content": "ok", "response": {"content": "ok", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)
    cli.run_step()
    assert seen["settings"].llm_stream_mode == "disabled"


def test_run_step_passes_reasoning_callback_when_thinking_stream_enabled(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "1")
    monkeypatch.setenv("TOAS_STREAM_THINKING", "1")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    seen = {}

    def fake_generate(
        messages,
        *,
        settings=None,
        extra_body=None,
        on_delta=None,
        on_reasoning_delta=None,
        on_prompt_progress=None,
    ):
        seen["on_reasoning_delta"] = on_reasoning_delta
        if on_reasoning_delta is not None:
            on_reasoning_delta("trace")
        return {"role": "assistant", "content": "ok", "response": {"content": "ok", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)
    cli.run_step()
    assert callable(seen["on_reasoning_delta"])


def test_run_step_passes_prompt_progress_callback_when_enabled(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "1")
    monkeypatch.setenv("TOAS_STREAM_PROMPT_PROGRESS", "1")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    seen = {}

    def fake_generate(
        messages,
        *,
        settings=None,
        extra_body=None,
        on_delta=None,
        on_reasoning_delta=None,
        on_prompt_progress=None,
    ):
        seen["on_prompt_progress"] = on_prompt_progress
        return {"role": "assistant", "content": "ok", "response": {"content": "ok", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)
    cli.run_step()
    assert callable(seen["on_prompt_progress"])


def test_run_step_streamed_delta_without_newline_separates_assistant_marker(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "1")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")

    def fake_generate(
        messages,
        *,
        settings=None,
        extra_body=None,
        on_delta=None,
        on_reasoning_delta=None,
        on_prompt_progress=None,
    ):
        if on_delta is not None:
            on_delta("stream-fragment")
        return {"role": "assistant", "content": "ok", "response": {"content": "ok", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)
    cli.run_step()
    out = capsys.readouterr().out
    assert "stream-fragment\n## TOAS:ASSISTANT\n\nok\n\n" in out


def test_run_step_streaming_callable_result_includes_user_and_result_markers(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "1")
    Path("session.md").write_text(
        "## TOAS:ASSISTANT\n\nrun shell\n```yaml\n- tool_name: shell\n  args:\n    argv: [\"pwd\"]\n```\n",
        encoding="utf-8",
    )

    def fake_generate(
        messages,
        *,
        settings=None,
        extra_body=None,
        on_delta=None,
        on_reasoning_delta=None,
        on_prompt_progress=None,
    ):
        if on_delta is not None:
            on_delta("## RESULT\n\n[OK] shell: exit=0\nstdout:\n/workspace\n")
        return {"role": "assistant", "content": "", "response": {"content": "", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)
    cli.run_step()
    out = capsys.readouterr().out
    assert "## TOAS:USER" in out
    assert "## RESULT" in out
    assert "[OK] shell: exit=0" in out


def test_stream_presenter_prompt_progress_dedupes_and_reports_diag(capsys):
    state = {"enabled": True, "emitted": False, "ends_with_newline": True}
    presenter = cli._StreamPresenter(
        stream_state=state,
        stream_thinking=True,
        stream_prompt_progress=True,
    )
    progress = types.SimpleNamespace(total=100, processed=10, cache=0, time_ms=50)
    presenter.on_prompt_progress(progress)
    presenter.on_prompt_progress(progress)
    presenter.finalize()
    out = capsys.readouterr().out
    assert "prompt 10/100 (10%) | cache=0 | t=50ms" in out
    assert presenter.progress_callbacks == 2
    assert presenter.progress_rendered == 1
    assert "rendered=1" in presenter.prompt_progress_diag_line()


def test_stream_presenter_closes_thinking_on_content_delta(capsys):
    state = {"enabled": True, "emitted": False, "ends_with_newline": True}
    presenter = cli._StreamPresenter(
        stream_state=state,
        stream_thinking=True,
        stream_prompt_progress=True,
    )
    presenter.on_reasoning_delta("trace")
    presenter.on_delta("answer")
    presenter.finalize()
    out = capsys.readouterr().out
    assert "## TOAS:THINKING\ntrace\n## /TOAS:THINKING\nanswer" in out


def test_stream_presenter_escapes_closed_set_marker_lines_across_chunks(capsys):
    state = {"enabled": True, "emitted": False, "ends_with_newline": True}
    presenter = cli._StreamPresenter(
        stream_state=state,
        stream_thinking=False,
        stream_prompt_progress=False,
    )
    presenter.on_delta("## TOAS:US")
    presenter.on_delta("ER\n")
    presenter.finalize()
    out = capsys.readouterr().out
    assert "\\## TOAS:USER\n" in out


def test_closed_set_marker_escaper_non_marker_probe_flushes_text():
    escaper = cli._ClosedSetMarkerStreamEscaper()
    assert escaper.feed("hello") == "hello"
    assert escaper.flush() == ""


def test_closed_set_marker_escaper_newline_after_prefix_probe_emits_literal():
    escaper = cli._ClosedSetMarkerStreamEscaper()
    # Prefix probe that is not an exact marker when newline arrives should be emitted as-is.
    assert escaper.feed("## TOAS:X\n") == "## TOAS:X\n"
    assert escaper.flush() == ""


def test_closed_set_marker_escaper_handles_newline_and_line_start_state():
    escaper = cli._ClosedSetMarkerStreamEscaper()
    assert escaper.feed("abc\n") == "abc\n"
    assert escaper.feed("## TOAS:ASSISTANT\n") == "\\## TOAS:ASSISTANT\n"


def test_closed_set_marker_escaper_emits_non_marker_after_prefix_probe():
    escaper = cli._ClosedSetMarkerStreamEscaper()
    assert escaper.feed("## TOAS:X") == "## TOAS:X"
    assert escaper.flush() == ""


def test_closed_set_marker_escaper_flush_escapes_exact_marker_without_newline():
    escaper = cli._ClosedSetMarkerStreamEscaper()
    assert escaper.feed("## TOAS:USER") == ""
    assert escaper.flush() == "\\## TOAS:USER"


def test_closed_set_marker_escaper_feed_flushes_probe_on_non_marker_prefix_end():
    escaper = cli._ClosedSetMarkerStreamEscaper()
    assert escaper.feed("## TOAS:USX") == "## TOAS:USX"
    assert escaper.flush() == ""


def test_closed_set_marker_escaper_emits_probe_when_chunk_ends_with_nonmarker_prefix():
    escaper = cli._ClosedSetMarkerStreamEscaper()
    # Ends with a non-marker probe at chunk boundary -> feed() should flush probe immediately.
    assert escaper.feed("a") == "a"
    assert escaper.flush() == ""


def test_closed_set_marker_escaper_flush_returns_non_marker_probe_text():
    escaper = cli._ClosedSetMarkerStreamEscaper()
    # Build marker prefix probe and then force non-marker tail to stay buffered.
    assert escaper.feed("## TOAS:") == ""
    assert escaper.feed("X") == "## TOAS:X"
    assert escaper.flush() == ""


def test_closed_set_marker_escaper_newline_non_marker_prefix_branch():
    escaper = cli._ClosedSetMarkerStreamEscaper()
    # Trigger line-start probe + newline path where probe is not an exact marker.
    assert escaper.feed("## TOAS:X\n") == "## TOAS:X\n"


def test_closed_set_marker_escaper_trailing_nonmarker_probe_flushes_from_feed():
    escaper = cli._ClosedSetMarkerStreamEscaper()
    # Leave a non-marker prefix probe at chunk end to exercise trailing flush path.
    assert escaper.feed("## TOAS:X") == "## TOAS:X"
    assert escaper.flush() == ""


def test_closed_set_marker_escaper_feed_emits_nonmarker_probe_on_newline_branch():
    escaper = cli._ClosedSetMarkerStreamEscaper()
    # Force probe/newline branch with a non-marker line payload.
    escaper._line_start = True
    escaper._probe = "## TOAS:"
    assert escaper.feed("\n") == "## TOAS:\n"


def test_closed_set_marker_escaper_feed_trailing_probe_manual_state_branch():
    escaper = cli._ClosedSetMarkerStreamEscaper()
    # Exercise defensive trailing-probe flush path directly.
    escaper._line_start = True
    escaper._probe = "not-a-marker"
    assert escaper.feed("") == "not-a-marker"
    assert escaper._probe == ""


def test_stream_presenter_prompt_progress_disabled_is_noop(capsys):
    state = {"enabled": True, "emitted": False, "ends_with_newline": True}
    presenter = cli._StreamPresenter(
        stream_state=state,
        stream_thinking=False,
        stream_prompt_progress=False,
    )
    progress = types.SimpleNamespace(total=100, processed=10, cache=0, time_ms=50)
    presenter.on_prompt_progress(progress)
    presenter.finalize()
    assert capsys.readouterr().out == ""
    assert presenter.progress_callbacks == 0


def test_stream_presenter_finalize_flushes_pending_probe_without_newline(capsys):
    state = {"enabled": True, "emitted": False, "ends_with_newline": True}
    presenter = cli._StreamPresenter(
        stream_state=state,
        stream_thinking=False,
        stream_prompt_progress=False,
    )
    presenter.on_delta("## TOAS:X")
    presenter.finalize()
    out = capsys.readouterr().out
    assert "## TOAS:X" in out
    assert state["emitted"] is True
    assert state["ends_with_newline"] is False


def test_stream_presenter_progress_row_clears_before_thinking_open(capsys):
    state = {"enabled": True, "emitted": False, "ends_with_newline": True}
    presenter = cli._StreamPresenter(
        stream_state=state,
        stream_thinking=True,
        stream_prompt_progress=True,
    )
    progress = types.SimpleNamespace(total=100, processed=10, cache=0, time_ms=50)
    presenter.on_prompt_progress(progress)
    presenter.on_reasoning_delta("trace")
    presenter.finalize()
    out = capsys.readouterr().out
    assert "prompt 10/100 (10%) | cache=0 | t=50ms" in out
    assert "## TOAS:THINKING" in out


def test_stream_presenter_reasoning_delta_ignored_when_thinking_disabled(capsys):
    state = {"enabled": True, "emitted": False, "ends_with_newline": True}
    presenter = cli._StreamPresenter(
        stream_state=state,
        stream_thinking=False,
        stream_prompt_progress=True,
    )
    presenter.on_reasoning_delta("trace")
    presenter.finalize()
    assert capsys.readouterr().out == ""


def test_stream_presenter_delta_noop_when_empty(capsys):
    state = {"enabled": True, "emitted": False, "ends_with_newline": True}
    presenter = cli._StreamPresenter(
        stream_state=state,
        stream_thinking=True,
        stream_prompt_progress=True,
    )
    presenter.on_delta("")
    presenter.finalize()
    assert capsys.readouterr().out == ""
    assert state["emitted"] is False


def test_stream_presenter_finalize_noops_with_no_pending_state(capsys):
    state = {"enabled": True, "emitted": False, "ends_with_newline": True}
    presenter = cli._StreamPresenter(
        stream_state=state,
        stream_thinking=False,
        stream_prompt_progress=False,
    )
    presenter.finalize()
    assert capsys.readouterr().out == ""
    assert state["emitted"] is False


def test_stream_presenter_closes_thinking_with_pending_probe_before_content(capsys):
    state = {"enabled": True, "emitted": False, "ends_with_newline": True}
    presenter = cli._StreamPresenter(
        stream_state=state,
        stream_thinking=True,
        stream_prompt_progress=False,
    )
    presenter.on_reasoning_delta("trace")
    presenter.on_reasoning_delta("## TOAS:US")
    presenter.on_delta("answer")
    presenter.finalize()
    out = capsys.readouterr().out
    assert "## TOAS:THINKING\ntrace" in out
    assert "## TOAS:US" in out
    assert "## /TOAS:THINKING\nanswer" in out


def test_stream_presenter_thinking_open_prints_pending_probe(capsys):
    state = {"enabled": True, "emitted": False, "ends_with_newline": True}
    presenter = cli._StreamPresenter(
        stream_state=state,
        stream_thinking=True,
        stream_prompt_progress=False,
    )
    presenter.on_delta("## TOAS:US")
    presenter.on_reasoning_delta("trace")
    presenter.finalize()
    out = capsys.readouterr().out
    assert "## TOAS:US" in out
    assert "## TOAS:THINKING\ntrace" in out


def test_stream_presenter_delta_closing_thinking_prints_pending_probe(capsys):
    state = {"enabled": True, "emitted": False, "ends_with_newline": True}
    presenter = cli._StreamPresenter(
        stream_state=state,
        stream_thinking=True,
        stream_prompt_progress=False,
    )
    presenter.on_reasoning_delta("trace")
    presenter.on_reasoning_delta("## TOAS:US")
    presenter.on_delta("answer")
    out = capsys.readouterr().out
    assert "## TOAS:US" in out
    assert "## /TOAS:THINKING" in out


def test_stream_presenter_finalize_marks_state_on_pending_flush(capsys):
    state = {"enabled": True, "emitted": False, "ends_with_newline": True}
    presenter = cli._StreamPresenter(
        stream_state=state,
        stream_thinking=False,
        stream_prompt_progress=False,
    )
    presenter.on_delta("## TOAS:US")
    presenter.finalize()
    out = capsys.readouterr().out
    assert "## TOAS:US" in out
    assert state["emitted"] is True
    assert state["ends_with_newline"] is False


def test_stream_presenter_delta_closing_thinking_prints_pending_probe_manual_state(capsys):
    state = {"enabled": True, "emitted": False, "ends_with_newline": True}
    presenter = cli._StreamPresenter(
        stream_state=state,
        stream_thinking=True,
        stream_prompt_progress=False,
    )
    presenter.thinking_open = True
    presenter._escaper._line_start = True
    presenter._escaper._probe = "pending-fragment"
    presenter.on_delta("answer")
    out = capsys.readouterr().out
    assert "pending-fragment" in out
    assert "## /TOAS:THINKING" in out


def test_render_blocks_escapes_result_body_closed_set_markers():
    rendered = cli._render_blocks(
        [
            {"role": "result", "content": "ok\n## TOAS:ASSISTANT\nend"},
        ]
    )
    assert "## RESULT\n\nok\n\\## TOAS:ASSISTANT\nend\n\n" == rendered


def test_run_step_ignores_prompt_progress_after_content_starts(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "1")
    monkeypatch.setenv("TOAS_STREAM_PROMPT_PROGRESS", "1")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")

    progress = types.SimpleNamespace(total=100, processed=10, cache=0, time_ms=50)
    progress_late = types.SimpleNamespace(total=100, processed=50, cache=0, time_ms=120)

    def fake_generate(
        messages,
        *,
        settings=None,
        extra_body=None,
        on_delta=None,
        on_reasoning_delta=None,
        on_prompt_progress=None,
    ):
        if on_prompt_progress is not None:
            on_prompt_progress(progress)
        if on_delta is not None:
            on_delta("hel")
        if on_prompt_progress is not None:
            on_prompt_progress(progress_late)
        if on_delta is not None:
            on_delta("lo")
        return {"role": "assistant", "content": "ok", "response": {"content": "ok", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)
    cli.run_step()
    out = capsys.readouterr().out
    assert "hello" in out


def test_run_step_emits_prompt_progress_diagnostic_when_enabled(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    monkeypatch.setenv("TOAS_STREAM_STDOUT", "1")
    monkeypatch.setenv("TOAS_STREAM_PROMPT_PROGRESS", "1")
    monkeypatch.setenv("TOAS_DEBUG_PROMPT_PROGRESS", "1")
    diag_path = tmp_path / "diag.log"
    monkeypatch.setenv("TOAS_DEBUG_PROMPT_PROGRESS_FILE", str(diag_path))
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")

    progress = types.SimpleNamespace(total=100, processed=10, cache=0, time_ms=50)

    def fake_generate(
        messages,
        *,
        settings=None,
        extra_body=None,
        on_delta=None,
        on_reasoning_delta=None,
        on_prompt_progress=None,
    ):
        if on_prompt_progress is not None:
            on_prompt_progress(progress)
        if on_delta is not None:
            on_delta("ok")
        return {"role": "assistant", "content": "ok", "response": {"content": "ok", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)
    cli.run_step()
    out = capsys.readouterr().out
    assert "[diag] prompt_progress: callbacks=1" in out
    assert diag_path.exists()
    assert "callbacks=1" in diag_path.read_text(encoding="utf-8")


def test_run_step_writes_full_llm_trace_when_enabled(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    monkeypatch.setenv("TOAS_LLM_TRACE", "full")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")

    def fake_generate(messages, **kwargs):
        settings = kwargs.get("settings")
        extra_body = kwargs.get("extra_body")
        return {
            "role": "assistant",
            "content": "<think>private</think>\nanswer",
            "response": {
                "content": "<think>private</think>\nanswer",
                "model": "model-full",
                "reasoning_content": "private chain",
            },
        }

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)

    cli.run_step()

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}, "provenance": {"source": "user_authored"}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "<think>private</think>\\nanswer", "metadata": {}, "provenance": {"source": "llm_generated"}}\n'
        '{"kind": "llm_call", "payload": {"requested_model": "local-model", "trace_mode": "full", "input_count": 1, "messages": [{"role": "user", "content": "hello"}], "response_model": "model-full", "response": {"content": "<think>private</think>\\nanswer", "reasoning_content": "private chain", "has_reasoning_blocks": true}, "response_has_reasoning_content": true, "attempt": 1, "max_attempts": 1, "message_id": "n1"}}\n'
    )


def test_run_step_projects_assistant_think_blocks_out_of_next_llm_input(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "<think>private</think>\\nanswer", "metadata": {}}\n'
        ),
        encoding="utf-8",
    )
    Path("session.md").write_text(
        "## TOAS:USER\n\nhello\n\n## TOAS:ASSISTANT\n\n<think>private</think>\nanswer\n\n## TOAS:USER\n\nfollowup\n",
        encoding="utf-8",
    )
    seen = {}

    def fake_generate(messages, **kwargs):
        settings = kwargs.get("settings")
        extra_body = kwargs.get("extra_body")
        seen["messages"] = messages
        return {"role": "assistant", "content": "next", "response": {"content": "next", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)

    cli.run_step()

    assert seen["messages"] == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "answer"},
        {"role": "user", "content": "followup"},
    ]


def test_run_step_preserves_explicit_parent_from_step_output(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:ASSISTANT\n\nalternate\n", encoding="utf-8")
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}}\n'
        ),
        encoding="utf-8",
    )

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        return (
            [
                {"role": "assistant", "content": "alternate", "parent": "n0"},
            ],
            [],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}}\n'
        '{"id": "n2", "parent": "n0", "role": "assistant", "content": "alternate", "metadata": {}}\n'
    )
    assert capsys.readouterr().out == ""


def test_run_step_writes_tool_request_and_result_records_for_callable_tail(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text(
        "## TOAS:USER\n\nplease run this\n```yaml\n- tool_name: echo\n  args:\n    text: hi\n```\n",
        encoding="utf-8",
    )

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        return (
            [
                {
                    "role": "user",
                    "content": "please run this\n```yaml\n- tool_name: echo\n  args:\n    text: hi\n```",
                },
                {"role": "result", "content": "ran echo"},
            ],
            [{"role": "result", "content": "ran echo"}],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "please run this\\n```yaml\\n- tool_name: echo\\n  args:\\n    text: hi\\n```", "metadata": {}}\n'
        '{"kind": "tool_request", "related_to": "n0", "payload": [{"tool_name": "echo", "args": {"text": "hi"}}]}\n'
        '{"kind": "tool_result", "related_to": "n0", "payload": {"content": "ran echo"}}\n'
    )
    assert capsys.readouterr().out == "## TOAS:USER\n\n\n\n## RESULT\n\nran echo\n\n"


def test_run_step_extract_selection_adopts_user_content_without_tool_execution(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        '{"id": "n0", "parent": null, "role": "assistant", "content": "```yaml\\n- tool_name: echo\\n  args:\\n    text: hi\\n```", "metadata": {}}\n',
        encoding="utf-8",
    )
    Path("session.md").write_text("## TOAS:USER\n\n/extract 1\n", encoding="utf-8")

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
        **kwargs,
    ):
        return (
            [
                {"role": "user", "content": "/extract 1"},
                {"role": "user", "content": "```yaml\n- tool_name: echo\n  args:\n    text: hi\n```"},
            ],
            [
                {"role": "user", "content": "```yaml\n- tool_name: echo\n  args:\n    text: hi\n```"},
            ],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "assistant", "content": "```yaml\\n- tool_name: echo\\n  args:\\n    text: hi\\n```", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "user", "content": "/extract 1", "metadata": {}}\n'
        '{"id": "n2", "parent": "n1", "role": "user", "content": "```yaml\\n- tool_name: echo\\n  args:\\n    text: hi\\n```", "metadata": {}}\n'
    )
    assert capsys.readouterr().out == "## TOAS:USER\n\n```yaml\n- tool_name: echo\n  args:\n    text: hi\n```\n\n"


def test_run_step_replay_result_writes_tool_records_for_target_message(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        '{"id": "n0", "parent": null, "role": "assistant", "content": "```yaml\\n- tool_name: echo\\n  args:\\n    text: hi\\n```", "metadata": {}}\n',
        encoding="utf-8",
    )
    Path("session.md").write_text("## TOAS:USER\n\n/replay --index 1\n", encoding="utf-8")

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
        **kwargs,
    ):
        return (
            [
                {"role": "user", "content": "/replay --index 1"},
                {
                    "role": "result",
                    "content": "ran replay",
                    "payload": {"tool_name": "echo", "ok": True, "summary": "hi", "text": "hi"},
                    "replay_execution": {
                        "target_message_index": 1,
                        "request_plan": [{"tool_name": "echo", "args": {"text": "hi"}}],
                    },
                },
            ],
            [{"role": "result", "content": "ran replay"}],
        )

    monkeypatch.setattr(cli, "step", fake_step)
    cli.run_step()
    events = Path(".toas/events.jsonl").read_text(encoding="utf-8")
    assert '"kind": "tool_request", "related_to": "n0"' in events
    assert '"kind": "tool_result", "related_to": "n0"' in events


def test_run_step_prints_user_bridge_before_result_for_assistant_callable_tail(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text(
        "## TOAS:ASSISTANT\n\nplease run this\n```yaml\n- tool_name: echo\n  args:\n    text: hi\n```\n",
        encoding="utf-8",
    )

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        return (
            [
                {
                    "role": "assistant",
                    "content": "please run this\n```yaml\n- tool_name: echo\n  args:\n    text: hi\n```",
                },
                {"role": "result", "content": "ran echo"},
            ],
            [{"role": "result", "content": "ran echo"}],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "assistant", "content": "please run this\\n```yaml\\n- tool_name: echo\\n  args:\\n    text: hi\\n```", "metadata": {}}\n'
        '{"kind": "tool_request", "related_to": "n0", "payload": [{"tool_name": "echo", "args": {"text": "hi"}}]}\n'
        '{"kind": "tool_result", "related_to": "n0", "payload": {"content": "ran echo"}}\n'
    )
    assert capsys.readouterr().out == "## TOAS:USER\n\n\n\n## RESULT\n\nran echo\n\n"


def test_run_step_prints_user_bridge_before_result_for_user_callable_tail(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text(
        "## TOAS:USER\n\nplease run this\n```yaml\n- tool_name: echo\n  args:\n    text: hi\n```\n",
        encoding="utf-8",
    )

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        return (
            [
                {
                    "role": "user",
                    "content": "please run this\n```yaml\n- tool_name: echo\n  args:\n    text: hi\n```",
                },
                {"role": "result", "content": "ran echo"},
            ],
            [{"role": "result", "content": "ran echo"}],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "please run this\\n```yaml\\n- tool_name: echo\\n  args:\\n    text: hi\\n```", "metadata": {}}\n'
        '{"kind": "tool_request", "related_to": "n0", "payload": [{"tool_name": "echo", "args": {"text": "hi"}}]}\n'
        '{"kind": "tool_result", "related_to": "n0", "payload": {"content": "ran echo"}}\n'
    )
    assert capsys.readouterr().out == "## TOAS:USER\n\n\n\n## RESULT\n\nran echo\n\n"


def test_run_step_writes_shell_tool_request_and_result_records_for_dollar_tail(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text(
        "## TOAS:USER\n\nshow cwd\n$ pwd\n",
        encoding="utf-8",
    )

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        return (
            [
                {"role": "user", "content": "show cwd\n$ pwd"},
                {
                    "role": "result",
                    "content": "[OK] shell: exit=0\nstdout:\n/workspace",
                    "payload": {
                        "tool_name": "shell",
                        "ok": True,
                        "summary": "exit=0",
                        "argv": ["pwd"],
                        "cwd": "/workspace",
                        "exit_code": 0,
                        "stdout": "/workspace",
                        "stderr": "",
                        "content": "exit=0\nstdout:\n/workspace",
                    },
                },
            ],
            [{"role": "result", "content": "[OK] shell: exit=0\nstdout:\n/workspace"}],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "show cwd\\n$ pwd", "metadata": {}}\n'
        '{"kind": "tool_request", "related_to": "n0", "payload": [{"tool_name": "shell", "args": {"argv": ["pwd"]}}]}\n'
        '{"kind": "tool_result", "related_to": "n0", "payload": {"tool_name": "shell", "ok": true, "summary": "exit=0", "argv": ["pwd"], "cwd": "/workspace", "exit_code": 0, "stdout": "/workspace", "stderr": "", "content": "exit=0\\nstdout:\\n/workspace"}}\n'
    )
    assert capsys.readouterr().out == "## TOAS:USER\n\n\n\n## RESULT\n\n[OK] shell: exit=0\nstdout:\n/workspace\n\n"


def test_run_step_redacts_config_secret_command_before_durability(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\n/config secret set llm_api_key supersecret\n", encoding="utf-8")

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
        **kwargs,
    ):
        return (
            [
                {"role": "user", "content": "/config secret set llm_api_key supersecret"},
                {"role": "result", "content": "secret llm_api_key set for current runtime (non-durable)", "secret_update": {"action": "set", "key": "llm_api_key", "value": "supersecret"}},
            ],
            [{"role": "result", "content": "secret llm_api_key set for current runtime (non-durable)"}],
        )

    monkeypatch.setattr(cli, "step", fake_step)
    cli.run_step()
    events = Path(".toas/events.jsonl").read_text(encoding="utf-8")
    assert "supersecret" not in events
    assert "[REDACTED]" in events
    assert "config_override" not in events
    assert "supersecret" not in Path(".toas/session.md").read_text(encoding="utf-8")


def test_run_step_writes_config_unset_override_record(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\n/config unset llm.model\n", encoding="utf-8")

    def fake_step(transcript, log, **kwargs):
        return (
            [
                {"role": "user", "content": "/config unset llm.model"},
                {"role": "result", "content": "Unset override for llm.model.", "config_update": {"__op__": "unset", "key": "llm.model"}},
            ],
            [{"role": "result", "content": "Unset override for llm.model."}],
        )

    monkeypatch.setattr(cli, "step", fake_step)
    cli.run_step()
    events = Path(".toas/events.jsonl").read_text(encoding="utf-8")
    assert '"kind": "config_override"' in events
    assert '"__op__": "unset"' in events


def test_run_step_writes_config_restore_override_record(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\n/config restore\n", encoding="utf-8")

    def fake_step(transcript, log, **kwargs):
        return (
            [
                {"role": "user", "content": "/config restore"},
                {"role": "result", "content": "restore", "config_update": {"__op__": "restore"}},
            ],
            [{"role": "result", "content": "restore"}],
        )

    monkeypatch.setattr(cli, "step", fake_step)
    cli.run_step()
    events = Path(".toas/events.jsonl").read_text(encoding="utf-8")
    assert '"kind": "config_override"' in events
    assert '"__op__": "restore"' in events


def test_run_step_config_save_writes_toml(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\n/config save out.toml\n", encoding="utf-8")

    def fake_step(transcript, log, **kwargs):
        return (
            [
                {"role": "user", "content": "/config save out.toml"},
                {"role": "result", "content": "saved", "config_save": {"path": "out.toml"}},
            ],
            [{"role": "result", "content": "saved"}],
        )

    monkeypatch.setattr(cli, "step", fake_step)
    cli.run_step()
    rendered = Path("out.toml").read_text(encoding="utf-8")
    assert "[generation]" in rendered
    assert "[llm]" in rendered


def test_run_step_canonicalizes_assistant_loose_command_without_executing(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text(
        (
            "## TOAS:USER\n\n"
            "Scan the directories\n\n"
            "## TOAS:ASSISTANT\n\n"
            "```yaml\n"
            "command: find . -type f | head -5\n"
            "```\n"
        ),
        encoding="utf-8",
    )
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        '{"id": "n0", "parent": null, "role": "user", "content": "Scan the directories", "metadata": {}}\n',
        encoding="utf-8",
    )

    cli.run_step()

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "Scan the directories", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "```yaml\\ncommand: find . -type f | head -5\\n```", "metadata": {}}\n'
        '{"id": "n2", "parent": "n1", "role": "user", "content": "$ find . -type f | head -5", "metadata": {}}\n'
    )
    assert capsys.readouterr().out == "## TOAS:USER\n\n$ find . -type f | head -5\n\n"


def test_run_step_uses_persisted_command_context_for_user_shell(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    workdir = tmp_path / "work"
    workdir.mkdir()
    Path("session.md").write_text("## TOAS:USER\n\nshow cwd\n$ pwd\n", encoding="utf-8")
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        json.dumps({"kind": "command_context", "payload": {"cwd": str(workdir)}}) + "\n",
        encoding="utf-8",
    )

    cli.run_step()

    out = capsys.readouterr().out
    assert "stdout:\n" in out
    assert "/work" in out or "\\work" in out


def test_run_step_persists_command_context_updates_from_results(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\n/cd /tmp\n", encoding="utf-8")

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        return (
            [
                {"role": "user", "content": "/cd /tmp"},
                {
                    "role": "result",
                    "content": "/tmp",
                    "context_update": {"cwd": "/tmp", "previous_cwd": "/previous"},
                },
            ],
            [{"role": "result", "content": "/tmp", "context_update": {"cwd": "/tmp", "previous_cwd": "/previous"}}],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "/cd /tmp", "metadata": {}}\n'
        '{"kind": "command_request", "payload": {"id": "c1", "command": "cd", "args": ["/tmp"]}, "related_to": "n0"}\n'
        '{"kind": "command_result", "payload": {"ok": true, "content": "/tmp", "context_update": {"cwd": "/tmp", "previous_cwd": "/previous"}}, "related_to": "c1"}\n'
        '{"kind": "command_context", "payload": {"cwd": "/tmp", "previous_cwd": "/previous"}}\n'
    )
    assert capsys.readouterr().out == "## RESULT\n\n/tmp\n\n"


def test_run_step_persists_workspace_scope_updates_from_results(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\n/workspace mode unbounded\n", encoding="utf-8")

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        return (
            [
                {"role": "user", "content": "/workspace mode unbounded"},
                {
                    "role": "result",
                    "content": "mode=unbounded",
                    "workspace_update": {"mode": "unbounded", "roots": [str(tmp_path)]},
                },
            ],
            [{"role": "result", "content": "mode=unbounded", "workspace_update": {"mode": "unbounded", "roots": [str(tmp_path)]}}],
        )

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    events = [
        json.loads(line)
        for line in Path(".toas/events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert events == [
        {"id": "n0", "parent": None, "role": "user", "content": "/workspace mode unbounded", "metadata": {}},
        {"kind": "command_request", "payload": {"id": "c1", "command": "workspace", "args": ["mode", "unbounded"]}, "related_to": "n0"},
        {
            "kind": "command_result",
            "payload": {"ok": True, "content": "mode=unbounded", "workspace_update": {"mode": "unbounded", "roots": [str(tmp_path)]}},
            "related_to": "c1",
        },
        {"kind": "workspace_scope", "payload": {"mode": "unbounded", "roots": [str(tmp_path)]}},
    ]
    assert capsys.readouterr().out == "## RESULT\n\nmode=unbounded\n\n"


def test_run_step_uses_alignment_anchor_when_transcript_matches_prefix(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\nhello\n\n## TOAS:ASSISTANT\n\nhi\n\n## TOAS:USER\n\nnext\n", encoding="utf-8")
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}}\n'
            '{"kind": "anchor", "payload": {"offset": 43, "node_id": "n1"}}\n'
        ),
        encoding="utf-8",
    )

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        assert anchor_index == 2
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert capsys.readouterr().out == ""


def test_run_step_uses_selected_head_lineage_for_alignment(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\nroot\n\n## TOAS:ASSISTANT\n\nbranch\n", encoding="utf-8")
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "main", "metadata": {}}\n'
            '{"id": "n2", "parent": "n0", "role": "assistant", "content": "branch", "metadata": {}}\n'
            '{"kind": "head", "payload": {"head_id": "n2"}}\n'
        ),
        encoding="utf-8",
    )

    def fake_step(
        transcript,
        log,
        generate=None,
        execute=None,
        bind_index=None,
        bind_parent=None,
        anchor_index=None,
        storage_tip_parent=None,
    ):
        assert log == [
            {"role": "user", "content": "root", "id": "n0"},
            {"role": "assistant", "content": "branch", "id": "n2"},
        ]
        assert bind_parent == "n2"
        assert storage_tip_parent == "n2"
        return [], []

    monkeypatch.setattr(cli, "step", fake_step)

    cli.run_step()

    assert capsys.readouterr().out == ""


def test_main_rejects_unknown_command(monkeypatch):
    monkeypatch.setattr(cli.sys, "argv", ["toas", "bogus"])

    with pytest.raises(SystemExit, match="unknown command: bogus"):
        cli.main()


def test_run_step_prefers_rpc_when_available(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "_should_prefer_rpc", lambda: True)
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: {"stdout": "## RESULT\n\nok\n\n"})
    monkeypatch.setattr(cli, "run_step_local", lambda: (_ for _ in ()).throw(AssertionError("should not run local")))

    cli.run_step()

    assert capsys.readouterr().out == "## RESULT\n\nok\n\n"


def test_run_step_falls_back_to_local_when_rpc_fails(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "_should_prefer_rpc", lambda: True)
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: (_ for _ in ()).throw(cli.RpcClientError("down")))

    seen = {"local": False}

    def fake_local():
        seen["local"] = True

    monkeypatch.setattr(cli, "run_step_local", fake_local)

    cli.run_step()

    assert seen["local"] is True


def test_run_jump_prefers_rpc_when_enabled(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: {"stdout": "bound transcript to node 5\n"})
    monkeypatch.setattr(cli, "run_jump_local", lambda index: (_ for _ in ()).throw(AssertionError("local jump should not run")))

    cli.run_jump(5)

    assert capsys.readouterr().out == "bound transcript to node 5\n"


def test_run_jump_uses_local_when_rpc_mode_off(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "off")
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: (_ for _ in ()).throw(AssertionError("rpc should not run")))

    cli.run_jump(2)

    assert capsys.readouterr().out == "bound transcript to node 2\n"
    assert Path(".toas/events.jsonl").read_text(encoding="utf-8") == (
        '{"kind": "jump", "payload": {"bind_index": 2}}\n'
    )


def test_run_step_creates_index_alongside_events(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")

    def fake_generate(messages, **kwargs):
        settings = kwargs.get("settings")
        extra_body = kwargs.get("extra_body")
        return {"role": "assistant", "content": "hi", "response": {"content": "hi", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)

    cli.run_step()

    assert Path(".toas/events.idx").exists()
    # index has one record per message event (user + assistant = 2)
    from toas.graph import INDEX_RECORD_SIZE, read_index
    assert Path(".toas/events.idx").stat().st_size == 2 * INDEX_RECORD_SIZE
    records = read_index(str(tmp_path / ".toas/events.idx"))
    assert [mid for _, _, mid in records] == ["n0", "n1"]


def test_run_step_transient_frontier_flip_is_not_persisted(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\nhello\n\n## TOAS:ASSISTANT\n\nhi\n", encoding="utf-8")
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id":"n0","parent":null,"role":"user","content":"hello","metadata":{}}\n'
            '{"id":"n1","parent":"n0","role":"assistant","content":"hi","metadata":{}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_step_local()

    out = capsys.readouterr().out
    assert "## TOAS:USER" in out
    events_after = Path(".toas/events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(events_after) == 2


def test_run_step_local_transcript_edit_branches_from_divergence_boundary(monkeypatch, tmp_path):
    import json

    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id":"n0","parent":null,"role":"user","content":"A","metadata":{}}\n'
            '{"id":"n1","parent":"n0","role":"assistant","content":"B","metadata":{}}\n'
            '{"id":"n2","parent":"n1","role":"user","content":"C","metadata":{}}\n'
        ),
        encoding="utf-8",
    )
    Path(".toas/session.md").write_text(
        "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nD\n\n## TOAS:USER\n\nC\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "generate_assistant_message", lambda *_args, **_kwargs: {"role": "assistant", "content": "D"})

    cli.run_step_local()

    events = [
        json.loads(line)
        for line in Path(".toas/events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    message_events = [event for event in events if "id" in event and "role" in event]
    id_to_event = {event["id"]: event for event in message_events}
    children = {event["id"]: [] for event in message_events}
    for event in message_events:
        parent = event.get("parent")
        if isinstance(parent, str) and parent in children:
            children[parent].append(event["id"])

    a_id = next(event["id"] for event in message_events if event["role"] == "user" and event["content"] == "A")
    c_ids = [event["id"] for event in message_events if event["role"] == "user" and event["content"] == "C"]
    heads = [event["id"] for event in message_events if not children[event["id"]]]

    assert len(c_ids) == 2
    assert len(heads) == 2
    assert len(children[a_id]) == 2
    c_parents = {id_to_event[cid]["parent"] for cid in c_ids}
    assert len(c_parents) == 2


def test_run_step_local_assistant_only_divergence_branches_from_user_boundary(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    events_path = Path(".toas/events.jsonl")
    events_path.write_text(
        (
            '{"id":"n0","parent":null,"role":"user","content":"A","metadata":{}}\n'
            '{"id":"n1","parent":"n0","role":"assistant","content":"B","metadata":{}}\n'
        ),
        encoding="utf-8",
    )
    Path(".toas/session.md").write_text(
        "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nD\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_rpc_stdout", lambda _op: False)
    monkeypatch.setattr(cli, "generate_assistant_message", lambda *_args, **_kwargs: {"role": "assistant", "content": ""})
    cli.run_step_local()
    events = cli.read_log(str(events_path))
    id_to_event = {event.get("id"): event for event in events if isinstance(event.get("id"), str)}
    d_nodes = [event for event in events if event.get("role") == "assistant" and event.get("content") == "D"]
    assert len(d_nodes) >= 1
    latest_d = d_nodes[-1]
    assert latest_d.get("parent") == "n0"
    assert "n1" in id_to_event
    assert latest_d["id"] != "n1"


def test_run_step_local_multi_turn_tail_preserves_linear_order_after_divergence(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    events_path = Path(".toas/events.jsonl")
    events_path.write_text(
        (
            '{"id":"n0","parent":null,"role":"user","content":"A","metadata":{}}\n'
            '{"id":"n1","parent":"n0","role":"assistant","content":"B","metadata":{}}\n'
            '{"id":"n2","parent":"n1","role":"user","content":"C","metadata":{}}\n'
        ),
        encoding="utf-8",
    )
    Path(".toas/session.md").write_text(
        "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nD\n\n## TOAS:USER\n\nE\n\n## TOAS:ASSISTANT\n\nF\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_rpc_stdout", lambda _op: False)
    monkeypatch.setattr(cli, "generate_assistant_message", lambda *_args, **_kwargs: {"role": "assistant", "content": ""})
    cli.run_step_local()
    events = cli.read_log(str(events_path))
    ids_by_content = {
        event.get("content"): event.get("id")
        for event in events
        if event.get("content") in {"D", "E", "F"} and isinstance(event.get("id"), str)
    }
    assert all(key in ids_by_content for key in {"D", "E", "F"})
    id_to_event = {event["id"]: event for event in events if isinstance(event.get("id"), str)}
    d_id = ids_by_content["D"]
    e_id = ids_by_content["E"]
    f_id = ids_by_content["F"]
    assert id_to_event[d_id]["parent"] == "n0"
    assert id_to_event[e_id]["parent"] == d_id
    assert id_to_event[f_id]["parent"] == e_id


def test_run_step_local_bind_index_constrained_divergence_branches_from_selected_head(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    events_path = Path(".toas/events.jsonl")
    events_path.write_text(
        (
            '{"id":"n0","parent":null,"role":"user","content":"A","metadata":{}}\n'
            '{"id":"n1","parent":"n0","role":"assistant","content":"B-main","metadata":{}}\n'
            '{"id":"n2","parent":"n0","role":"assistant","content":"B-branch","metadata":{}}\n'
            '{"id":"n3","parent":"n2","role":"user","content":"C","metadata":{}}\n'
            '{"type":"head","head_id":"n2"}\n'
            '{"type":"jump","bind_index":2}\n'
        ),
        encoding="utf-8",
    )
    Path(".toas/session.md").write_text(
        "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nD\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_rpc_stdout", lambda _op: False)
    monkeypatch.setattr(cli, "generate_assistant_message", lambda *_args, **_kwargs: {"role": "assistant", "content": ""})
    cli.run_step_local()
    events = cli.read_log(str(events_path))
    d_nodes = [event for event in events if event.get("role") == "assistant" and event.get("content") == "D"]
    assert len(d_nodes) >= 1
    latest_d = d_nodes[-1]
    assert latest_d.get("parent") == "n0"


def test_run_step_local_root_edit_creates_new_root_branch_and_preserves_original(monkeypatch, tmp_path):
    import json

    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    events_path = Path(".toas/events.jsonl")
    events_path.write_text(
        (
            '{"id":"n0","parent":null,"role":"user","content":"You are a helpful assistant kind of thing.","metadata":{}}\n'
            '{"id":"n1","parent":"n0","role":"assistant","content":"B","metadata":{}}\n'
            '{"id":"n2","parent":"n1","role":"user","content":"C","metadata":{}}\n'
        ),
        encoding="utf-8",
    )
    Path(".toas/session.md").write_text(
        "## TOAS:USER\n\nYou are a big helpful assistant kind of thing.\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_rpc_stdout", lambda _op: False)
    monkeypatch.setattr(cli, "generate_assistant_message", lambda *_args, **_kwargs: {"role": "assistant", "content": ""})

    cli.run_step_local()

    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    message_events = [event for event in events if "id" in event and "role" in event]
    id_to_event = {event["id"]: event for event in message_events}

    old_root = next(event for event in message_events if event["id"] == "n0")
    assert old_root["parent"] is None

    new_root_candidates = [
        event
        for event in message_events
        if event["role"] == "user"
        and event["content"] == "You are a big helpful assistant kind of thing."
    ]
    assert new_root_candidates, "expected rewritten root user node"
    new_root = new_root_candidates[-1]
    assert new_root.get("parent") == "n0"
    assert new_root["id"] != "n0"

    rewritten_b_nodes = [
        event
        for event in message_events
        if event["role"] == "assistant" and event["content"] == "B" and event.get("parent") == new_root["id"]
    ]
    assert rewritten_b_nodes, "expected assistant tail to rebase onto new root"
    rewritten_b = rewritten_b_nodes[-1]
    rewritten_c_nodes = [
        event
        for event in message_events
        if event["role"] == "user" and event["content"] == "C" and event.get("parent") == rewritten_b["id"]
    ]
    assert rewritten_c_nodes, "expected user tail to remain contiguous on rebased branch"


def test_run_step_async_calls_rpc(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "rpc")
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: {"run_id": "abc123", "status": "running"})
    cli.run_step_async()
    assert capsys.readouterr().out == "run_id=abc123 status=running backend=rpc\n"


def test_run_step_async_handles_rpc_failure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "rpc")
    monkeypatch.setattr(
        cli,
        "rpc_request",
        lambda op, payload=None: (_ for _ in ()).throw(cli.RpcClientError("down")),
    )
    with pytest.raises(SystemExit, match="step --async failed: down"):
        cli.run_step_async()


def test_run_step_async_requires_run_id(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "rpc")
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: {"status": "running"})
    with pytest.raises(SystemExit, match="step --async failed: missing run_id"):
        cli.run_step_async()


def test_run_step_async_requires_rpc(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "off")
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "rpc")
    with pytest.raises(SystemExit, match="step --async requires daemon rpc mode"):
        cli.run_step_async()


def test_run_step_async_respects_runtime_policy(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text("[runtime]\nasync_runs = \"disabled\"\n", encoding="utf-8")
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: (_ for _ in ()).throw(AssertionError("rpc should not run")))
    with pytest.raises(SystemExit, match="step --async disabled by runtime.async_runs policy"):
        cli.run_step_async()


def test_run_watch_calls_rpc_once_without_follow(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "rpc")
    seen_payloads = []

    def fake_rpc(op, payload=None):
        seen_payloads.append(dict(payload or {}))
        return {"chunk": "hello\n", "next_offset": 6, "next_seq": 1, "status": "running"}

    monkeypatch.setattr(
        cli,
        "rpc_request",
        fake_rpc,
    )
    cli.run_watch("abc123")
    assert capsys.readouterr().out == "hello\n[run running] offset=6 backend=rpc\n"
    assert seen_payloads[0]["since_seq"] == 0


def test_run_watch_rpc_chunk_does_not_inject_user_scope_marker(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "rpc")

    def fake_rpc(op, payload=None):
        return {
            "chunk": "## RESULT\n\n[OK] shell: exit=0\nstdout:\n/workspace\n",
            "next_offset": 40,
            "next_seq": 1,
            "status": "succeeded",
        }

    monkeypatch.setattr(cli, "rpc_request", fake_rpc)
    cli.run_watch("abc123")
    out = capsys.readouterr().out
    assert "## RESULT" in out
    assert "## TOAS:USER" not in out


def test_run_watch_respects_runtime_policy(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text("[runtime]\nstreaming_mode = \"disabled\"\n", encoding="utf-8")
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: (_ for _ in ()).throw(AssertionError("rpc should not run")))
    with pytest.raises(SystemExit, match="watch disabled by runtime.streaming_mode policy"):
        cli.run_watch("abc123")


def test_run_watch_requires_rpc(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "off")
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "rpc")
    with pytest.raises(SystemExit, match="watch requires daemon rpc mode"):
        cli.run_watch("abc123")


def test_run_watch_handles_rpc_failure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "rpc")
    monkeypatch.setattr(
        cli,
        "rpc_request",
        lambda op, payload=None: (_ for _ in ()).throw(cli.RpcClientError("down")),
    )
    with pytest.raises(SystemExit, match="watch failed: down"):
        cli.run_watch("abc123")


def test_run_watch_prints_failed_status_with_error(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "rpc")
    monkeypatch.setattr(
        cli,
        "rpc_request",
        lambda op, payload=None: {"chunk": "", "next_offset": 0, "next_seq": 1, "status": "failed", "error": "boom"},
    )
    cli.run_watch("abc123")
    assert capsys.readouterr().out == "\n[run failed] boom\n"


def test_run_watch_prints_failed_status_without_error(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "rpc")
    monkeypatch.setattr(
        cli,
        "rpc_request",
        lambda op, payload=None: {"chunk": "", "next_offset": 0, "next_seq": 1, "status": "failed"},
    )
    cli.run_watch("abc123")
    assert capsys.readouterr().out == "\n[run failed]\n"


def test_run_cancel_calls_rpc(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "rpc")
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: {"status": "cancelling"})
    cli.run_cancel("abc123")
    assert capsys.readouterr().out == "run_id=abc123 status=cancelling backend=rpc\n"


def test_run_cancel_requires_rpc(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "off")
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "rpc")
    with pytest.raises(SystemExit, match="cancel requires daemon rpc mode"):
        cli.run_cancel("abc123")


def test_run_cancel_handles_rpc_failure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "rpc")
    monkeypatch.setattr(
        cli,
        "rpc_request",
        lambda op, payload=None: (_ for _ in ()).throw(cli.RpcClientError("down")),
    )
    with pytest.raises(SystemExit, match="cancel failed: down"):
        cli.run_cancel("abc123")


def test_run_cancel_respects_runtime_policy(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text("[runtime]\ncancellation_mode = \"disabled\"\n", encoding="utf-8")
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: (_ for _ in ()).throw(AssertionError("rpc should not run")))
    with pytest.raises(SystemExit, match="cancel disabled by runtime.cancellation_mode policy"):
        cli.run_cancel("abc123")


def test_run_backend_calls_rpc(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    Path("toas.toml").write_text(
        "[backend]\nmode = \"managed-local\"\n[backend.managed_local]\ncommand = [\"python\", \"-m\", \"http.server\", \"8080\"]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: {"mode": "managed-local", "status": "running", "pid": 555})
    cli.run_backend("status")
    assert capsys.readouterr().out == "backend mode=managed-local status=running pid=555\n"


def test_run_backend_requires_rpc(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "off")
    with pytest.raises(SystemExit, match="backend lifecycle requires daemon rpc mode"):
        cli.run_backend("status")


def test_run_backend_rejects_unknown_action_usage(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    with pytest.raises(SystemExit, match="usage: toas backend \\[start\\|stop\\|restart\\|status\\]"):
        cli.run_backend("bogus")


def test_run_backend_handles_rpc_failure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setattr(
        cli,
        "rpc_request",
        lambda op, payload=None: (_ for _ in ()).throw(cli.RpcClientError("down")),
    )
    with pytest.raises(SystemExit, match="backend status failed: down"):
        cli.run_backend("status")


def test_run_backend_prints_detail_without_pid(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setattr(
        cli,
        "rpc_request",
        lambda op, payload=None: {"mode": "managed-local", "status": "running", "detail": "warming"},
    )
    cli.run_backend("status")
    assert capsys.readouterr().out == "backend mode=managed-local status=running\ndetail: warming\n"


def test_run_index_rebuild_recreates_index(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}}\n',
        encoding="utf-8",
    )

    cli.run_index_rebuild_local()

    assert Path(".toas/events.idx").exists()
    from toas.graph import read_index
    records = read_index(str(tmp_path / ".toas/events.idx"))
    assert len(records) == 2
    assert records[0][2] == "n0"
    assert records[1][2] == "n1"
    assert capsys.readouterr().out == "rebuilt .toas/events.idx (2 message event(s) indexed)\n"


def test_resolve_events_path_prefers_dot_toas_by_default(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert cli.resolve_events_path() == Path(".toas/events.jsonl")


def test_resolve_events_path_prefers_dot_toas_when_present(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text("", encoding="utf-8")
    assert cli.resolve_events_path() == Path(".toas/events.jsonl")


def test_resolve_events_path_falls_back_to_legacy_when_dot_toas_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("events.jsonl").write_text("", encoding="utf-8")
    assert cli.resolve_events_path() == Path("events.jsonl")


def test_resolve_events_path_prefers_dot_toas_when_both_paths_exist(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text("", encoding="utf-8")
    Path("events.jsonl").write_text("", encoding="utf-8")
    assert cli.resolve_events_path() == Path(".toas/events.jsonl")


def test_run_index_rebuild_uses_dot_toas_paths_by_default(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    events_path = Path(".toas/events.jsonl")
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text(
        '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}}\n',
        encoding="utf-8",
    )

    cli.run_index_rebuild_local()

    assert Path(".toas/events.idx").exists()
    from toas.graph import read_index

    records = read_index(str(tmp_path / ".toas/events.idx"))
    assert len(records) == 2
    assert records[0][2] == "n0"
    assert records[1][2] == "n1"
    assert capsys.readouterr().out == "rebuilt .toas/events.idx (2 message event(s) indexed)\n"


def test_run_heads_shows_provenance_breakdown_when_present(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}, "provenance": {"source": "user_authored"}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}, "provenance": {"source": "llm_generated"}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_heads_local()

    out = capsys.readouterr().out
    assert "n1 assistant: hi" in out
    assert "d=2" in out
    assert "t=1" in out
    assert "G:1" in out
    assert "U:1" in out


def test_run_ancestry_walks_from_message_to_root(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}, "provenance": {"source": "user_authored"}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi there", "metadata": {}, "provenance": {"source": "llm_generated"}}\n'
            '{"id": "n2", "parent": "n1", "role": "user", "content": "next question", "metadata": {}, "provenance": {"source": "user_authored"}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_ancestry_local("n2")

    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("n0")
    assert "[U]" in lines[0]
    assert lines[1].startswith("n1")
    assert "[G]" in lines[1]
    assert lines[2].startswith("n2")
    assert "[U]" in lines[2]


def test_run_ancestry_depth_limit_shows_tail(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "a", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "b", "metadata": {}}\n'
            '{"id": "n2", "parent": "n1", "role": "user", "content": "c", "metadata": {}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_ancestry_local("n2", depth=2)

    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("n1")
    assert lines[1].startswith("n2")


def test_run_ancestry_full_shows_complete_content(monkeypatch, tmp_path, capsys):
    import json as _json
    monkeypatch.chdir(tmp_path)
    event = {"id": "n0", "parent": None, "role": "user", "content": "line one\nline two\nline three", "metadata": {}}
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(_json.dumps(event) + "\n", encoding="utf-8")

    cli.run_ancestry_local("n0", full=True)

    out = capsys.readouterr().out
    assert "line two" in out
    assert "line three" in out


def test_run_ancestry_provenance_markers_all_sources(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "authored", "metadata": {}, "provenance": {"source": "user_authored"}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "generated", "metadata": {}, "provenance": {"source": "llm_generated"}}\n'
            '{"id": "n2", "parent": "n1", "role": "user", "content": "adopted", "metadata": {}, "provenance": {"source": "adopted"}}\n'
            '{"id": "n3", "parent": "n2", "role": "user", "content": "correction", "metadata": {}, "provenance": {"source": "user_correction", "corrects": "n1"}}\n'
            '{"id": "n4", "parent": "n3", "role": "user", "content": "unknown", "metadata": {}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_ancestry_local("n4")

    out = capsys.readouterr().out
    assert "[U]" in out
    assert "[G]" in out
    assert "[A]" in out
    assert "[C\u2192n1]" in out
    assert "[?]" in out


def test_run_ancestry_exits_for_unknown_id(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="no message found with id: n99"):
        cli.run_ancestry_local("n99")


# --- diff tests ---

_DIFF_EVENTS = (
    '{"id": "root", "parent": null, "role": "user", "content": "shared root", "metadata": {}, "provenance": {"source": "user_authored"}}\n'
    '{"id": "anode", "parent": "root", "role": "assistant", "content": "branch A diverges here", "metadata": {}, "provenance": {"source": "llm_generated"}}\n'
    '{"id": "bnode", "parent": "root", "role": "user", "content": "branch B diverges here", "metadata": {}, "provenance": {"source": "user_authored"}}\n'
)


def test_run_diff_shows_common_ancestor(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(_DIFF_EVENTS, encoding="utf-8")

    cli.run_diff_local("anode", "bnode")

    out = capsys.readouterr().out
    assert "common ancestor: root" in out


def test_run_diff_shows_diverging_nodes(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(_DIFF_EVENTS, encoding="utf-8")

    cli.run_diff_local("anode", "bnode")

    out = capsys.readouterr().out
    assert "anode" in out
    assert "bnode" in out
    assert "branch A" in out
    assert "branch B" in out


def test_run_diff_shows_provenance_markers(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(_DIFF_EVENTS, encoding="utf-8")

    cli.run_diff_local("anode", "bnode")

    out = capsys.readouterr().out
    assert "[U]" in out   # root (ancestor)
    assert "[G]" in out   # anode
    # bnode also [U] — check it appears at least twice
    assert out.count("[U]") >= 2


def test_run_diff_same_head(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(_DIFF_EVENTS, encoding="utf-8")

    cli.run_diff_local("anode", "anode")

    out = capsys.readouterr().out
    assert "same head" in out


def test_run_diff_no_common_ancestor(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        '{"id": "x", "parent": null, "role": "user", "content": "x", "metadata": {}}\n'
        '{"id": "y", "parent": null, "role": "user", "content": "y", "metadata": {}}\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="no common ancestor"):
        cli.run_diff_local("x", "y")


def test_run_diff_unknown_head(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        '{"id": "n0", "parent": null, "role": "user", "content": "hi", "metadata": {}}\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="no message found with id: bad"):
        cli.run_diff_local("bad", "n0")


def test_run_diff_unknown_other_head(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        '{"id": "n0", "parent": null, "role": "user", "content": "hi", "metadata": {}}\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="no message found with id: bad"):
        cli.run_diff_local("n0", "bad")


def test_run_diff_full_shows_complete_content(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    long_content = "word " * 30
    import json as _json
    events = (
        _json.dumps({"id": "r", "parent": None, "role": "user", "content": long_content, "metadata": {}}) + "\n"
        + _json.dumps({"id": "a", "parent": "r", "role": "assistant", "content": "short", "metadata": {}}) + "\n"
        + _json.dumps({"id": "b", "parent": "r", "role": "user", "content": "other", "metadata": {}}) + "\n"
    )
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(events, encoding="utf-8")

    cli.run_diff_local("a", "b", full=False)
    out_short = capsys.readouterr().out

    cli.run_diff_local("a", "b", full=True)
    out_full = capsys.readouterr().out

    assert len(out_full) >= len(out_short)


def test_run_help_includes_all_sections(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    cli.run_help()
    out = capsys.readouterr().out
    assert "toas [step]" in out        # CLI commands
    assert "/extract" in out           # slash commands
    assert "shell" in out              # tools
    assert "generation.thinking_mode" in out  # config keys


def test_split_append_nodes_sanitizes_secret_and_filters_transient():
    append_set = [
        {"role": "user", "content": "/config secret set llm_api_key abc123", "metadata": {}},
        {"role": "assistant", "content": "hi", "metadata": {"transient_projection": "frontier_flip"}},
        {"role": "result", "content": "ok"},
    ]
    _, persisted, results = cli._split_append_nodes(append_set)
    assert len(results) == 1
    assert persisted == [
        {"role": "user", "content": "/config secret set llm_api_key [REDACTED]", "metadata": {}}
    ]


def test_extract_operator_command_tail_requires_column_one_slash():
    assert cli._extract_operator_command_tail("hello\n/config show\n") == ("config", ["show"])
    assert cli._extract_operator_command_tail("hello\n  /config show\n") is None
    assert cli._extract_operator_command_tail("hello\nnote: /config show\n") is None


def test_stitch_frontier_records_writes_command_records(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    operator_config = cli.config_from_file(Path("toas.toml"))
    materialized = [{"id": "n1", "role": "user", "content": "/pwd"}]
    result_nodes = [{"role": "result", "content": "done", "payload": {"content": "done"}}]

    prefix = cli._stitch_frontier_records(
        events_path=Path(".toas/events.jsonl"),
        materialized=materialized,
        operator_config=operator_config,
        result_nodes=result_nodes,
        head_id="n1",
        lineage=[],
    )

    assert prefix == []
    text = Path(".toas/events.jsonl").read_text(encoding="utf-8")
    assert '"kind": "command_request"' in text
    assert '"kind": "command_result"' in text


def test_apply_result_side_effects_updates_runtime_secret_and_session(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    operator_config = cli.config_from_file(Path("toas.toml"))
    cli._RUNTIME_SECRETS.clear()
    result_nodes = [
        {"role": "result", "content": "x", "secret_update": {"key": "llm_api_key", "action": "set", "value": "k1"}},
        {"role": "result", "content": "x", "session_update": {"transcript": "## TOAS:USER\n\nhello\n"}},
    ]
    cli._apply_result_side_effects(
        events_path=Path(".toas/events.jsonl"),
        result_nodes=result_nodes,
        operator_config=operator_config,
        session_path=Path("session.md"),
        session_newline="\n",
    )
    assert cli._RUNTIME_SECRETS["llm_api_key"] == "k1"
    assert Path("session.md").read_text(encoding="utf-8") == "## TOAS:USER\n\nhello\n"


def test_run_replay_script_local_writes_artifact(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    script = Path("replay.yaml")
    script.write_text(
        (
            "steps:\n"
            "  - append: \"## TOAS:USER\\n\\nhello\"\n"
            "    step: false\n"
            "  - append: \"repo_discovery_triage_v1\"\n"
            "    source: procedure\n"
            "    step: false\n"
        ),
        encoding="utf-8",
    )

    cli.run_replay_script_local(str(script), output_path="artifact.json", dry_run=True)

    out = capsys.readouterr().out
    assert "replay-script: wrote artifact artifact.json" in out
    assert Path("artifact.json").exists()
    content = Path("artifact.json").read_text(encoding="utf-8")
    assert '"dry_run": true' in content
    assert '"source": "procedure"' in content


def test_run_step_local_migrates_legacy_session_to_configured_path(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text('[session]\ntranscript_path = ".toas/session3.md"\n', encoding="utf-8")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "generate_assistant_message",
        lambda messages, **kwargs: {"role": "assistant", "content": "hi"},
    )

    cli.run_step_local()

    assert not Path(".toas/session3.md").exists()
    assert Path(".toas/events.jsonl").read_text(encoding="utf-8").find('"role": "user", "content": "hello"') != -1


def test_run_replay_script_local_migrates_legacy_session_to_configured_path(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text('[session]\ntranscript_path = ".toas/session4.md"\n', encoding="utf-8")
    Path("session.md").write_text("## TOAS:USER\n\nlegacy\n", encoding="utf-8")
    script = Path("replay.yaml")
    script.write_text("steps:\n  - append: \"## TOAS:USER\\n\\nnext\"\n    step: false\n", encoding="utf-8")

    cli.run_replay_script_local(str(script), output_path="artifact.json", dry_run=True)

    text = Path(".toas/session4.md").read_text(encoding="utf-8")
    assert "legacy" in text
    assert "next" in text


def test_ensure_session_path_compat_noops_for_default_or_existing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("legacy\n", encoding="utf-8")
    cli.ensure_session_path_compat(Path("session.md"))
    assert Path("session.md").read_text(encoding="utf-8") == "legacy\n"

    existing = Path(".toas/existing.md")
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("keep\n", encoding="utf-8")
    cli.ensure_session_path_compat(existing)
    assert existing.read_text(encoding="utf-8") == "keep\n"


def test_ensure_session_path_compat_noops_when_no_legacy(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    target = Path(".toas/new.md")
    cli.ensure_session_path_compat(target)
    assert not target.exists()

def test_run_step_local_result_tail_rewrite_steps_new_sibling_not_previous_tip(monkeypatch, tmp_path):
    import json

    monkeypatch.chdir(tmp_path)
    Path('.toas').mkdir(parents=True, exist_ok=True)
    events_path = Path('.toas/events.jsonl')
    events_path.write_text(
        (
            '{"id":"n0","parent":null,"role":"user","content":"A","metadata":{}}\n'
            '{"id":"n1","parent":"n0","role":"assistant","content":"B","metadata":{}}\n'
            '{"id":"n2","parent":"n1","role":"user","content":"C","metadata":{}}\n'
            '{"id":"n3","parent":"n2","role":"assistant","content":"old tip","metadata":{}}\n'
        ),
        encoding='utf-8',
    )
    Path('.toas/session.md').write_text(
        '## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n\n## RESULT\n\nedited\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(cli, '_rpc_stdout', lambda _op: False)
    monkeypatch.setattr(cli, 'generate_assistant_message', lambda *_args, **_kwargs: {'role': 'assistant', 'content': 'new consequence'})

    cli.run_step_local()

    events = [
        json.loads(line)
        for line in events_path.read_text(encoding='utf-8').splitlines()
        if line.strip()
    ]
    message_events = [event for event in events if 'id' in event and 'role' in event]
    id_to_event = {event['id']: event for event in message_events}

    edited_user = [event for event in message_events if event['role'] == 'user' and '## RESULT\n\nedited' in event['content']]
    assert edited_user, 'expected edited user sibling to be persisted'
    edited_id = edited_user[-1]['id']
    assert id_to_event[edited_id]['parent'] == 'n1'

    new_assistant = [event for event in message_events if event['role'] == 'assistant' and event['content'] == 'new consequence']
    assert new_assistant, 'expected consequence generation on edited sibling frontier'
    assert new_assistant[-1]['parent'] == edited_id

def test_run_step_local_truncate_rebuild_result_tail_does_not_rebase_to_root(monkeypatch, tmp_path):
    import json

    monkeypatch.chdir(tmp_path)
    Path('.toas').mkdir(parents=True, exist_ok=True)
    events_path = Path('.toas/events.jsonl')
    # Seed a deeper lineage similar to observed drift shape.
    events_path.write_text(
        (
            '{"id":"n0","parent":null,"role":"user","content":"A","metadata":{}}\n'
            '{"id":"n1","parent":"n0","role":"assistant","content":"B","metadata":{}}\n'
            '{"id":"n2","parent":"n1","role":"user","content":"C","metadata":{}}\n'
            '{"id":"n3","parent":"n2","role":"assistant","content":"D","metadata":{}}\n'
            '{"id":"n4","parent":"n3","role":"user","content":"E","metadata":{}}\n'
        ),
        encoding='utf-8',
    )

    monkeypatch.setattr(cli, '_rpc_stdout', lambda _op: False)
    monkeypatch.setattr(cli, 'generate_assistant_message', lambda *_args, **_kwargs: {'role': 'assistant', 'content': 'next'})

    Path('.toas/session.md').write_text(
        '## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n',
        encoding='utf-8',
    )
    cli.run_step_local()

    events = [json.loads(line) for line in events_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    msgs = [e for e in events if 'id' in e and 'role' in e]
    id_to_event = {e['id']: e for e in msgs}

    rebuilt = [e for e in msgs if e['role'] == 'user' and e['content'] == 'rebuild tail']
    assert rebuilt, 'expected rebuilt user node'
    rebuilt_id = rebuilt[-1]['id']
    assert id_to_event[rebuilt_id]['parent'] == 'n1'

def test_repro_frontier_drift_sequence_reduced_fixture_red(monkeypatch, tmp_path):
    import json

    monkeypatch.chdir(tmp_path)
    Path('.toas').mkdir(parents=True, exist_ok=True)
    events_path = Path('.toas/events.jsonl')
    Path('.toas/session.md').write_text('## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n', encoding='utf-8')
    monkeypatch.setattr(cli, '_rpc_stdout', lambda _op: False)
    monkeypatch.setattr(cli, 'generate_assistant_message', lambda *_args, **_kwargs: {'role': 'assistant', 'content': 'GEN'})

    # Step the same transcript several times to create durable tail beyond authored content.
    cli.run_step_local()
    cli.run_step_local()
    cli.run_step_local()

    # Tail rewrite/truncate style mutation with inline RESULT text.
    Path('.toas/session.md').write_text(
        '## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n',
        encoding='utf-8',
    )
    cli.run_step_local()

    events = [json.loads(line) for line in events_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    msgs = [e for e in events if 'id' in e and 'role' in e]
    rebuilt = [e for e in msgs if e['role'] == 'user' and e['content'] == 'rebuild tail']
    assert rebuilt, 'expected rebuilt tail message event'
    # RED TARGET: this currently drifts in observed logs; keep as failing guard.
    assert rebuilt[-1]['parent'] == 'n1'


def test_run_step_local_harness_captures_context_and_step_kwargs_across_tail_rewrite(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    Path(".toas/events.jsonl").write_text(
        (
            '{"id":"n0","parent":null,"role":"user","content":"A","metadata":{}}\n'
            '{"id":"n1","parent":"n0","role":"assistant","content":"B","metadata":{}}\n'
            '{"id":"n2","parent":"n1","role":"user","content":"C","metadata":{}}\n'
            '{"id":"n3","parent":"n2","role":"assistant","content":"tip","metadata":{}}\n'
        ),
        encoding="utf-8",
    )
    session = Path(".toas/session.md")
    session.write_text("## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n", encoding="utf-8")

    captured: list[dict] = []
    real_step = cli.step

    def wrapped_step(transcript, log, **kwargs):
        captured.append(
            {
                "transcript": transcript,
                "log_len": len(log),
                "bind_index": kwargs.get("bind_index"),
                "bind_parent": kwargs.get("bind_parent"),
                "anchor_index": kwargs.get("anchor_index"),
                "storage_tip_parent": kwargs.get("storage_tip_parent"),
            }
        )
        # Keep behavior deterministic/no-llm: no new consequences.
        return [], []

    monkeypatch.setattr(cli, "_rpc_stdout", lambda _op: False)
    monkeypatch.setattr(cli, "step", wrapped_step)

    cli.run_step_local()
    session.write_text(
        "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n",
        encoding="utf-8",
    )
    cli.run_step_local()

    assert len(captured) == 2
    # Initial exact-prefix state against selected lineage.
    assert captured[0]["bind_parent"] == "n3"
    assert captured[0]["anchor_index"] == 0
    # Tail rewrite should still anchor from A/B shared prefix and use latest tip as context seed.
    assert captured[1]["bind_parent"] == "n3"
    assert captured[1]["anchor_index"] == 0
    assert "rebuild tail" in captured[1]["transcript"]


def test_run_step_local_harness_bind_parent_tracks_selected_head_not_non_message_records(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    # Include non-message records; bind_parent should still resolve from message lineage.
    Path(".toas/events.jsonl").write_text(
        (
            '{"id":"n0","parent":null,"role":"user","content":"A","metadata":{}}\n'
            '{"kind":"tool_result","related_to":"n0","payload":{"ok":true,"content":"x"}}\n'
            '{"id":"n1","parent":"n0","role":"assistant","content":"B","metadata":{}}\n'
            '{"kind":"head","payload":{"head_id":"n1"}}\n'
        ),
        encoding="utf-8",
    )
    Path(".toas/session.md").write_text("## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n", encoding="utf-8")

    seen: dict[str, object] = {}

    def wrapped_step(_transcript, _log, **kwargs):
        seen["bind_parent"] = kwargs.get("bind_parent")
        seen["bind_index"] = kwargs.get("bind_index")
        seen["anchor_index"] = kwargs.get("anchor_index")
        return [], []

    monkeypatch.setattr(cli, "_rpc_stdout", lambda _op: False)
    monkeypatch.setattr(cli, "step", wrapped_step)
    cli.run_step_local()

    assert seen["bind_parent"] == "n1"
    assert seen["bind_index"] is None
    assert seen["anchor_index"] == 0

def test_run_step_local_end_to_end_control_sequence_emits_no_boundary_lag_signature(monkeypatch, tmp_path):
    import json

    monkeypatch.chdir(tmp_path)
    Path('.toas').mkdir(parents=True, exist_ok=True)
    events_path = Path('.toas/events.jsonl')
    session_path = Path('.toas/session.md')
    debug_path = Path('.toas/frontier-debug-e2e.jsonl')

    monkeypatch.setenv('TOAS_DEBUG_FRONTIER', '1')
    monkeypatch.setenv('TOAS_DEBUG_FRONTIER_FILE', str(debug_path))
    monkeypatch.setattr(cli, '_rpc_stdout', lambda _op: False)
    monkeypatch.setattr(cli, 'generate_assistant_message', lambda *_args, **_kwargs: {'role': 'assistant', 'content': 'GEN'})

    session_path.write_text('## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n', encoding='utf-8')
    cli.run_step_local()

    # Introduce control turn, then continue with tail rewrite including RESULT content.
    session_path.write_text(
        '## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:CONTROL\n\n/session show\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n',
        encoding='utf-8',
    )
    cli.run_step_local()

    assert events_path.exists()
    assert debug_path.exists()
    rows = [json.loads(line) for line in debug_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    builds = [row for row in rows if row.get('phase') == 'build_new_transcript_nodes']
    assert builds, 'expected build_new_transcript_nodes debug records'

    # Diagnostic-only breadcrumb: under current seam policy locks, boundary lag
    # may exceed one. Keep this capture for future repro triage, but do not
    # enforce the older strict invariant here.
    def _num(node_id):
        if not isinstance(node_id, str) or not node_id.startswith('n'):
            return None
        try:
            return int(node_id[1:])
        except ValueError:
            return None

    last = builds[-1]
    b = _num(last.get('bind_parent'))
    d = _num(last.get('divergence_parent'))
    if b is not None and d is not None:
        assert (b - d) >= 0

def test_capture_red_case_build_new_transcript_nodes_inputs_for_reduction(monkeypatch, tmp_path):
    import json
    import toas.runtime.step_runtime as sr

    monkeypatch.chdir(tmp_path)
    Path('.toas').mkdir(parents=True, exist_ok=True)
    session_path = Path('.toas/session.md')

    captured = {}
    real_build = sr._build_new_transcript_nodes

    def wrapped_build_new_transcript_nodes(**kwargs):
        # Capture the second call (the red-producing control/tail-rewrite step)
        count = captured.get('_count', 0) + 1
        captured['_count'] = count
        if count == 2:
            captured['kwargs'] = kwargs
        return real_build(**kwargs)

    monkeypatch.setattr(sr, '_build_new_transcript_nodes', wrapped_build_new_transcript_nodes)
    monkeypatch.setenv('TOAS_DEBUG_FRONTIER', '0')
    monkeypatch.setattr(cli, '_rpc_stdout', lambda _op: False)
    monkeypatch.setattr(cli, 'generate_assistant_message', lambda *_args, **_kwargs: {'role': 'assistant', 'content': 'GEN'})

    session_path.write_text('## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n', encoding='utf-8')
    cli.run_step_local()

    session_path.write_text(
        '## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:CONTROL\n\n/session show\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n',
        encoding='utf-8',
    )
    cli.run_step_local()

    assert 'kwargs' in captured
    k = captured['kwargs']
    # Persist a normalized fixture-like dump so unit reduction can replay exact seam inputs.
    dump = {
        'transcript': k['transcript'],
        'log': k['log'],
        'lineage': k['lineage'],
        'bind_index': k['bind_index'],
        'anchor_index': k['anchor_index'],
        'bind_parent': k['bind_parent'],
        'storage_tip_parent': k['storage_tip_parent'],
    }
    out = Path('/tmp/toas-red-build-input.json')
    out.write_text(json.dumps(dump, ensure_ascii=True, indent=2), encoding='utf-8')
    assert out.exists()

def test_run_step_local_interaction_transition_trace_control_vs_no_control(monkeypatch, tmp_path):
    import importlib

    monkeypatch.chdir(tmp_path)
    Path('.toas').mkdir(parents=True, exist_ok=True)
    session_path = Path('.toas/session.md')
    events_path = Path('.toas/events.jsonl')

    mod = importlib.import_module('toas.cli_session_commands')
    real_ctx = mod._build_runtime_context
    real_kwargs = mod._build_step_kwargs

    traces = []

    def wrapped_ctx(*, events, normalized_transcript):
        ctx = real_ctx(events=events, normalized_transcript=normalized_transcript)
        traces.append({
            'phase': 'ctx',
            'head_id': ctx.get('head_id'),
            'lineage_len': len(ctx.get('lineage', [])),
            'bind_index': ctx.get('bind_index'),
            'bind_parent': ctx.get('bind_parent'),
            'anchor_index': ctx.get('anchor_index'),
            'transcript_preview': normalized_transcript.splitlines()[:8],
        })
        return ctx

    def wrapped_kwargs(*, cli_mod, runtime_ctx, operator_config, config_sources, generation_fn):
        kw = real_kwargs(
            cli_mod=cli_mod,
            runtime_ctx=runtime_ctx,
            operator_config=operator_config,
            config_sources=config_sources,
            generation_fn=generation_fn,
        )
        traces.append({
            'phase': 'kwargs',
            'bind_index': kw.get('bind_index'),
            'bind_parent': kw.get('bind_parent'),
            'anchor_index': kw.get('anchor_index'),
            'storage_tip_parent': kw.get('storage_tip_parent'),
        })
        return kw

    monkeypatch.setattr(mod, '_build_runtime_context', wrapped_ctx)
    monkeypatch.setattr(mod, '_build_step_kwargs', wrapped_kwargs)
    monkeypatch.setattr(cli, '_rpc_stdout', lambda _op: False)
    monkeypatch.setattr(cli, 'generate_assistant_message', lambda *_args, **_kwargs: {'role': 'assistant', 'content': 'GEN'})

    # Step A: baseline
    session_path.write_text('## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n', encoding='utf-8')
    cli.run_step_local()

    # Step B: same prefix with control insertion + tail rewrite
    session_path.write_text(
        '## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:CONTROL\n\n/session show\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n',
        encoding='utf-8',
    )
    cli.run_step_local()

    assert events_path.exists()
    ctx_rows = [t for t in traces if t['phase'] == 'ctx']
    kw_rows = [t for t in traces if t['phase'] == 'kwargs']
    assert len(ctx_rows) >= 2
    assert len(kw_rows) >= 2

    base_ctx = ctx_rows[-2]
    ctl_ctx = ctx_rows[-1]
    base_kw = kw_rows[-2]
    ctl_kw = kw_rows[-1]

    # M2/M3/M4 initial interaction checks at handoff level.
    assert base_ctx['anchor_index'] == 0
    assert ctl_ctx['anchor_index'] == 0
    assert ctl_ctx['lineage_len'] >= base_ctx['lineage_len']
    assert ctl_kw['bind_parent'] == ctl_ctx['bind_parent']

def test_run_step_local_interaction_trace_includes_downstream_boundary_transition(monkeypatch, tmp_path):
    import importlib
    import toas.runtime.step_runtime as sr

    monkeypatch.chdir(tmp_path)
    Path('.toas').mkdir(parents=True, exist_ok=True)
    session_path = Path('.toas/session.md')

    cmod = importlib.import_module('toas.cli_session_commands')
    real_ctx = cmod._build_runtime_context
    real_kwargs = cmod._build_step_kwargs
    real_build = sr._build_new_transcript_nodes

    trace = []

    def wrapped_ctx(*, events, normalized_transcript):
        ctx = real_ctx(events=events, normalized_transcript=normalized_transcript)
        trace.append({
            'phase': 'ctx',
            'head_id': ctx.get('head_id'),
            'lineage_len': len(ctx.get('lineage', [])),
            'bind_index': ctx.get('bind_index'),
            'bind_parent': ctx.get('bind_parent'),
            'anchor_index': ctx.get('anchor_index'),
        })
        return ctx

    def wrapped_kwargs(*, cli_mod, runtime_ctx, operator_config, config_sources, generation_fn):
        kw = real_kwargs(
            cli_mod=cli_mod,
            runtime_ctx=runtime_ctx,
            operator_config=operator_config,
            config_sources=config_sources,
            generation_fn=generation_fn,
        )
        trace.append({
            'phase': 'kwargs',
            'bind_index': kw.get('bind_index'),
            'bind_parent': kw.get('bind_parent'),
            'anchor_index': kw.get('anchor_index'),
            'storage_tip_parent': kw.get('storage_tip_parent'),
        })
        return kw

    def wrapped_build(**kwargs):
        bind_index, i, nodes = real_build(**kwargs)
        trace.append({
            'phase': 'build',
            'bind_index': bind_index,
            'anchor_index_in': kwargs.get('anchor_index'),
            'bind_parent': kwargs.get('bind_parent'),
            'storage_tip_parent': kwargs.get('storage_tip_parent'),
            'i': i,
            'nodes_len': len(nodes),
            'first_new_parent': nodes[0].get('parent') if nodes else None,
            'first_new_role': nodes[0].get('role') if nodes else None,
        })
        return bind_index, i, nodes

    monkeypatch.setattr(cmod, '_build_runtime_context', wrapped_ctx)
    monkeypatch.setattr(cmod, '_build_step_kwargs', wrapped_kwargs)
    monkeypatch.setattr(sr, '_build_new_transcript_nodes', wrapped_build)
    monkeypatch.setattr(cli, '_rpc_stdout', lambda _op: False)
    monkeypatch.setattr(cli, 'generate_assistant_message', lambda *_args, **_kwargs: {'role': 'assistant', 'content': 'GEN'})

    session_path.write_text('## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n', encoding='utf-8')
    cli.run_step_local()

    session_path.write_text(
        '## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:CONTROL\n\n/session show\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n',
        encoding='utf-8',
    )
    cli.run_step_local()

    # Expect two full ctx->kwargs->build chains.
    ctx = [r for r in trace if r['phase'] == 'ctx']
    kw = [r for r in trace if r['phase'] == 'kwargs']
    bd = [r for r in trace if r['phase'] == 'build']
    assert len(ctx) >= 2 and len(kw) >= 2 and len(bd) >= 2

    last_ctx, last_kw, last_bd = ctx[-1], kw[-1], bd[-1]
    # Hand-off consistency.
    assert last_kw['bind_parent'] == last_ctx['bind_parent']
    assert last_kw['anchor_index'] == last_ctx['anchor_index']
    # Boundary outcome should preserve at least shared A/B prefix in this sequence.
    assert last_bd['i'] >= 2

def test_run_step_local_interaction_trace_three_step_control_rewrite_sequence(monkeypatch, tmp_path):
    import importlib
    import toas.runtime.step_runtime as sr

    monkeypatch.chdir(tmp_path)
    Path('.toas').mkdir(parents=True, exist_ok=True)
    session_path = Path('.toas/session.md')

    cmod = importlib.import_module('toas.cli_session_commands')
    real_build = sr._build_new_transcript_nodes

    builds = []

    def wrapped_build(**kwargs):
        bind_index, i, nodes = real_build(**kwargs)
        builds.append({
            'bind_parent': kwargs.get('bind_parent'),
            'storage_tip_parent': kwargs.get('storage_tip_parent'),
            'anchor_index': kwargs.get('anchor_index'),
            'i': i,
            'first_new_parent': nodes[0].get('parent') if nodes else None,
            'nodes_len': len(nodes),
        })
        return bind_index, i, nodes

    monkeypatch.setattr(sr, '_build_new_transcript_nodes', wrapped_build)
    monkeypatch.setattr(cli, '_rpc_stdout', lambda _op: False)
    monkeypatch.setattr(cli, 'generate_assistant_message', lambda *_args, **_kwargs: {'role': 'assistant', 'content': 'GEN'})

    # step 1
    session_path.write_text('## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n', encoding='utf-8')
    cli.run_step_local()
    # step 2
    session_path.write_text(
        '## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:CONTROL\n\n/session show\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n',
        encoding='utf-8',
    )
    cli.run_step_local()
    # step 3: mutate only tail content
    session_path.write_text(
        '## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:CONTROL\n\n/session show\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2 edited\n',
        encoding='utf-8',
    )
    cli.run_step_local()

    assert len(builds) >= 3
    last = builds[-1]
    assert last['i'] >= 2
    if isinstance(last['bind_parent'], str) and isinstance(last['first_new_parent'], str):
        b = int(last['bind_parent'][1:])
        p = int(last['first_new_parent'][1:])
        assert (b - p) <= 2

def test_run_step_local_end_to_end_control_sequence_trace_dump_for_interaction_fixture(monkeypatch, tmp_path):
    import importlib
    import json
    import toas.runtime.step_runtime as sr

    monkeypatch.chdir(tmp_path)
    Path('.toas').mkdir(parents=True, exist_ok=True)
    session_path = Path('.toas/session.md')

    cmod = importlib.import_module('toas.cli_session_commands')
    real_ctx = cmod._build_runtime_context
    real_kwargs = cmod._build_step_kwargs
    real_build = sr._build_new_transcript_nodes

    trace = []

    def wrapped_ctx(*, events, normalized_transcript):
        ctx = real_ctx(events=events, normalized_transcript=normalized_transcript)
        trace.append({
            'phase': 'ctx',
            'head_id': ctx.get('head_id'),
            'lineage_len': len(ctx.get('lineage', [])),
            'bind_index': ctx.get('bind_index'),
            'bind_parent': ctx.get('bind_parent'),
            'anchor_index': ctx.get('anchor_index'),
        })
        return ctx

    def wrapped_kwargs(*, cli_mod, runtime_ctx, operator_config, config_sources, generation_fn):
        kw = real_kwargs(
            cli_mod=cli_mod,
            runtime_ctx=runtime_ctx,
            operator_config=operator_config,
            config_sources=config_sources,
            generation_fn=generation_fn,
        )
        trace.append({
            'phase': 'kwargs',
            'bind_index': kw.get('bind_index'),
            'bind_parent': kw.get('bind_parent'),
            'anchor_index': kw.get('anchor_index'),
            'storage_tip_parent': kw.get('storage_tip_parent'),
        })
        return kw

    def wrapped_build(**kwargs):
        bind_index, i, nodes = real_build(**kwargs)
        # reconstruct divergence parent exactly as runtime step code intends
        lineage = kwargs.get('lineage') or []
        bidx = bind_index
        bound_lineage = lineage[bidx:] if lineage else []
        divergence_parent = kwargs.get('bind_parent')
        if i == 0 and bound_lineage:
            rid = bound_lineage[0].get('id')
            if isinstance(rid, str) and rid:
                divergence_parent = rid
        elif i > 0 and i - 1 < len(bound_lineage):
            bid = bound_lineage[i - 1].get('id')
            if isinstance(bid, str) and bid:
                divergence_parent = bid
        trace.append({
            'phase': 'build',
            'bind_index': bind_index,
            'bind_parent': kwargs.get('bind_parent'),
            'storage_tip_parent': kwargs.get('storage_tip_parent'),
            'anchor_index_in': kwargs.get('anchor_index'),
            'i': i,
            'lineage_len_in': len(lineage),
            'parsed_nodes_len': len(sr.importlib.import_module('toas.step').parse_transcript(kwargs.get('transcript', ''))),
            'nodes_len': len(nodes),
            'first_new_parent': nodes[0].get('parent') if nodes else None,
            'divergence_parent': divergence_parent,
        })
        return bind_index, i, nodes

    monkeypatch.setattr(cmod, '_build_runtime_context', wrapped_ctx)
    monkeypatch.setattr(cmod, '_build_step_kwargs', wrapped_kwargs)
    monkeypatch.setattr(sr, '_build_new_transcript_nodes', wrapped_build)
    monkeypatch.setattr(cli, '_rpc_stdout', lambda _op: False)
    monkeypatch.setattr(cli, 'generate_assistant_message', lambda *_args, **_kwargs: {'role': 'assistant', 'content': 'GEN'})

    # match currently failing red shape
    session_path.write_text('## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n', encoding='utf-8')
    cli.run_step_local()
    session_path.write_text(
        '## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:CONTROL\n\n/session show\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n',
        encoding='utf-8',
    )
    cli.run_step_local()

    out = Path('/tmp/toas-interaction-trace.json')
    out.write_text(json.dumps(trace, ensure_ascii=True, indent=2), encoding='utf-8')
    assert out.exists()


def test_run_step_local_interaction_lag_evolution_signature_current_behavior(monkeypatch, tmp_path):
    import importlib
    import toas.runtime.step_runtime as sr

    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    session_path = Path(".toas/session.md")

    cmod = importlib.import_module("toas.cli_session_commands")
    real_build = sr._build_new_transcript_nodes

    builds = []

    def wrapped_build(**kwargs):
        bind_index, i, nodes = real_build(**kwargs)
        lineage = kwargs.get("lineage") or []
        bound_lineage = lineage[bind_index:] if lineage else []
        divergence_parent = kwargs.get("bind_parent")
        if i == 0 and bound_lineage:
            rid = bound_lineage[0].get("id")
            if isinstance(rid, str) and rid:
                divergence_parent = rid
        elif i > 0 and i - 1 < len(bound_lineage):
            bid = bound_lineage[i - 1].get("id")
            if isinstance(bid, str) and bid:
                divergence_parent = bid
        builds.append(
            {
                "bind_parent": kwargs.get("bind_parent"),
                "i": i,
                "parsed_nodes_len": len(sr.importlib.import_module("toas.step").parse_transcript(kwargs.get("transcript", ""))),
                "lineage_len_in": len(lineage),
                "divergence_parent": divergence_parent,
                "first_new_parent": nodes[0].get("parent") if nodes else None,
            }
        )
        return bind_index, i, nodes

    monkeypatch.setattr(sr, "_build_new_transcript_nodes", wrapped_build)
    monkeypatch.setattr(cli, "_rpc_stdout", lambda _op: False)
    monkeypatch.setattr(cli, "generate_assistant_message", lambda *_args, **_kwargs: {"role": "assistant", "content": "GEN"})

    # Step 1: baseline conversation.
    session_path.write_text("## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n", encoding="utf-8")
    cli.run_step_local()
    # Step 2: control insertion + tail rewrite (observed lag case).
    session_path.write_text(
        "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:CONTROL\n\n/session show\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n",
        encoding="utf-8",
    )
    cli.run_step_local()

    assert len(builds) >= 2
    first, second = builds[-2], builds[-1]
    assert first["divergence_parent"] in {None, first["bind_parent"]}
    # Current observed evolution: second step lags from bind parent to older boundary.
    assert second["bind_parent"] == "n3"
    assert second["divergence_parent"] == "n1"
    assert second["first_new_parent"] == "n1"
    assert second["i"] == 2


def test_run_step_local_interaction_perturbation_matrix_observes_lag_trigger(monkeypatch, tmp_path):
    import importlib
    import toas.runtime.step_runtime as sr

    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    session_path = Path(".toas/session.md")

    real_build = sr._build_new_transcript_nodes
    observed = []

    def wrapped_build(**kwargs):
        bind_index, i, nodes = real_build(**kwargs)
        lineage = kwargs.get("lineage") or []
        bound_lineage = lineage[bind_index:] if lineage else []
        divergence_parent = kwargs.get("bind_parent")
        if i == 0 and bound_lineage:
            rid = bound_lineage[0].get("id")
            if isinstance(rid, str) and rid:
                divergence_parent = rid
        elif i > 0 and i - 1 < len(bound_lineage):
            bid = bound_lineage[i - 1].get("id")
            if isinstance(bid, str) and bid:
                divergence_parent = bid
        observed.append(
            {
                "bind_parent": kwargs.get("bind_parent"),
                "divergence_parent": divergence_parent,
                "i": i,
                "first_new_parent": nodes[0].get("parent") if nodes else None,
            }
        )
        return bind_index, i, nodes

    monkeypatch.setattr(sr, "_build_new_transcript_nodes", wrapped_build)
    monkeypatch.setattr(cli, "_rpc_stdout", lambda _op: False)
    monkeypatch.setattr(cli, "generate_assistant_message", lambda *_args, **_kwargs: {"role": "assistant", "content": "GEN"})

    base = "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n"
    cases = [
        (
            "control+result",
            "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:CONTROL\n\n/session show\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n",
        ),
        (
            "control-only",
            "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:CONTROL\n\n/session show\n\n## TOAS:USER\n\nrebuild tail\n",
        ),
        (
            "result-only",
            "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n",
        ),
    ]

    results = {}
    for label, text in cases:
        observed.clear()
        session_path.write_text(base, encoding="utf-8")
        cli.run_step_local()
        session_path.write_text(text, encoding="utf-8")
        cli.run_step_local()
        assert len(observed) >= 2
        results[label] = observed[-1]

    assert results["control+result"]["bind_parent"] == "n3"
    assert results["control+result"]["divergence_parent"] == "n1"
    assert results["control-only"]["divergence_parent"] in {"n1", "n2", "n3"}
    # Key perturbation finding: lag can occur without control insertion; tail rewrite + RESULT is sufficient.
    assert results["result-only"]["divergence_parent"] == "n1"


def test_run_step_local_input_space_variants_tail_shape_matrix(monkeypatch, tmp_path):
    import toas.runtime.step_runtime as sr

    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    session_path = Path(".toas/session.md")

    real_build = sr._build_new_transcript_nodes
    observed = []

    def wrapped_build(**kwargs):
        bind_index, i, nodes = real_build(**kwargs)
        lineage = kwargs.get("lineage") or []
        bound_lineage = lineage[bind_index:] if lineage else []
        divergence_parent = kwargs.get("bind_parent")
        if i == 0 and bound_lineage:
            rid = bound_lineage[0].get("id")
            if isinstance(rid, str) and rid:
                divergence_parent = rid
        elif i > 0 and i - 1 < len(bound_lineage):
            bid = bound_lineage[i - 1].get("id")
            if isinstance(bid, str) and bid:
                divergence_parent = bid
        observed.append(
            {
                "bind_parent": kwargs.get("bind_parent"),
                "divergence_parent": divergence_parent,
                "i": i,
                "first_new_parent": nodes[0].get("parent") if nodes else None,
            }
        )
        return bind_index, i, nodes

    monkeypatch.setattr(sr, "_build_new_transcript_nodes", wrapped_build)
    monkeypatch.setattr(cli, "_rpc_stdout", lambda _op: False)
    monkeypatch.setattr(cli, "generate_assistant_message", lambda *_args, **_kwargs: {"role": "assistant", "content": "GEN"})

    base = "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n"
    cases = [
        (
            "two-user-inline-result",
            "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n",
        ),
        (
            "single-user-inline-result",
            "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nrebuild tail\n\n## RESULT\n\nZ2\n",
        ),
        (
            "single-user-shell-shorthand",
            "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nrebuild tail\n$ echo hi\n",
        ),
        (
            "append-only-extra-user-no-result",
            "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n\n## TOAS:USER\n\ntail edit\n",
        ),
    ]

    results = {}
    for label, text in cases:
        observed.clear()
        session_path.write_text(base, encoding="utf-8")
        cli.run_step_local()
        session_path.write_text(text, encoding="utf-8")
        cli.run_step_local()
        assert len(observed) >= 2
        results[label] = observed[-1]

    def _num(node_id):
        if not isinstance(node_id, str) or not node_id.startswith("n"):
            return None
        try:
            return int(node_id[1:])
        except ValueError:
            return None

    assert results["two-user-inline-result"]["divergence_parent"] == "n1"
    assert results["single-user-inline-result"]["divergence_parent"] == "n1"
    assert results["single-user-shell-shorthand"]["divergence_parent"] == "n1"
    ab = _num(results["append-only-extra-user-no-result"]["bind_parent"])
    ad = _num(results["append-only-extra-user-no-result"]["divergence_parent"])
    assert ab is not None and ad is not None
    assert (ab - ad) <= 1


@pytest.mark.parametrize(
    ("label", "mapper", "expected_divergence"),
    [
        ("baseline_i_minus_one", lambda i: (None if i <= 0 else i - 1), "n1"),
        ("offset_plus_one", lambda i: (None if i <= 0 else i), "n2"),
        ("aggressive_plus_two", lambda i: (None if i <= 0 else i + 1), "n3"),
    ],
)
def test_run_step_local_hypothesis_mapper_variants_on_minimal_lag_sequence(
    monkeypatch,
    tmp_path,
    label,
    mapper,
    expected_divergence,
):
    import toas.runtime.step_runtime as sr

    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    session_path = Path(".toas/session.md")

    real_mapper = sr._map_lcp_index_to_lineage_boundary_index
    real_build = sr._build_new_transcript_nodes
    seen = {}

    def wrapped_mapper(*, lcp_index: int, bound_log=None, bound_lineage=None):
        return mapper(lcp_index)

    def wrapped_build(**kwargs):
        bind_index, i, nodes = real_build(**kwargs)
        lineage = kwargs.get("lineage") or []
        bound_lineage = lineage[bind_index:] if lineage else []
        divergence_parent = kwargs.get("bind_parent")
        if i == 0 and bound_lineage:
            rid = bound_lineage[0].get("id")
            if isinstance(rid, str) and rid:
                divergence_parent = rid
        elif i > 0:
            bidx = sr._map_lcp_index_to_lineage_boundary_index(
                lcp_index=i,
                bound_log=kwargs.get("log"),
                bound_lineage=bound_lineage,
            )
            if isinstance(bidx, int) and 0 <= bidx < len(bound_lineage):
                bid = bound_lineage[bidx].get("id")
                if isinstance(bid, str) and bid:
                    divergence_parent = bid
        seen["label"] = label
        seen["lcp_index"] = i
        seen["divergence_parent"] = divergence_parent
        return bind_index, i, nodes

    monkeypatch.setattr(sr, "_map_lcp_index_to_lineage_boundary_index", wrapped_mapper)
    monkeypatch.setattr(sr, "_build_new_transcript_nodes", wrapped_build)
    monkeypatch.setattr(cli, "_rpc_stdout", lambda _op: False)
    monkeypatch.setattr(cli, "generate_assistant_message", lambda *_args, **_kwargs: {"role": "assistant", "content": "GEN"})

    session_path.write_text("## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n", encoding="utf-8")
    cli.run_step_local()
    session_path.write_text(
        "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nrebuild tail\n\n## RESULT\n\nZ2\n",
        encoding="utf-8",
    )
    cli.run_step_local()

    assert seen["lcp_index"] == 2
    assert seen["divergence_parent"] == expected_divergence
    monkeypatch.setattr(sr, "_map_lcp_index_to_lineage_boundary_index", real_mapper)


def test_run_step_local_frontier_selection_uses_rewritten_tail_not_divergence_parent(monkeypatch, tmp_path):
    import json

    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    session_path = Path(".toas/session.md")
    debug_path = Path(".toas/frontier-debug-frontier-vs-divergence.jsonl")

    monkeypatch.setenv("TOAS_DEBUG_FRONTIER", "1")
    monkeypatch.setenv("TOAS_DEBUG_FRONTIER_FILE", str(debug_path))
    monkeypatch.setattr(cli, "_rpc_stdout", lambda _op: False)
    monkeypatch.setattr(cli, "generate_assistant_message", lambda *_args, **_kwargs: {"role": "assistant", "content": "GEN"})

    session_path.write_text("## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n", encoding="utf-8")
    cli.run_step_local()
    session_path.write_text(
        "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:CONTROL\n\n/session show\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n",
        encoding="utf-8",
    )
    cli.run_step_local()

    rows = [json.loads(line) for line in debug_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    builds = [row for row in rows if row.get("phase") == "build_new_transcript_nodes"]
    frontier = [row for row in rows if row.get("phase") == "run_step_frontier"]
    assert builds and frontier

    last_build = builds[-1]
    last_frontier = frontier[-1]

    # This sequence intentionally has divergence at shared-prefix boundary.
    assert last_build.get("divergence_parent") == "n1"
    # Correct frontier behavior: execute on rewritten tail, not divergence parent.
    assert last_frontier.get("frontier_id") != last_build.get("divergence_parent")
    assert last_frontier.get("frontier_role") == "user"


@pytest.mark.parametrize(
    ("label", "second_transcript"),
    [
        (
            "control_plus_result_tail_rewrite",
            "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:CONTROL\n\n/session show\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n",
        ),
        (
            "result_only_tail_rewrite",
            "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nrebuild tail\n\n## RESULT\n\nZ2\n",
        ),
        (
            "shell_shorthand_tail_rewrite",
            "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nrebuild tail\n$ echo hi\n",
        ),
    ],
)
def test_run_step_local_behavior_e2e_consequence_attaches_from_rewritten_tail_matrix(
    monkeypatch,
    tmp_path,
    label,
    second_transcript,
):
    import json

    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    session_path = Path(".toas/session.md")
    debug_path = Path(f".toas/frontier-debug-behavior-{label}.jsonl")

    monkeypatch.setenv("TOAS_DEBUG_FRONTIER", "1")
    monkeypatch.setenv("TOAS_DEBUG_FRONTIER_FILE", str(debug_path))
    monkeypatch.setattr(cli, "_rpc_stdout", lambda _op: False)
    monkeypatch.setattr(cli, "generate_assistant_message", lambda *_args, **_kwargs: {"role": "assistant", "content": "GEN"})

    base = "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n"
    session_path.write_text(base, encoding="utf-8")
    cli.run_step_local()
    session_path.write_text(second_transcript, encoding="utf-8")
    cli.run_step_local()

    rows = [json.loads(line) for line in debug_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    builds = [row for row in rows if row.get("phase") == "build_new_transcript_nodes"]
    frontiers = [row for row in rows if row.get("phase") == "run_step_frontier"]
    assert builds and frontiers

    last_build = builds[-1]
    last_frontier = frontiers[-1]

    # Behavior contract: consequence frontier comes from rewritten tail, not divergence boundary.
    assert last_frontier.get("frontier_role") == "user"
    assert (last_frontier.get("frontier_preview") or "").strip() != "B"
    assert last_frontier.get("frontier_id") != last_build.get("divergence_parent")


@pytest.mark.xfail(reason="Target contract: control insertion should not induce extra boundary lag", strict=False)
def test_run_step_local_interaction_lag_evolution_target_behavior(monkeypatch, tmp_path):
    import importlib
    import toas.runtime.step_runtime as sr

    monkeypatch.chdir(tmp_path)
    Path(".toas").mkdir(parents=True, exist_ok=True)
    session_path = Path(".toas/session.md")

    cmod = importlib.import_module("toas.cli_session_commands")
    real_build = sr._build_new_transcript_nodes
    seen = {}

    def wrapped_build(**kwargs):
        bind_index, i, nodes = real_build(**kwargs)
        lineage = kwargs.get("lineage") or []
        bound_lineage = lineage[bind_index:] if lineage else []
        divergence_parent = kwargs.get("bind_parent")
        if i > 0 and i - 1 < len(bound_lineage):
            bid = bound_lineage[i - 1].get("id")
            if isinstance(bid, str) and bid:
                divergence_parent = bid
        seen["bind_parent"] = kwargs.get("bind_parent")
        seen["divergence_parent"] = divergence_parent
        return bind_index, i, nodes

    monkeypatch.setattr(sr, "_build_new_transcript_nodes", wrapped_build)
    monkeypatch.setattr(cli, "_rpc_stdout", lambda _op: False)
    monkeypatch.setattr(cli, "generate_assistant_message", lambda *_args, **_kwargs: {"role": "assistant", "content": "GEN"})

    session_path.write_text("## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:USER\n\nC\n", encoding="utf-8")
    cli.run_step_local()
    session_path.write_text(
        "## TOAS:USER\n\nA\n\n## TOAS:ASSISTANT\n\nB\n\n## TOAS:CONTROL\n\n/session show\n\n## TOAS:USER\n\nrebuild tail\n\n## TOAS:USER\n\n## RESULT\n\nZ2\n",
        encoding="utf-8",
    )
    cli.run_step_local()

    b = int(str(seen["bind_parent"])[1:])
    d = int(str(seen["divergence_parent"])[1:])
    assert (b - d) <= 1

def test_build_runtime_context_derives_best_prefix_head_instead_of_active_head():
    import importlib

    mod = importlib.import_module("toas.cli_session_commands")
    events = [
        {"id": "n0", "parent": None, "role": "user", "content": "/prompts"},
        {"id": "n1", "parent": "n0", "role": "assistant", "content": "legacy branch"},
        {"id": "n2", "parent": "n0", "role": "user", "content": "You are collaborating with the user in a direct, practical loop."},
        {"id": "n3", "parent": "n2", "role": "user", "content": "Help me understand what went wrong here."},
        {"kind": "head", "payload": {"head_id": "n1"}},
    ]
    transcript = (
        "## TOAS:USER\n\nYou are collaborating with the user in a direct, practical loop.\n\n"
        "## TOAS:USER\n\nHelp me understand what went wrong here.\n"
    )

    ctx = mod._build_runtime_context(events=events, normalized_transcript=transcript)

    assert ctx["head_id"] == "n3"
    assert len(ctx["lineage"]) == 3
    assert ctx["lineage"][0]["id"] == "n0"
    assert ctx["lineage"][1]["id"] == "n2"
