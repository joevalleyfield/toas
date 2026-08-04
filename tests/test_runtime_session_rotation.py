from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from toas.cli import run_session_rotate
from toas.graph import (
    active_config_overrides,
    list_heads,
    message_lineage,
    read_log,
    surface_bindings,
    write_compaction_projection_record,
    write_message_events,
    write_surface_bind_record,
    write_surface_select_record,
)
from toas.runtime.session_rotation import (
    restoration_plan,
    rotate_session,
    rotation_blocker,
    suggested_rotation_name,
)
from toas.runtime.step_context_runtime import build_runtime_context
from toas.step import step


def _handoff(*, files: str = "$ cat src/toas/step.py", commands: str = "$ uv run pytest -q") -> str:
    return f"""# Handoff Summary

## Current Objective
Implement explicit Vim successor rotation without automatic transcript policy.

## Working State
Compaction is selected.

## Plans
- active: rotate

## Observations
History is durable.

## Actions Taken
- compacted

## Commits / Change History
No commit.

## Policy / Procedure Updates
Rotation is explicit.

## Open Questions
None.

## Next Best Step
Restore context.

## Context to Preserve Verbatim

### Files to Restore
{files}

### Commands to Run
{commands}"""


def _compacted_repo(tmp_path: Path, *, handoff: str | None = None) -> tuple[Path, str]:
    content = handoff or _handoff()
    events_path = tmp_path / ".toas" / "events.jsonl"
    events_path.parent.mkdir(parents=True)
    messages = write_message_events(
        str(events_path),
        [
            {"role": "user", "content": "old work"},
            {"role": "assistant", "content": "old answer"},
            {"role": "user", "content": content, "provenance": {"source": "llm_compaction"}},
        ],
        timestamp_fn=lambda: 1,
    )
    write_compaction_projection_record(
        str(events_path),
        projection_message_id=messages[-1]["id"],
        source_message_ids=[messages[0]["id"], messages[1]["id"]],
        source_head_id=messages[1]["id"],
        prompt_ref="compaction/handoff_v1",
    )
    session_path = tmp_path / ".toas" / "session.md"
    session_path.write_text(
        f"## TOAS:USER\n\nold work\n\n"
        f"## TOAS:ASSISTANT\n\nold answer\n\n"
        f"## RESULT\n\n{content}\n",
        encoding="utf-8",
    )
    return session_path, content


def test_restoration_plan_restores_agents_first_and_preserves_order(tmp_path):
    (tmp_path / "AGENTS.md").write_text("rules", encoding="utf-8")
    handoff = _handoff(
        files="- $ cat src/toas/step.py\n- $ cat 'docs/my notes.md'\n- $ cat AGENTS.md\n- $ cat src/toas/step.py",
        commands="$ jj status\n$ uv run pytest -q",
    )

    assert restoration_plan(handoff, workdir=tmp_path) == [
        {"operation": "read_file", "arguments": {"path": "AGENTS.md", "number_lines": True}},
        {"operation": "read_file", "arguments": {"path": "src/toas/step.py", "number_lines": True}},
        {"operation": "read_file", "arguments": {"path": "docs/my notes.md", "number_lines": True}},
        {"operation": "shell_script", "arguments": {"script": "jj status"}},
        {"operation": "shell_script", "arguments": {"script": "uv run pytest -q"}},
    ]


def test_restoration_plan_adds_governing_agents_and_rejects_bad_entries(tmp_path):
    (tmp_path / "AGENTS.md").write_text("rules", encoding="utf-8")
    plan = restoration_plan(_handoff(files="$ cat src/toas/step.py", commands="$ jj status"), workdir=tmp_path)
    assert plan[0]["arguments"]["path"] == "AGENTS.md"

    with pytest.raises(ValueError, match=r"must be '\$ cat <path>'"):
        restoration_plan(_handoff(files="$ cat -n x", commands="$ jj status"), workdir=tmp_path)
    with pytest.raises(ValueError, match="invalid ### Commands to Run entry"):
        restoration_plan(_handoff(commands="jj status"), workdir=tmp_path)


