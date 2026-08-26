from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from toas.cli import run_session_continue
from toas.graph import (
    list_heads,
    message_lineage,
    read_log,
    write_message_events,
    write_surface_bind_record,
    write_surface_select_record,
)
from toas.prompts import load_prompt_ref
from toas.runtime.session_rotation import (
    _handoff_from_transcript,
    _leading_graph_start,
    _render_successor,
    _seed_message,
    continuation_blocker,
    continue_session,
    restoration_commands,
    restoration_plan,
    rotation_blocker,
    suggested_continuation_name,
    suggested_rotation_name,
)
from toas.runtime.step_context_runtime import build_runtime_context
from toas.step import parse_transcript, step


def _handoff(*, files: str = "$ cat src/toas/step.py", commands: str = "$ jj status") -> str:
    return f"""# Handoff Summary

## Current Objective
Implement explicit transcript continuation without journal rotation.

## Working State
Compaction is complete.

## Plans
- active: continue

## Observations
History is durable.

## Actions Taken
- compacted

## Commits / Change History
No commit.

## Policy / Procedure Updates
Continuation is explicit.

## Open Questions
None.

## Next Best Step
Restore context.

## Context to Preserve Verbatim

### Files to Restore
{files}

### Commands to Run
{commands}"""


def _compacted_repo(
    tmp_path: Path,
    *,
    handoff: str | None = None,
    newline: str = "\n",
    user_prefix: str = "",
) -> tuple[Path, str]:
    content = _handoff() if handoff is None else handoff
    events_path = tmp_path / ".toas" / "events.jsonl"
    events_path.parent.mkdir(parents=True)
    write_message_events(
        str(events_path),
        [
            {"role": "user", "content": "old work"},
            {"role": "assistant", "content": "old answer"},
            {"role": "user", "content": f"{user_prefix}/compact"},
            {"role": "assistant", "content": content, "provenance": {"source": "llm_compaction"}},
        ],
        timestamp_fn=lambda: 1,
    )
    session_path = tmp_path / ".toas" / "session.md"
    normalized = (
        "## TOAS:USER\n\nold work\n\n"
        "## TOAS:ASSISTANT\n\nold answer\n\n"
        f"## TOAS:USER\n\n{user_prefix}/compact\n\n"
        f"## TOAS:ASSISTANT\n\n{content}\n"
    )
    with session_path.open("w", encoding="utf-8", newline="") as stream:
        stream.write(normalized.replace("\n", newline))
    return session_path, content


def test_continue_session_accepts_verbose_compact_prompt_shape(tmp_path):
    session_path, handoff = _compacted_repo(tmp_path)
    prompt = load_prompt_ref("compaction/handoff_v1")
    session_path.write_text(
        "## TOAS:USER\n\n/compact\n\n"
        f"## TOAS:USER\n\n{prompt}\n\n"
        f"## TOAS:ASSISTANT\n\n{handoff}\n",
        encoding="utf-8",
    )

    result = continue_session(workdir=tmp_path, predecessor_path=str(session_path), accepted_name="verbose")

    assert result["status"] == "continued"


def test_handoff_and_leading_graph_helpers_accept_direct_shapes():
    nodes = [
        {"role": "user", "content": "/concept-graph"},
        {"role": "assistant", "content": "graph"},
        {"role": "user", "content": "/compact"},
        {"role": "assistant", "content": "handoff"},
    ]
    assert _leading_graph_start(nodes, command_index=2) == 0
    assert _handoff_from_transcript("\n\n".join(f"## TOAS:{node['role'].upper()}\n\n{node['content']}" for node in nodes)) == "handoff"


