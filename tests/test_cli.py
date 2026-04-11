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

    assert Path("session.md").read_text(encoding="utf-8") == ""
    assert Path("events.jsonl").read_text(encoding="utf-8") == ""
    assert calls == {
        "transcript": "",
        "log": [],
        "bind_index": None,
        "bind_parent": None,
        "anchor_index": 0,
        "storage_tip_parent": None,
    }
    assert capsys.readouterr().out == ""


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

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
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

    assert Path("session.md").read_text(encoding="utf-8") == updated
    assert Path("events.jsonl").read_text(encoding="utf-8") == (
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

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"kind": "jump", "payload": {"bind_index": 7}}\n'
    )
    assert capsys.readouterr().out == "bound transcript to node 7\n"


def test_run_head_is_invokable(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    cli.run_head("n7")

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"kind": "head", "payload": {"head_id": "n7"}}\n'
    )
    assert capsys.readouterr().out == "selected head n7\n"


def test_run_heads_lists_known_heads_and_marks_selected(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("events.jsonl").write_text(
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
    Path("events.jsonl").write_text(
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
        assert log == [{"role": "user", "content": "old"}]
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
    Path("events.jsonl").write_text(
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
    Path("events.jsonl").write_text(
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
    Path("events.jsonl").write_text(
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
    Path("events.jsonl").write_text(
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
    Path("events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "branch", "metadata": {}}\n'
            '{"kind": "head", "payload": {"head_id": "n1"}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_rebuild()

    assert Path("session.md").read_text(encoding="utf-8") == "## TOAS:USER\n\nroot\n\n## TOAS:ASSISTANT\n\nbranch\n"
    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "branch", "metadata": {}}\n'
        '{"kind": "head", "payload": {"head_id": "n1"}}\n'
        '{"kind": "anchor", "payload": {"offset": 46, "node_id": "n1"}}\n'
    )
    assert capsys.readouterr().out == "rebuilt session.md from head n1\n"


def test_run_rebuild_avoids_duplicate_equivalent_anchor(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
            '{"kind": "anchor", "payload": {"offset": 19, "node_id": "n0"}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_rebuild()

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
        '{"kind": "anchor", "payload": {"offset": 19, "node_id": "n0"}}\n'
    )
    assert capsys.readouterr().out == "rebuilt session.md from head n0\n"


def test_run_step_derives_bind_parent_from_message_event_space(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    Path("events.jsonl").write_text(
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
            {"role": "user", "content": "root"},
            {"role": "assistant", "content": "old"},
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
    Path("events.jsonl").write_text(
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
    Path("events.jsonl").write_text(
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
        assert log == [{"role": "user", "content": "hello"}]
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

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}}\n'
    )
    assert capsys.readouterr().out == "## TOAS:ASSISTANT\n\nhi\n\n"


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
    assert capsys.readouterr().out == "## TOAS:ASSISTANT\r\n\r\nhi\r\n\r\n"


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
    with Path("session.md").open("r", encoding="utf-8", newline="") as f:
        assert f.read() == "## TOAS:USER\r\n\r\nupdated\r\n"


def test_run_step_uses_real_generation_callback_with_projected_llm_input(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\npart one\n\n## TOAS:USER\n\npart two\n", encoding="utf-8")
    seen = {}
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")

    def fake_generate(messages, *, settings=None, extra_body=None):
        seen["messages"] = messages
        seen["model"] = settings.llm_model
        seen["extra_body"] = extra_body
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
    assert Path("events.jsonl").read_text(encoding="utf-8") == (
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

    def fake_generate(messages, *, settings=None, extra_body=None):
        raise RuntimeError("backend unavailable")

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)

    with pytest.raises(SystemExit, match="llm generation failed after 1 attempt\\(s\\): backend unavailable \\(endpoint="):
        cli.run_step()

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"kind": "llm_call", "payload": {"requested_model": "local-model", "trace_mode": "minimal", "input_count": 1, "error": "backend unavailable (endpoint=http://localhost:8080/v1, endpoint_source=env_or_default, model=local-model, model_source=env_or_default, api_key_source=env:TOAS_LLM_API_KEY, transport_source=default)", "error_class": "transient", "attempt": 1, "max_attempts": 1}}\n'
    )


def test_run_step_retries_transient_llm_failure_then_succeeds(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    Path("toas.toml").write_text("[generation]\nmax_retries = 2\nretry_delay_s = 0\n", encoding="utf-8")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    calls = {"n": 0}

    def fake_generate(messages, *, settings=None, extra_body=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("temporary backend failure")
        return {"role": "assistant", "content": "answer", "response": {"content": "answer", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)

    cli.run_step()

    assert calls["n"] == 2
    assert Path("events.jsonl").read_text(encoding="utf-8") == (
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

    def fake_generate(messages, *, settings=None, extra_body=None):
        seen["settings"] = settings
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

    def fake_generate(messages, *, settings=None, extra_body=None):
        seen["settings"] = settings
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

    def fake_generate(messages, *, settings=None, extra_body=None):
        return {"role": "assistant", "content": "ok", "response": {"content": "ok", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)
    cli.run_step()
    assert '"transport_mode": "single_user_blob"' in Path("events.jsonl").read_text(encoding="utf-8")


def test_run_step_preserves_stream_mode_from_env_settings(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    monkeypatch.setenv("TOAS_LLM_STREAM_MODE", "enabled")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    seen = {}

    def fake_generate(messages, *, settings=None, extra_body=None):
        seen["settings"] = settings
        return {"role": "assistant", "content": "ok", "response": {"content": "ok", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)
    cli.run_step()
    assert seen["settings"].llm_stream_mode == "enabled"


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


def test_run_step_writes_full_llm_trace_when_enabled(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    monkeypatch.setenv("TOAS_LLM_TRACE", "full")
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")

    def fake_generate(messages, *, settings=None, extra_body=None):
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

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}, "provenance": {"source": "user_authored"}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "<think>private</think>\\nanswer", "metadata": {}, "provenance": {"source": "llm_generated"}}\n'
        '{"kind": "llm_call", "payload": {"requested_model": "local-model", "trace_mode": "full", "input_count": 1, "messages": [{"role": "user", "content": "hello"}], "response_model": "model-full", "response": {"content": "<think>private</think>\\nanswer", "reasoning_content": "private chain", "has_reasoning_blocks": true}, "response_has_reasoning_content": true, "attempt": 1, "max_attempts": 1, "message_id": "n1"}}\n'
    )


def test_run_step_projects_assistant_think_blocks_out_of_next_llm_input(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    Path("events.jsonl").write_text(
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

    def fake_generate(messages, *, settings=None, extra_body=None):
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
    Path("events.jsonl").write_text(
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

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
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

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "please run this\\n```yaml\\n- tool_name: echo\\n  args:\\n    text: hi\\n```", "metadata": {}}\n'
        '{"kind": "tool_request", "related_to": "n0", "payload": [{"tool_name": "echo", "args": {"text": "hi"}}]}\n'
        '{"kind": "tool_result", "related_to": "n0", "payload": {"content": "ran echo"}}\n'
    )
    assert capsys.readouterr().out == "## TOAS:USER\n\n\n\n## RESULT\n\nran echo\n\n"


def test_run_step_extract_selection_adopts_user_content_without_tool_execution(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("events.jsonl").write_text(
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

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "assistant", "content": "```yaml\\n- tool_name: echo\\n  args:\\n    text: hi\\n```", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "user", "content": "/extract 1", "metadata": {}}\n'
        '{"id": "n2", "parent": "n1", "role": "user", "content": "```yaml\\n- tool_name: echo\\n  args:\\n    text: hi\\n```", "metadata": {}}\n'
    )
    assert capsys.readouterr().out == "## TOAS:USER\n\n```yaml\n- tool_name: echo\n  args:\n    text: hi\n```\n\n"


def test_run_step_replay_result_writes_tool_records_for_target_message(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("events.jsonl").write_text(
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
    events = Path("events.jsonl").read_text(encoding="utf-8")
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

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
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

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
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

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
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
    events = Path("events.jsonl").read_text(encoding="utf-8")
    assert "supersecret" not in events
    assert "[REDACTED]" in events
    assert "config_override" not in events
    assert "supersecret" not in Path("session.md").read_text(encoding="utf-8")


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
    events = Path("events.jsonl").read_text(encoding="utf-8")
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
    events = Path("events.jsonl").read_text(encoding="utf-8")
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
    Path("events.jsonl").write_text(
        '{"id": "n0", "parent": null, "role": "user", "content": "Scan the directories", "metadata": {}}\n',
        encoding="utf-8",
    )

    cli.run_step()

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
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
    Path("events.jsonl").write_text(
        (
            '{"kind": "command_context", "payload": {"cwd": "'
            + str(workdir)
            + '"}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_step()

    out = capsys.readouterr().out
    assert f"stdout:\n{workdir}" in out


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

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
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

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "/workspace mode unbounded", "metadata": {}}\n'
        '{"kind": "command_request", "payload": {"id": "c1", "command": "workspace", "args": ["mode", "unbounded"]}, "related_to": "n0"}\n'
        '{"kind": "command_result", "payload": {"ok": true, "content": "mode=unbounded", "workspace_update": {"mode": "unbounded", "roots": ["'
        + str(tmp_path)
        + '"]}}, "related_to": "c1"}\n'
        '{"kind": "workspace_scope", "payload": {"mode": "unbounded", "roots": ["'
        + str(tmp_path)
        + '"]}}\n'
    )
    assert capsys.readouterr().out == "## RESULT\n\nmode=unbounded\n\n"


def test_run_step_uses_alignment_anchor_when_transcript_matches_prefix(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\nhello\n\n## TOAS:ASSISTANT\n\nhi\n\n## TOAS:USER\n\nnext\n", encoding="utf-8")
    Path("events.jsonl").write_text(
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
    Path("events.jsonl").write_text(
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
            {"role": "user", "content": "root"},
            {"role": "assistant", "content": "branch"},
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
    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"kind": "jump", "payload": {"bind_index": 2}}\n'
    )


def test_run_step_creates_index_alongside_events(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\nhello\n", encoding="utf-8")
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")

    def fake_generate(messages, *, settings=None, extra_body=None):
        return {"role": "assistant", "content": "hi", "response": {"content": "hi", "model": "m"}}

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)

    cli.run_step()

    assert Path("events.idx").exists()
    # index has one record per message event (user + assistant = 2)
    from toas.graph import INDEX_RECORD_SIZE, read_index
    assert Path("events.idx").stat().st_size == 2 * INDEX_RECORD_SIZE
    records = read_index(str(tmp_path / "events.idx"))
    assert [mid for _, _, mid in records] == ["n0", "n1"]


def test_run_step_transient_frontier_flip_is_not_persisted(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## TOAS:USER\n\nhello\n\n## TOAS:ASSISTANT\n\nhi\n", encoding="utf-8")
    Path("events.jsonl").write_text(
        (
            '{"id":"n0","parent":null,"role":"user","content":"hello","metadata":{}}\n'
            '{"id":"n1","parent":"n0","role":"assistant","content":"hi","metadata":{}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_step_local()

    out = capsys.readouterr().out
    assert "## TOAS:USER" in out
    events_after = Path("events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(events_after) == 2


def test_run_step_async_calls_rpc(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: {"run_id": "abc123", "status": "running"})
    cli.run_step_async()
    assert capsys.readouterr().out == "run_id=abc123 status=running\n"


def test_run_step_async_requires_rpc(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "off")
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
    assert capsys.readouterr().out == "hello\n[run running] offset=6\n"
    assert seen_payloads[0]["since_seq"] == 0


def test_run_watch_respects_runtime_policy(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text("[runtime]\nstreaming_mode = \"disabled\"\n", encoding="utf-8")
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: (_ for _ in ()).throw(AssertionError("rpc should not run")))
    with pytest.raises(SystemExit, match="watch disabled by runtime.streaming_mode policy"):
        cli.run_watch("abc123")


def test_run_cancel_calls_rpc(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_RPC_MODE", "on")
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: {"status": "cancelling"})
    cli.run_cancel("abc123")
    assert capsys.readouterr().out == "run_id=abc123 status=cancelling\n"


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


def test_run_index_rebuild_recreates_index(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("events.jsonl").write_text(
        '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}}\n',
        encoding="utf-8",
    )

    cli.run_index_rebuild_local()

    assert Path("events.idx").exists()
    from toas.graph import read_index
    records = read_index(str(tmp_path / "events.idx"))
    assert len(records) == 2
    assert records[0][2] == "n0"
    assert records[1][2] == "n1"
    assert capsys.readouterr().out == "rebuilt events.idx (2 message event(s) indexed)\n"


def test_run_heads_shows_provenance_breakdown_when_present(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("events.jsonl").write_text(
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
    Path("events.jsonl").write_text(
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
    Path("events.jsonl").write_text(
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
    Path("events.jsonl").write_text(_json.dumps(event) + "\n", encoding="utf-8")

    cli.run_ancestry_local("n0", full=True)

    out = capsys.readouterr().out
    assert "line two" in out
    assert "line three" in out


def test_run_ancestry_provenance_markers_all_sources(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("events.jsonl").write_text(
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
    Path("events.jsonl").write_text(
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
    Path("events.jsonl").write_text(_DIFF_EVENTS, encoding="utf-8")

    cli.run_diff_local("anode", "bnode")

    out = capsys.readouterr().out
    assert "common ancestor: root" in out


def test_run_diff_shows_diverging_nodes(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("events.jsonl").write_text(_DIFF_EVENTS, encoding="utf-8")

    cli.run_diff_local("anode", "bnode")

    out = capsys.readouterr().out
    assert "anode" in out
    assert "bnode" in out
    assert "branch A" in out
    assert "branch B" in out


def test_run_diff_shows_provenance_markers(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("events.jsonl").write_text(_DIFF_EVENTS, encoding="utf-8")

    cli.run_diff_local("anode", "bnode")

    out = capsys.readouterr().out
    assert "[U]" in out   # root (ancestor)
    assert "[G]" in out   # anode
    # bnode also [U] — check it appears at least twice
    assert out.count("[U]") >= 2


def test_run_diff_same_head(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("events.jsonl").write_text(_DIFF_EVENTS, encoding="utf-8")

    cli.run_diff_local("anode", "anode")

    out = capsys.readouterr().out
    assert "same head" in out


def test_run_diff_no_common_ancestor(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("events.jsonl").write_text(
        '{"id": "x", "parent": null, "role": "user", "content": "x", "metadata": {}}\n'
        '{"id": "y", "parent": null, "role": "user", "content": "y", "metadata": {}}\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="no common ancestor"):
        cli.run_diff_local("x", "y")


def test_run_diff_unknown_head(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("events.jsonl").write_text(
        '{"id": "n0", "parent": null, "role": "user", "content": "hi", "metadata": {}}\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="no message found with id: bad"):
        cli.run_diff_local("bad", "n0")


def test_run_diff_full_shows_complete_content(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    long_content = "word " * 30
    import json as _json
    events = (
        _json.dumps({"id": "r", "parent": None, "role": "user", "content": long_content, "metadata": {}}) + "\n"
        + _json.dumps({"id": "a", "parent": "r", "role": "assistant", "content": "short", "metadata": {}}) + "\n"
        + _json.dumps({"id": "b", "parent": "r", "role": "user", "content": "other", "metadata": {}}) + "\n"
    )
    Path("events.jsonl").write_text(events, encoding="utf-8")

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
