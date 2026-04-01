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

    assert seen["messages"] == [
        {
            "role": "system",
            "content": (
                "You are TOAS operating on a transcript-oriented conversation.\n"
                "Continue the selected lineage faithfully.\n"
                "Return only the next assistant message content."
            ),
        },
        {"role": "user", "content": "part one\n\npart two"},
    ]
    assert seen["model"] == "local-model"
    assert seen["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert Path("events.jsonl").read_text(encoding="utf-8") == (
        '{"kind": "llm_call", "payload": {"requested_model": "local-model", "messages": [{"role": "system", "content": "You are TOAS operating on a transcript-oriented conversation.\\nContinue the selected lineage faithfully.\\nReturn only the next assistant message content."}, {"role": "user", "content": "part one\\n\\npart two"}], "response_model": "Qwen3.5-35B-A3B-UD-Q8_K_XL.gguf", "response": {"content": "answer", "reasoning_content": "private chain"}}}\n'
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
        '{"kind": "llm_call", "payload": {"requested_model": "local-model", "messages": [{"role": "system", "content": "You are TOAS operating on a transcript-oriented conversation.\\nContinue the selected lineage faithfully.\\nReturn only the next assistant message content."}, {"role": "user", "content": "hello"}], "error": "backend unavailable"}}\n'
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