def test_continue_session_rejects_unrecognized_visible_prompt(tmp_path):
    session_path, handoff = _compacted_repo(tmp_path)
    session_path.write_text(
        "## TOAS:USER\n\n/compact\n\n"
        "## TOAS:USER\n\nnot the compaction prompt\n\n"
        f"## TOAS:ASSISTANT\n\n{handoff}\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="at the end of the last user turn"):
        continue_session(workdir=tmp_path, predecessor_path=str(session_path))


def test_continue_session_replays_graph_order_and_tail_controls(tmp_path):
    prompt = load_prompt_ref("concept-graph/projection_v1")
    seed = _seed_message(load_prompt_ref("session-start/templates/pragmatic-default_v2"))["content"]
    handoff = _handoff(files="$ cat AGENTS.md", commands="$ jj status")
    session_path = tmp_path / ".toas" / "session.md"
    session_path.parent.mkdir(parents=True)
    session_path.write_text(
        "## TOAS:USER\n\n/concept-graph\n\n"
        f"## TOAS:USER\n\n{prompt}\n\n"
        "## TOAS:ASSISTANT\n\n- Graph before\n\n"
        "## TOAS:USER\n\n/compact\n\n"
        f"## TOAS:ASSISTANT\n\n{handoff}\n\n"
        "## TOAS:USER\n\n/later\n\n"
        "## TOAS:ASSISTANT\n\n- Graph after\n",
        encoding="utf-8",
    )

    out = continue_session(workdir=tmp_path, predecessor_path=str(session_path), accepted_name="ordered")
    nodes = parse_transcript((tmp_path / out["successor_path"]).read_text(encoding="utf-8"))
    assert [node["content"] for node in nodes] == [
        seed,
        "/concept-graph",
        prompt,
        "- Graph before",
        "/compact",
        handoff,
        "$ cat AGENTS.md\n$ jj status",
        "/later",
        "- Graph after",
    ]

    ignored = continue_session(
        workdir=tmp_path,
        predecessor_path=str(session_path),
        accepted_name="ignored",
        ignore_preceding_graph=True,
    )
    ignored_nodes = parse_transcript((tmp_path / ignored["successor_path"]).read_text(encoding="utf-8"))
    assert [node["content"] for node in ignored_nodes[1:]] == [
        "/compact",
        handoff,
        "$ cat AGENTS.md\n$ jj status",
        "/later",
        "- Graph after",
    ]

    excluded = continue_session(
        workdir=tmp_path,
        predecessor_path=str(session_path),
        accepted_name="excluded",
        exclude_tail=True,
    )
    excluded_nodes = parse_transcript((tmp_path / excluded["successor_path"]).read_text(encoding="utf-8"))
    assert [node["content"] for node in excluded_nodes[1:]] == [
        "/concept-graph",
        prompt,
        "- Graph before",
        "/compact",
        handoff,
    ]


def test_restoration_commands_preserve_user_shape_agents_first_and_order(tmp_path):
    (tmp_path / "AGENTS.md").write_text("rules", encoding="utf-8")
    handoff = _handoff(
        files="- $ cat src/toas/step.py\n- $ cat 'docs/my notes.md'\n- $ cat AGENTS.md\n- $ cat src/toas/step.py",
        commands="$ jj status\n$ uv run pytest -q",
    )

    assert restoration_commands(handoff, workdir=tmp_path) == [
        "cat AGENTS.md",
        "cat src/toas/step.py",
        "cat 'docs/my notes.md'",
        "jj status",
        "uv run pytest -q",
    ]


def test_restoration_commands_normalize_windows_paths_to_forward_slashes(tmp_path):
    handoff = _handoff(files=r"$ cat src\toas\graph.py", commands="$ jj status")

    assert restoration_commands(handoff, workdir=tmp_path) == [
        "cat src/toas/graph.py",
        "jj status",
    ]


def test_restoration_commands_add_agents_and_skip_bad_entries(tmp_path):
    (tmp_path / "AGENTS.md").write_text("rules", encoding="utf-8")
    commands = restoration_commands(_handoff(), workdir=tmp_path)
    assert commands[0] == "cat AGENTS.md"

    malformed = _handoff(
        files="\n".join(
            [
                "$ cat -n x",
                "$ cat 'unterminated",
                "cat skipped.txt",
                "$ cat kept.txt",
            ]
        ),
        commands="jj status\n$ \n$ uv run pytest -q",
    )
    assert restoration_commands(malformed, workdir=tmp_path) == [
        "cat AGENTS.md",
        "cat kept.txt",
        "uv run pytest -q",
    ]
    missing = _handoff().replace("### Files to Restore", "### Missing").replace(
        "### Commands to Run", "### Also Missing"
    )
    assert restoration_commands(missing, workdir=tmp_path) == ["cat AGENTS.md"]

    assert restoration_plan(_handoff(), workdir=tmp_path) == restoration_commands(_handoff(), workdir=tmp_path)


def test_suggested_continuation_name_is_deterministic_and_has_fallback():
    assert suggested_continuation_name(_handoff(), today=date(2026, 8, 4)) == (
        "260804-implement-explicit-transcript-continuation-witho"
    )
    blank = _handoff().replace(
        "Implement explicit transcript continuation without journal rotation.",
        "***",
    )
    assert suggested_continuation_name(blank, today=date(2026, 8, 4)) == "260804-session-handoff"
    assert suggested_rotation_name(blank, today=date(2026, 8, 4)) == "260804-session-handoff"
    assert suggested_continuation_name("free-form handoff", today=date(2026, 8, 4)) == (
        "260804-session-handoff"
    )


def test_continuation_blocker_reports_active_runs_and_queues():
    assert continuation_blocker([]) is None
    assert continuation_blocker([{"kind": "run", "payload": {"run_id": "r2", "status": "running"}}]) == (
        "active run prevents session continuation: r2"
    )
    assert continuation_blocker(
        [
            {"kind": "run", "payload": {"run_id": "r2", "status": "completed"}},
            {"kind": "execution_queue", "payload": {"id": "q1", "status": "blocked"}},
        ]
    ) == "unresolved execution queue prevents session continuation: q1"
    assert continuation_blocker([{"kind": "run", "payload": "bad"}]) is None
    assert rotation_blocker([]) is None


def test_successor_seed_composition_accepts_plain_seed_and_rejects_multiple_messages():
    assert _seed_message("plain seed") == {"role": "user", "content": "plain seed"}
    with pytest.raises(RuntimeError, match="one user message"):
        _seed_message("## TOAS:USER\n\none\n\n## TOAS:ASSISTANT\n\ntwo\n")

    rendered = _render_successor(
        seed="plain seed",
        handoff=_handoff(),
        commands=["jj status"],
        newline="\n",
    )
    assert parse_transcript(rendered)[0] == {"role": "user", "content": "plain seed"}


def test_continue_session_suggest_is_mutation_free_and_projection_independent(tmp_path):
    session_path, _ = _compacted_repo(tmp_path)
    events_path = tmp_path / ".toas" / "events.jsonl"
    with events_path.open("a", encoding="utf-8") as stream:
        stream.write('{"kind":"compaction_projection","payload":{"projection_message_id":"stale","selected":true}}\n')
    before_events = events_path.read_bytes()
    before_session = session_path.read_bytes()

    out = continue_session(
        workdir=tmp_path,
        predecessor_path=str(session_path),
        today=date(2026, 8, 4),
    )

    assert out["status"] == "suggested"
    assert out["suggested_name"].startswith("260804-implement-explicit-transcript")
    assert out["suggested_path"].startswith(".toas/session-")
    assert events_path.read_bytes() == before_events
    assert session_path.read_bytes() == before_session
    assert not (tmp_path / out["suggested_path"]).exists()


def test_continue_session_appends_only_relationship_and_composes_messages(tmp_path):
    session_path, handoff = _compacted_repo(tmp_path, user_prefix="notes before the command\n")
    (tmp_path / "AGENTS.md").write_text("rules", encoding="utf-8")
    events_path = tmp_path / ".toas" / "events.jsonl"
    before = events_path.read_bytes()
    before_inode = events_path.stat().st_ino
    lineage_before = message_lineage(read_log(str(events_path)))

    out = continue_session(
        workdir=tmp_path,
        predecessor_path=str(session_path),
        accepted_name="vim-continuation",
        today=date(2026, 8, 4),
    )

    assert out == {
        "status": "continued",
        "accepted_name": "vim-continuation",
        "successor_path": ".toas/session-vim-continuation.md",
        "predecessor_path": ".toas/session.md",
        "restoration_commands": 3,
    }
    after = events_path.read_bytes()
    assert after.startswith(before)
    assert events_path.stat().st_ino == before_inode
    events = read_log(str(events_path))
    assert message_lineage(events) == lineage_before
    appended = events[len(read_log_bytes(before)) :]
    assert [event["kind"] for event in appended] == ["session_successor"]
    assert appended[0]["payload"] == {
        "predecessor_path": ".toas/session.md",
        "successor_path": out["successor_path"],
        "seed_prompt_ref": "session-start/templates/pragmatic-default_v2",
        "continuation_parent_id": lineage_before[-1]["id"],
    }
    nodes = parse_transcript((tmp_path / out["successor_path"]).read_text(encoding="utf-8"))
    assert [node["role"] for node in nodes] == ["user", "user", "assistant", "user"]
    assert nodes[1]["content"] == "notes before the command\n/compact"
    assert nodes[2]["content"] == handoff
    assert nodes[3]["content"] == "$ cat AGENTS.md\n$ cat src/toas/step.py\n$ jj status"
    assert "operation:" not in nodes[3]["content"]
    assert sum(1 for node in nodes if node["content"].startswith("# Handoff Summary")) == 1


def read_log_bytes(data: bytes) -> list[dict]:
    return [json.loads(line) for line in data.decode("utf-8").splitlines() if line]


def test_continue_session_does_not_rebind_unrelated_selected_surface(tmp_path):
    session_path, _ = _compacted_repo(tmp_path)
    events_path = tmp_path / ".toas" / "events.jsonl"
    write_surface_bind_record(
        str(events_path), surface_id="other", transcript_path=".toas/other.md", reason="fixture"
    )
    write_surface_select_record(str(events_path), surface_id="other")

    out = continue_session(workdir=tmp_path, predecessor_path=str(session_path), accepted_name="explicit")

    appended = read_log(str(events_path))[-1]
    assert appended["kind"] == "session_successor"
    assert appended["payload"]["successor_path"] == out["successor_path"]
    assert not any(
        event.get("kind") in {"config_override", "surface_bind"}
        for event in read_log(str(events_path))[-1:]
    )


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_continue_session_inherits_predecessor_newlines(tmp_path, newline):
    session_path, _ = _compacted_repo(tmp_path, newline=newline)

    out = continue_session(workdir=tmp_path, predecessor_path=str(session_path), accepted_name="newline")

    data = (tmp_path / out["successor_path"]).read_bytes()
    if newline == "\r\n":
        assert b"\r\n" in data
        assert b"\n" not in data.replace(b"\r\n", b"")
    else:
        assert b"\r\n" not in data


def test_continue_session_mixed_newlines_fall_back_to_lf(tmp_path):
    session_path, _ = _compacted_repo(tmp_path)
    data = session_path.read_bytes().replace(b"\n", b"\r\n", 1)
    session_path.write_bytes(data)

    out = continue_session(workdir=tmp_path, predecessor_path=str(session_path), accepted_name="mixed")

    assert b"\r\n" not in (tmp_path / out["successor_path"]).read_bytes()


def test_continue_session_resolves_collisions_without_overwrite(tmp_path):
    session_path, _ = _compacted_repo(tmp_path)
    existing = tmp_path / ".toas" / "session-next.md"
    existing.write_text("keep", encoding="utf-8")

    out = continue_session(workdir=tmp_path, predecessor_path=str(session_path), accepted_name="next")

    assert existing.read_text(encoding="utf-8") == "keep"
    assert out["successor_path"] == ".toas/session-next-2.md"


@pytest.mark.parametrize("name", ["", "bad name", "../escape"])
def test_continue_session_rejects_invalid_names_without_mutation(tmp_path, name):
    session_path, _ = _compacted_repo(tmp_path)
    before = (tmp_path / ".toas" / "events.jsonl").read_bytes()
    with pytest.raises(ValueError, match="must match"):
        continue_session(workdir=tmp_path, predecessor_path=str(session_path), accepted_name=name)
    assert (tmp_path / ".toas" / "events.jsonl").read_bytes() == before


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("/compact", "followed by an assistant handoff"),
        ("## TOAS:USER\n\nhello\n\n## TOAS:ASSISTANT\n\n# Handoff Summary\n", "at the end"),
    ],
)
def test_continue_session_requires_transcript_local_compact_and_assistant_turn(
    tmp_path, replacement, message
):
    session_path, _ = _compacted_repo(tmp_path)
    session_path.write_text(replacement, encoding="utf-8")

    with pytest.raises(RuntimeError, match=message):
        continue_session(workdir=tmp_path, predecessor_path=str(session_path))