def test_suggested_rotation_name_is_deterministic_and_has_fallback():
    assert suggested_rotation_name(_handoff(), today=date(2026, 8, 4)) == (
        "260804-implement-explicit-vim-successor-rotation-withou"
    )
    blank = _handoff().replace(
        "Implement explicit Vim successor rotation without automatic transcript policy.",
        "***",
    )
    assert suggested_rotation_name(blank, today=date(2026, 8, 4)) == "260804-session-handoff"


def test_rotation_blocker_reports_active_runs_and_queues():
    assert rotation_blocker([]) is None
    assert rotation_blocker([{"kind": "run", "payload": {"run_id": "r2", "status": "running"}}]) == (
        "active run prevents session rotation: r2"
    )
    assert rotation_blocker(
        [
            {"kind": "run", "payload": {"run_id": "r2", "status": "completed"}},
            {"kind": "execution_queue", "payload": {"id": "q1", "status": "blocked"}},
        ]
    ) == "unresolved execution queue prevents session rotation: q1"
    assert rotation_blocker([{"kind": "run", "payload": "bad"}]) is None


def test_rotate_session_suggest_is_mutation_free(tmp_path):
    session_path, _ = _compacted_repo(tmp_path)
    before_events = (tmp_path / ".toas" / "events.jsonl").read_bytes()
    before_session = session_path.read_bytes()

    out = rotate_session(
        workdir=tmp_path,
        predecessor_path=str(session_path),
        today=date(2026, 8, 4),
    )

    assert out["status"] == "suggested"
    assert out["suggested_name"].startswith("260804-implement-explicit-vim")
    assert out["suggested_path"].startswith(".toas/session-")
    assert (tmp_path / ".toas" / "events.jsonl").read_bytes() == before_events
    assert session_path.read_bytes() == before_session
    assert not (tmp_path / out["suggested_path"]).exists()


def test_rotate_session_commits_successor_messages_path_and_boundary(tmp_path):
    session_path, handoff = _compacted_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("rules", encoding="utf-8")

    out = rotate_session(
        workdir=tmp_path,
        predecessor_path=str(session_path),
        accepted_name="vim-rotation",
        today=date(2026, 8, 4),
    )

    assert out == {
        "status": "rotated",
        "accepted_name": "vim-rotation",
        "successor_path": ".toas/session-vim-rotation.md",
        "predecessor_path": str(session_path),
        "restoration_operations": 3,
    }
    successor = tmp_path / out["successor_path"]
    text = successor.read_text(encoding="utf-8")
    assert handoff in text
    assert "operation: read_file\n  arguments:\n    path: AGENTS.md" in text
    assert "operation: shell_script" in text
    events = read_log(str(tmp_path / ".toas" / "events.jsonl"))
    rotation = next(event for event in events if event.get("kind") == "session_rotation")
    assert rotation["payload"]["successor_path"] == out["successor_path"]
    assert rotation["payload"]["seed_prompt_ref"] == "session-start/templates/pragmatic-default_v2"
    assert len(rotation["payload"]["boundary_message_ids"]) == 3
    assert active_config_overrides(events)["session"]["transcript_path"] == out["successor_path"]
    assert len(list_heads(events)) == 1
    runtime = build_runtime_context(events=events, normalized_transcript=text)
    assert runtime["bind_index"] == 3


def test_rotate_session_rebinds_selected_surface_to_successor(tmp_path):
    session_path, _ = _compacted_repo(tmp_path)
    events_path = tmp_path / ".toas" / "events.jsonl"
    write_surface_bind_record(
        str(events_path),
        surface_id="vim-main",
        transcript_path=".toas/session.md",
        reason="fixture",
    )
    write_surface_select_record(str(events_path), surface_id="vim-main")

    out = rotate_session(
        workdir=tmp_path,
        predecessor_path=str(session_path),
        accepted_name="surface",
    )

    events = read_log(str(events_path))
    assert surface_bindings(events)["vim-main"] == out["successor_path"]
    assert next(event for event in reversed(events) if event.get("kind") == "surface_bind")["payload"][
        "reason"
    ] == "session_rotation"


def test_rotate_session_resolves_collisions_without_overwrite(tmp_path):
    session_path, _ = _compacted_repo(tmp_path)
    existing = tmp_path / ".toas" / "session-vim-rotation.md"
    existing.write_text("keep", encoding="utf-8")

    out = rotate_session(
        workdir=tmp_path,
        predecessor_path=str(session_path),
        accepted_name="vim-rotation",
    )

    assert existing.read_text(encoding="utf-8") == "keep"
    assert out["successor_path"] == ".toas/session-vim-rotation-2.md"


