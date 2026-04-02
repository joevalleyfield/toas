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
    Path("session.md").write_text("## USER\nhello\n", encoding="utf-8")

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
        assert transcript == "## USER\nhello\n"
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
    assert capsys.readouterr().out == "## ASSISTANT\nhi\n\n"


def test_run_step_never_rewrites_session_md(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    original = "## USER\nhello\n"
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
    assert capsys.readouterr().out == "## ASSISTANT\nhi\n\n"


def test_run_step_does_not_touch_existing_session_file(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    session_path = Path("session.md")
    session_path.write_text("## USER\nhello\n", encoding="utf-8")
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
        "  n1 assistant: main\n"
        "* n2 assistant: branch\n"
    )


def test_main_defaults_to_step(monkeypatch):
    seen = []

    monkeypatch.setattr(cli.sys, "argv", ["toas"])
    monkeypatch.setattr(cli, "run_step", lambda: seen.append("step"))

    cli.main()

    assert seen == ["step"]


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
    monkeypatch.setattr(cli, "run_prompt", lambda ref: seen.append(ref))

    cli.main()

    assert seen == ["protocol/terse_v1"]


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
    Path("session.md").write_text("## USER\nhello\n", encoding="utf-8")
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
        assert transcript == "## USER\nhello\n"
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

    assert capsys.readouterr().out == "## USER\nroot\n\n## ASSISTANT\nbranch\n"


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

    assert capsys.readouterr().out == "## USER\nroot\n\n## ASSISTANT\nmain\n"


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

    assert capsys.readouterr().out == "## USER\npart one\n\npart two\n\n## ASSISTANT\nanswer\n\n"


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

    assert Path("session.md").read_text(encoding="utf-8") == "## USER\nroot\n\n## ASSISTANT\nbranch\n"
    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "assistant", "content": "branch", "metadata": {}}\n'
        '{"kind": "head", "payload": {"head_id": "n1"}}\n'
        '{"kind": "anchor", "payload": {"offset": 34, "node_id": "n1"}}\n'
    )
    assert capsys.readouterr().out == "rebuilt session.md from head n1\n"


def test_run_rebuild_avoids_duplicate_equivalent_anchor(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
            '{"kind": "anchor", "payload": {"offset": 13, "node_id": "n0"}}\n'
        ),
        encoding="utf-8",
    )

    cli.run_rebuild()

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"id": "n0", "parent": null, "role": "user", "content": "root", "metadata": {}}\n'
        '{"kind": "anchor", "payload": {"offset": 13, "node_id": "n0"}}\n'
    )
    assert capsys.readouterr().out == "rebuilt session.md from head n0\n"


def test_run_step_derives_bind_parent_from_message_event_space(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## USER\nhello\n", encoding="utf-8")
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
    Path("session.md").write_text("## USER\nhello\n", encoding="utf-8")
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
    Path("session.md").write_text("## USER\nhello\n", encoding="utf-8")
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
        assert transcript == "## USER\nhello\n"
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
    Path("session.md").write_text("## USER\nhello\n", encoding="utf-8")

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
    assert capsys.readouterr().out == "## ASSISTANT\nhi\n\n"


def test_run_step_uses_real_generation_callback_with_projected_llm_input(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## USER\npart one\n\n## USER\npart two\n", encoding="utf-8")
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
        '{"kind": "llm_call", "payload": {"requested_model": "local-model", "messages": [{"role": "user", "content": "part one\\n\\npart two"}], "response_model": "Qwen3.5-35B-A3B-UD-Q8_K_XL.gguf", "response": {"content": "answer", "reasoning_content": "private chain"}}}\n'
        '{"id": "n0", "parent": null, "role": "user", "content": "part one", "metadata": {}}\n'
        '{"id": "n1", "parent": "n0", "role": "user", "content": "part two", "metadata": {}}\n'
        '{"id": "n2", "parent": "n1", "role": "assistant", "content": "answer", "metadata": {}}\n'
    )
    assert capsys.readouterr().out == "## ASSISTANT\nanswer\n\n"


def test_run_step_records_llm_failure_and_exits(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TOAS_LLM_MODEL", "local-model")
    Path("session.md").write_text("## USER\nhello\n", encoding="utf-8")

    def fake_generate(messages, *, settings=None, extra_body=None):
        raise RuntimeError("backend unavailable")

    monkeypatch.setattr(cli, "generate_assistant_message", fake_generate)

    with pytest.raises(SystemExit, match="llm generation failed: backend unavailable"):
        cli.run_step()

    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"kind": "llm_call", "payload": {"requested_model": "local-model", "messages": [{"role": "user", "content": "hello"}], "error": "backend unavailable"}}\n'
    )


def test_run_step_preserves_explicit_parent_from_step_output(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## ASSISTANT\nalternate\n", encoding="utf-8")
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
        "## USER\nplease run this\n```yaml\n- tool_name: echo\n  args:\n    text: hi\n```\n",
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
    assert capsys.readouterr().out == "## RESULT\nran echo\n\n"


def test_run_step_writes_shell_tool_request_and_result_records_for_dollar_tail(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text(
        "## USER\nshow cwd\n$ pwd\n",
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
    assert capsys.readouterr().out == "## RESULT\n[OK] shell: exit=0\nstdout:\n/workspace\n\n"


def test_run_step_canonicalizes_assistant_loose_command_without_executing(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text(
        (
            "## USER\n"
            "Scan the directories\n\n"
            "## ASSISTANT\n"
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
    assert capsys.readouterr().out == "## USER\n$ find . -type f | head -5\n\n"


def test_run_step_uses_alignment_anchor_when_transcript_matches_prefix(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    Path("session.md").write_text("## USER\nhello\n\n## ASSISTANT\nhi\n\n## USER\nnext\n", encoding="utf-8")
    Path("events.jsonl").write_text(
        (
            '{"id": "n0", "parent": null, "role": "user", "content": "hello", "metadata": {}}\n'
            '{"id": "n1", "parent": "n0", "role": "assistant", "content": "hi", "metadata": {}}\n'
            '{"kind": "anchor", "payload": {"offset": 31, "node_id": "n1"}}\n'
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
    Path("session.md").write_text("## USER\nroot\n\n## ASSISTANT\nbranch\n", encoding="utf-8")
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
    monkeypatch.setattr(cli, "rpc_request", lambda op, payload=None: {"stdout": "## RESULT\nok\n\n"})
    monkeypatch.setattr(cli, "run_step_local", lambda: (_ for _ in ()).throw(AssertionError("should not run local")))

    cli.run_step()

    assert capsys.readouterr().out == "## RESULT\nok\n\n"


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