def test_continue_session_input_validation_and_safe_boundary_failures(tmp_path):
    with pytest.raises(RuntimeError, match="does not exist"):
        continue_session(workdir=tmp_path)

    session_path, _ = _compacted_repo(tmp_path)
    with pytest.raises(RuntimeError, match="does not exist"):
        continue_session(workdir=tmp_path, predecessor_path=".toas/missing.md")

    outside = tmp_path.parent / "outside-session.md"
    outside.write_text("## TOAS:USER\n\n/compact\n\n## TOAS:ASSISTANT\n\n# Handoff Summary\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="inside the workspace"):
        continue_session(workdir=tmp_path, predecessor_path=str(outside))

    events_path = tmp_path / ".toas" / "events.jsonl"
    with events_path.open("a", encoding="utf-8") as stream:
        stream.write('{"kind":"run","payload":{"run_id":"r1","status":"running"}}\n')
    with pytest.raises(RuntimeError, match="active run"):
        continue_session(workdir=tmp_path, predecessor_path=str(session_path))


@pytest.mark.parametrize("handoff", ["ordinary answer", ""])
def test_continue_session_preserves_arbitrary_handoff_with_empty_user_slot(tmp_path, handoff):
    session_path, _ = _compacted_repo(tmp_path, handoff=handoff)

    suggested = continue_session(
        workdir=tmp_path,
        predecessor_path=str(session_path),
        today=date(2026, 8, 4),
    )
    out = continue_session(
        workdir=tmp_path,
        predecessor_path=str(session_path),
        accepted_name="advisory",
    )

    assert suggested["suggested_name"] == "260804-session-handoff"
    assert out["restoration_commands"] == 0
    nodes = parse_transcript((tmp_path / out["successor_path"]).read_text(encoding="utf-8"))
    assert [node["role"] for node in nodes] == ["user", "user", "assistant", "user"]
    assert nodes[1]["content"] == "/compact"
    assert nodes[2]["content"] == handoff
    assert nodes[3]["content"] == ""


def test_continue_session_cleans_successor_when_record_append_fails_without_bytes(tmp_path, monkeypatch):
    session_path, _ = _compacted_repo(tmp_path)
    monkeypatch.setattr(
        "toas.runtime.session_rotation.write_session_successor_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("write failed")),
    )

    with pytest.raises(RuntimeError, match="write failed"):
        continue_session(workdir=tmp_path, predecessor_path=str(session_path), accepted_name="failed")

    assert not (tmp_path / ".toas" / "session-failed.md").exists()


def test_continue_session_cleans_temporary_file_when_successor_replace_fails(tmp_path, monkeypatch):
    session_path, _ = _compacted_repo(tmp_path)
    monkeypatch.setattr(
        "toas.runtime.session_rotation.os.replace",
        lambda *_args: (_ for _ in ()).throw(OSError("replace failed")),
    )

    with pytest.raises(OSError, match="replace failed"):
        continue_session(workdir=tmp_path, predecessor_path=str(session_path), accepted_name="replace-failed")

    assert not (tmp_path / ".toas" / "session-replace-failed.md").exists()
    assert not list((tmp_path / ".toas").glob(".session-replace-failed.md.tmp-*"))


def test_first_successor_step_synchronizes_messages_after_continuation_parent(tmp_path):
    session_path, _ = _compacted_repo(tmp_path, handoff=_handoff(files="$ cat missing.txt", commands=""))
    out = continue_session(workdir=tmp_path, predecessor_path=str(session_path), accepted_name="first-step")
    successor = tmp_path / out["successor_path"]
    transcript = successor.read_text(encoding="utf-8")
    events = read_log(str(tmp_path / ".toas" / "events.jsonl"))
    runtime = build_runtime_context(
        events=events,
        normalized_transcript=transcript,
        session_path=successor,
        workdir=tmp_path,
    )

    new_nodes, consequences = step(
        transcript,
        runtime["log"],
        command_cwd=str(tmp_path),
        workspace_roots=[str(tmp_path)],
        bind_index=runtime["bind_index"],
        events=events,
    )

    assert runtime["bind_index"] == len(message_lineage(events))
    assert [node["role"] for node in new_nodes[:4]] == ["user", "user", "assistant", "user"]
    assert consequences[0]["payload"]["ok"] is False
    assert "missing.txt" in consequences[0]["content"]


def test_repeated_continuations_remain_on_one_lineage(tmp_path):
    first_path, _ = _compacted_repo(tmp_path)
    first = continue_session(workdir=tmp_path, predecessor_path=str(first_path), accepted_name="first")
    events_path = tmp_path / ".toas" / "events.jsonl"
    first_successor = tmp_path / first["successor_path"]
    write_message_events(str(events_path), parse_transcript(first_successor.read_text(encoding="utf-8")))
    second_handoff = _handoff(files="$ cat src/toas/graph.py", commands="").replace(
        "Implement explicit transcript continuation without journal rotation.",
        "Verify repeated continuation stays bounded.",
    )
    write_message_events(
        str(events_path),
        [
            {"role": "user", "content": "/compact"},
            {"role": "assistant", "content": second_handoff},
        ],
    )
    with first_successor.open("a", encoding="utf-8", newline="") as stream:
        stream.write(f"\n## TOAS:USER\n\n/compact\n\n## TOAS:ASSISTANT\n\n{second_handoff}\n")

    second = continue_session(workdir=tmp_path, predecessor_path=str(first_successor), accepted_name="second")
    final_events = read_log(str(events_path))
    second_path = tmp_path / second["successor_path"]
    runtime = build_runtime_context(
        events=final_events,
        normalized_transcript=second_path.read_text(encoding="utf-8"),
        session_path=second_path,
        workdir=tmp_path,
    )

    assert len(list_heads(final_events)) == 1
    assert runtime["bind_index"] == len(message_lineage(final_events))
    assert len(second_path.read_text(encoding="utf-8")) < 20_000


def test_runtime_context_ignores_unmatched_records_and_reads_legacy_rotation(tmp_path):
    events = [
        {"id": "n1", "parent": "n0", "role": "user", "content": "one", "metadata": {}},
        {"id": "n2", "parent": "n1", "role": "assistant", "content": "two", "metadata": {}},
        {"kind": "other", "payload": {"successor_path": ".toas/session-next.md"}},
        {"kind": "session_successor", "payload": "bad"},
        {
            "kind": "session_rotation",
            "payload": {
                "successor_path": ".toas/session-next.md",
                "boundary_message_ids": ["n2"],
            },
        },
    ]

    runtime = build_runtime_context(
        events=events,
        normalized_transcript="",
        session_path=tmp_path / ".toas" / "session-next.md",
        workdir=tmp_path,
    )
    outside = build_runtime_context(
        events=events,
        normalized_transcript="",
        session_path=tmp_path.parent / "outside.md",
        workdir=tmp_path,
    )

    assert runtime["bind_index"] == 1
    assert outside["bind_index"] == 0

    unrelated = build_runtime_context(
        events=[
            {"id": "n1", "parent": "n0", "role": "user", "content": "one", "metadata": {}},
            {"kind": "other", "payload": {"successor_path": ".toas/session-next.md"}},
        ],
        normalized_transcript="",
        session_path=tmp_path / ".toas" / "session-next.md",
        workdir=tmp_path,
    )
    assert unrelated["bind_index"] == 0


def test_run_session_continue_prints_canonical_result_json(tmp_path, monkeypatch, capsys):
    seen = {}

    def fake_continue(**kwargs):
        seen.update(kwargs)
        return {"status": "suggested", "suggested_name": "next"}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("toas.cli_commands.continue_runtime_session", fake_continue)
    run_session_continue(predecessor_path="session.md", accepted_name="next")

    assert seen == {
        "workdir": tmp_path,
        "predecessor_path": "session.md",
        "accepted_name": "next",
    }
    assert json.loads(capsys.readouterr().out) == {"status": "suggested", "suggested_name": "next"}


def test_run_session_continue_forwards_replay_controls(tmp_path, monkeypatch, capsys):
    seen = {}

    def fake_continue(**kwargs):
        seen.update(kwargs)
        return {"status": "suggested", "suggested_name": "next"}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("toas.cli_commands.continue_runtime_session", fake_continue)
    run_session_continue(
        predecessor_path="session.md",
        accepted_name="next",
        ignore_preceding_graph=True,
        exclude_tail=True,
    )

    assert seen == {
        "workdir": tmp_path,
        "predecessor_path": "session.md",
        "accepted_name": "next",
        "ignore_preceding_graph": True,
        "exclude_tail": True,
    }