@pytest.mark.parametrize("name", ["", "bad name", "../escape"])
def test_rotate_session_rejects_invalid_names_without_mutation(tmp_path, name):
    session_path, _ = _compacted_repo(tmp_path)
    before = (tmp_path / ".toas" / "events.jsonl").read_bytes()
    with pytest.raises(ValueError, match="must match"):
        rotate_session(workdir=tmp_path, predecessor_path=str(session_path), accepted_name=name)
    assert (tmp_path / ".toas" / "events.jsonl").read_bytes() == before


def test_rotate_session_requires_current_projection_and_matching_predecessor(tmp_path):
    session_path, _ = _compacted_repo(tmp_path)
    session_path.write_text("wrong", encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not contain"):
        rotate_session(workdir=tmp_path, predecessor_path=str(session_path))

    events_path = tmp_path / ".toas" / "events.jsonl"
    write_message_events(str(events_path), [{"role": "user", "content": "later"}], timestamp_fn=lambda: 2)
    with pytest.raises(RuntimeError, match="not the current safe lineage boundary"):
        rotate_session(workdir=tmp_path, predecessor_path=str(session_path))


def test_rotation_input_validation_and_safe_boundary_failures(tmp_path):
    with pytest.raises(RuntimeError, match="requires a selected"):
        rotate_session(workdir=tmp_path)

    session_path, _ = _compacted_repo(tmp_path)
    with pytest.raises(RuntimeError, match="predecessor transcript does not exist"):
        rotate_session(workdir=tmp_path, predecessor_path=".toas/missing.md")

    outside = tmp_path.parent / "outside-session.md"
    outside.write_text(_handoff(), encoding="utf-8")
    with pytest.raises(RuntimeError, match="must be inside the workspace"):
        rotate_session(workdir=tmp_path, predecessor_path=str(outside))

    events_path = tmp_path / ".toas" / "events.jsonl"
    with events_path.open("a", encoding="utf-8") as stream:
        stream.write('{"kind":"run","payload":{"run_id":"r1","status":"running"}}\n')
    with pytest.raises(RuntimeError, match="active run"):
        rotate_session(workdir=tmp_path, predecessor_path=str(session_path))


def test_restoration_parser_rejects_missing_empty_and_unparseable_entries(tmp_path):
    with pytest.raises(ValueError, match="missing ### Files to Restore"):
        restoration_plan(_handoff().replace("### Files to Restore", "### Missing"), workdir=tmp_path)
    with pytest.raises(ValueError, match="invalid ### Commands to Run entry"):
        restoration_plan(_handoff(commands="$ "), workdir=tmp_path)
    with pytest.raises(ValueError, match="invalid Files to Restore command"):
        restoration_plan(_handoff(files="$ cat 'unterminated"), workdir=tmp_path)


def test_rotate_session_requires_at_least_one_restore_operation(tmp_path):
    empty_handoff = _handoff(files="", commands="")
    session_path, _ = _compacted_repo(tmp_path, handoff=empty_handoff)
    with pytest.raises(RuntimeError, match="contains no restoration operations"):
        rotate_session(workdir=tmp_path, predecessor_path=str(session_path))


def test_rotate_session_cleans_successor_file_when_durable_commit_fails(tmp_path, monkeypatch):
    session_path, _ = _compacted_repo(tmp_path)
    monkeypatch.setattr(
        "toas.runtime.session_rotation.write_session_rotation_transition",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("write failed")),
    )
    with pytest.raises(RuntimeError, match="write failed"):
        rotate_session(workdir=tmp_path, predecessor_path=str(session_path), accepted_name="failed")
    assert not (tmp_path / ".toas" / "session-failed.md").exists()


def test_rotate_session_preserves_journal_when_atomic_transition_replace_fails(tmp_path, monkeypatch):
    session_path, _ = _compacted_repo(tmp_path)
    events_path = tmp_path / ".toas" / "events.jsonl"
    before = events_path.read_bytes()
    monkeypatch.setattr(
        "toas.graph._replace_session_rotation_log",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("replace failed")),
    )

    with pytest.raises(OSError, match="replace failed"):
        rotate_session(workdir=tmp_path, predecessor_path=str(session_path), accepted_name="atomic-fail")

    assert events_path.read_bytes() == before
    assert not (tmp_path / ".toas" / "session-atomic-fail.md").exists()
    assert list((tmp_path / ".toas").glob(".events.jsonl.*")) == []


def test_rotated_restoration_uses_ordinary_first_failure_recovery(tmp_path):
    handoff = _handoff(files="$ cat missing.txt\n$ cat later.txt", commands="")
    session_path, _ = _compacted_repo(tmp_path, handoff=handoff)
    out = rotate_session(
        workdir=tmp_path,
        predecessor_path=str(session_path),
        accepted_name="recovery",
    )
    successor = tmp_path / out["successor_path"]
    transcript = successor.read_text(encoding="utf-8")
    events = read_log(str(tmp_path / ".toas" / "events.jsonl"))
    runtime = build_runtime_context(events=events, normalized_transcript=transcript)

    _new_nodes, consequences = step(
        transcript,
        runtime["log"],
        command_cwd=str(tmp_path),
        workspace_roots=[str(tmp_path)],
        bind_index=runtime["bind_index"],
        events=events,
    )

    assert consequences[0]["payload"]["ok"] is False
    assert "missing.txt" in consequences[1]["content"]
    assert "Retry failed operation" in consequences[1]["content"]
    assert "later.txt" in consequences[1]["content"]


def test_repeated_explicit_rotations_rebind_small_transcripts_on_one_lineage(tmp_path):
    first_path, _ = _compacted_repo(tmp_path)
    first = rotate_session(
        workdir=tmp_path,
        predecessor_path=str(first_path),
        accepted_name="first",
    )
    events_path = tmp_path / ".toas" / "events.jsonl"
    events = read_log(str(events_path))
    second_handoff = _handoff(files="$ cat src/toas/graph.py", commands="").replace(
        "Implement explicit Vim successor rotation without automatic transcript policy.",
        "Verify a second explicit rotation remains bounded.",
    )
    projection = write_message_events(
        str(events_path),
        [{"role": "user", "content": second_handoff, "provenance": {"source": "llm_compaction"}}],
        timestamp_fn=lambda: 2,
    )[0]
    first_boundary = next(event for event in reversed(events) if event.get("kind") == "session_rotation")["payload"][
        "boundary_message_ids"
    ]
    write_compaction_projection_record(
        str(events_path),
        projection_message_id=projection["id"],
        source_message_ids=first_boundary,
        source_head_id=first_boundary[-1],
        prompt_ref="compaction/handoff_v1",
    )
    first_successor = tmp_path / first["successor_path"]
    first_successor.write_text(
        f"{first_successor.read_text(encoding='utf-8')}\n## RESULT\n\n{second_handoff}\n",
        encoding="utf-8",
    )

    second = rotate_session(
        workdir=tmp_path,
        predecessor_path=str(first_successor),
        accepted_name="second",
    )

    final_events = read_log(str(events_path))
    second_text = (tmp_path / second["successor_path"]).read_text(encoding="utf-8")
    runtime = build_runtime_context(events=final_events, normalized_transcript=second_text)
    assert len(list_heads(final_events)) == 1
    assert len(message_lineage(final_events)) == 10
    assert runtime["bind_index"] == 7
    assert active_config_overrides(final_events)["session"]["transcript_path"] == second["successor_path"]
    assert second_handoff in second_text
    assert len(second_text) < 20_000


def test_run_session_rotate_prints_runtime_transition_json(tmp_path, monkeypatch, capsys):
    seen = {}

    def fake_rotate(**kwargs):
        seen.update(kwargs)
        return {"status": "suggested", "suggested_name": "next"}

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("toas.cli_commands.rotate_runtime_session", fake_rotate)
    run_session_rotate(predecessor_path="session.md", accepted_name="next")

    assert seen == {
        "workdir": tmp_path,
        "predecessor_path": "session.md",
        "accepted_name": "next",
    }
    assert json.loads(capsys.readouterr().out) == {"status": "suggested", "suggested_name": "next"}
