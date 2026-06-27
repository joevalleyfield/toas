import json
import importlib.util
from pathlib import Path
import sys
import pytest

from toas.tasks import (
    LocalMarkdownAdapter,
    TaskTrackerAdapter,
    slugify,
    route_and_capture,
    resolve_active_message_id,
)
from toas.tools import REGISTRY, execute_call


def _load_sync_workboard_module():
    script_path = Path(__file__).resolve().parent.parent / "tasks" / "scripts" / "sync_workboard.py"
    module_name = "sync_workboard_module"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_slugify() -> None:
    assert slugify("My Cool Task!") == "my-cool-task"
    assert slugify("  Refactor Codebase  ") == "refactor-codebase"
    assert slugify("!!!") == "task"


def test_task_tracker_adapter_abstract_methods_are_noop_when_delegated() -> None:
    from toas.tasks import TaskCaptureEvent, TaskCapturePayload, TaskCaptureOutcome
    class _Adapter(TaskTrackerAdapter):
        def log_event(self, event: TaskCaptureEvent) -> None:
            return super().log_event(event)

        def find_existing_event(
            self,
            title: str,
            kind: str,
            active_task_id: str | None,
            capture_id: str | None = None,
        ) -> TaskCaptureEvent | None:
            return super().find_existing_event(title, kind, active_task_id, capture_id)

        def verify_physical_event(self, event: TaskCaptureEvent) -> bool:
            return super().verify_physical_event(event)

        def get_next_task_id(self) -> int:
            return super().get_next_task_id()

        def edit_task_section(self, task_file: str, section: str, item_text: str) -> bool:
            return super().edit_task_section(task_file, section, item_text)

        def create_standalone_task(
            self,
            task_id: int,
            title: str,
            kind: str,
            evidence: str,
            active_task_id: str | None = None,
            active_message_id: str | None = None,
        ) -> str:
            return super().create_standalone_task(task_id, title, kind, evidence, active_task_id, active_message_id)

        def mark_task_blocked(
            self,
            parent_task_file: str,
            blocker_task_file: str,
            why_blocked: str,
            capture_id: str,
            active_message_id: str | None = None,
            resume_condition: str | None = None,
            suggested_resume_action: str | None = None,
        ) -> bool:
            return super().mark_task_blocked(
                parent_task_file,
                blocker_task_file,
                why_blocked,
                capture_id,
                active_message_id,
                resume_condition,
                suggested_resume_action,
            )

        def route_to_inbox(self, title: str, kind: str, evidence: str, active_task_id: str | None = None) -> str:
            return super().route_to_inbox(title, kind, evidence, active_task_id)

    adapter = _Adapter()
    payload = TaskCapturePayload("T", "todo")
    outcome = TaskCaptureOutcome("macro", "path", "continue", "sum")
    event = TaskCaptureEvent("cap1", "time", payload, outcome)
    assert adapter.log_event(event) is None
    assert adapter.find_existing_event("T", "todo", None) is None
    assert adapter.verify_physical_event(event) is None
    assert adapter.get_next_task_id() is None
    assert adapter.edit_task_section("task", "Section", "item") is None
    assert adapter.create_standalone_task(1, "Title", "kind", "evidence") is None
    assert adapter.mark_task_blocked("parent", "blocker", "why", "cap") is None
    assert adapter.route_to_inbox("Title", "kind", "evidence") is None


def test_local_markdown_adapter_next_task_id(tmp_path: Path) -> None:
    adapter = LocalMarkdownAdapter(tmp_path)
    
    # Dir doesn't exist
    assert adapter.get_next_task_id() == 1
    
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True)
    assert adapter.get_next_task_id() == 1
    
    # Non-matching name
    (open_dir / "abc.md").write_text("hello", encoding="utf-8")
    assert adapter.get_next_task_id() == 1
    
    # Matching names
    (open_dir / "12-something.md").write_text("hello", encoding="utf-8")
    (open_dir / "9-another.md").write_text("hello", encoding="utf-8")
    assert adapter.get_next_task_id() == 13


def test_local_markdown_adapter_next_task_id_ignores_bad_match(monkeypatch, tmp_path: Path) -> None:
    adapter = LocalMarkdownAdapter(tmp_path)
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True)
    (open_dir / "1-task.md").write_text("hello", encoding="utf-8")

    class _BadMatch:
        def group(self, _index):
            return "not-an-int"

    import toas.tasks

    monkeypatch.setattr(toas.tasks.re, "match", lambda *_args, **_kwargs: _BadMatch())
    assert adapter.get_next_task_id() == 1


def test_local_markdown_adapter_resolve_task_file(tmp_path: Path) -> None:
    adapter = LocalMarkdownAdapter(tmp_path)
    
    # Missing parent task
    assert adapter._resolve_task_file("677") is None
    
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True)
    task_file = open_dir / "677-task-thread-capture.md"
    task_file.write_text("hello", encoding="utf-8")
    
    assert adapter._resolve_task_file("677") == task_file.resolve()
    assert adapter._resolve_task_file("677-task-thread-capture") == task_file.resolve()
    assert adapter._resolve_task_file("tasks/open/677-task-thread-capture.md") == task_file.resolve()
    assert adapter._resolve_task_file("invalid-id") is None


def test_local_markdown_adapter_edit_task_section(tmp_path: Path) -> None:
    adapter = LocalMarkdownAdapter(tmp_path)
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True)
    task_file = open_dir / "1-test.md"
    
    # File not found
    assert not adapter.edit_task_section("1", "Risks", "my risk")
    
    # Create file and test section appends
    task_file.write_text("# 1 test\n\n## Goal\n\nSome goal\n", encoding="utf-8")
    
    # Section doesn't exist -> gets appended at bottom
    assert adapter.edit_task_section("1", "Risks", "risk item 1")
    content = task_file.read_text(encoding="utf-8")
    assert "## Risks\n\n- [ ] risk item 1\n" in content
    
    # Section exists -> appends to list
    assert adapter.edit_task_section("1", "Risks", "risk item 2")
    content = task_file.read_text(encoding="utf-8")
    assert "## Risks\n\n- [ ] risk item 1\n- [ ] risk item 2\n" in content
    
    # Another section doesn't exist
    assert adapter.edit_task_section("1", "Next Actions", "todo 1")
    content = task_file.read_text(encoding="utf-8")
    assert "## Next Actions\n\n- [ ] todo 1\n" in content


def test_local_markdown_adapter_create_standalone_task(tmp_path: Path) -> None:
    adapter = LocalMarkdownAdapter(tmp_path)
    path = adapter.create_standalone_task(
        task_id=10,
        title="My Task",
        kind="cleanup",
        evidence="some code evidence",
        active_task_id="5",
        active_message_id="m4",
    )
    
    assert path == "tasks/open/10-my-task.md"
    p = tmp_path / path
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "# 10 My Task" in content
    assert "keywords: cleanup, captured, active_message_id=m4" in content
    assert "Captured during execution of active task 5." in content
    assert "## Evidence\n\nsome code evidence" in content


def test_local_markdown_adapter_mark_task_blocked(tmp_path: Path) -> None:
    adapter = LocalMarkdownAdapter(tmp_path)
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True)
    parent_file = open_dir / "5-parent.md"
    parent_file.write_text("# 5 Parent Task\n\n## Goal\n\nImplement parent task\n", encoding="utf-8")
    
    success = adapter.mark_task_blocked(
        parent_task_file="5",
        blocker_task_file="tasks/open/6-blocker.md",
        why_blocked="blocked by some issue",
        capture_id="cap_12345",
        active_message_id="m4",
        resume_condition="Blocker is completed.",
        suggested_resume_action="Continue working.",
    )
    
    assert success
    content = parent_file.read_text(encoding="utf-8")
    assert "# 5 Parent Task" in content
    assert "- **Status:** blocked" in content
    assert "- **Blocked By:** tasks/open/6-blocker.md" in content
    assert "- **Why Blocked:** blocked by some issue" in content
    assert "- **Active Message ID:** m4" in content
    assert "- **Resume Condition:** Blocker is completed." in content


def test_local_markdown_adapter_route_to_inbox(tmp_path: Path) -> None:
    adapter = LocalMarkdownAdapter(tmp_path)
    
    path = adapter.route_to_inbox(
        title="Unclear item",
        kind="unknown",
        evidence="some inline context\nline 2",
        active_task_id="5",
    )
    
    assert path == "tasks/open/inbox.md"
    p = tmp_path / path
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "# Task Review Inbox" in content
    assert "Review captured item: Unclear item (kind: unknown, active_task_id: 5) - Evidence: some inline context line 2" in content


def test_resolve_active_message_id(tmp_path: Path) -> None:
    # No events file
    assert resolve_active_message_id(tmp_path) is None
    
    toas_dir = tmp_path / ".toas"
    toas_dir.mkdir(parents=True)
    events_file = toas_dir / "events.jsonl"
    
    # Empty file
    events_file.write_text("", encoding="utf-8")
    assert resolve_active_message_id(tmp_path) is None
    
    # Write events
    events = [
        {"id": "n1", "role": "user", "content": "hello", "parent": None},
        {"id": "n2", "role": "assistant", "content": "hi", "parent": "n1"},
    ]
    events_file.write_text(
        "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8"
    )
    
    assert resolve_active_message_id(tmp_path) == "n2"


def test_route_and_capture_inbox_no_title(tmp_path: Path) -> None:
    res = route_and_capture(
        workspace_root=tmp_path,
        title="",
        kind="todo",
    )
    
    assert res["ok"]
    assert res["target"] == "inbox"
    assert res["path"] == "tasks/open/inbox.md"
    assert (tmp_path / "tasks" / "events.jsonl").exists()


def test_route_and_capture_macro(tmp_path: Path) -> None:
    res = route_and_capture(
        workspace_root=tmp_path,
        title="Standalone task",
        kind="todo",
        scope_hint="macro",
    )
    
    assert res["ok"]
    assert res["target"] == "macro"
    assert res["path"] == "tasks/open/1-standalone-task.md"
    assert (tmp_path / "tasks" / "open" / "1-standalone-task.md").exists()


def test_route_and_capture_micro(tmp_path: Path) -> None:
    # Create parent task file
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True)
    parent_file = open_dir / "5-parent.md"
    parent_file.write_text("# 5 Parent\n\n## Risks\n", encoding="utf-8")
    
    res = route_and_capture(
        workspace_root=tmp_path,
        title="Possible Risk",
        kind="risk",
        active_task_id="5",
        scope_hint="micro",
    )
    
    assert res["ok"]
    assert res["target"] == "micro"
    assert res["path"] == "tasks/open/5-parent.md"
    
    content = parent_file.read_text(encoding="utf-8")
    assert "## Risks\n- [ ] Possible Risk\n" in content


def test_route_and_capture_blocker(tmp_path: Path) -> None:
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True)
    parent_file = open_dir / "5-parent.md"
    parent_file.write_text("# 5 Parent\n\nGoal description\n", encoding="utf-8")
    
    res = route_and_capture(
        workspace_root=tmp_path,
        title="Blocked on API key",
        kind="blocker",
        blocks_progress=True,
        active_task_id="5",
    )
    
    assert res["ok"]
    assert res["target"] == "blocker"
    assert res["directive"] == "pause"
    assert res["path"] == "tasks/open/6-blocked-on-api-key.md"
    
    assert (open_dir / "6-blocked-on-api-key.md").exists()
    content = parent_file.read_text(encoding="utf-8")
    assert "- **Status:** blocked" in content
    assert "- **Blocked By:** tasks/open/6-blocked-on-api-key.md" in content


def test_route_and_capture_inbox_parent_missing(tmp_path: Path) -> None:
    res = route_and_capture(
        workspace_root=tmp_path,
        title="Possible micro task but missing parent",
        kind="todo",
        active_task_id="999",
        scope_hint="micro",
    )
    
    assert res["ok"]
    assert res["target"] == "inbox"
    assert res["path"] == "tasks/open/inbox.md"


def test_tool_registry_integration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    
    call = {
        "tool_name": "capture_task_thread",
        "args": {
            "title": "My Integrated Task",
            "kind": "todo",
            "evidence": "duplicate function definition",
            "scope_hint": "macro",
        }
    }
    
    assert "capture_task_thread" in REGISTRY
    result = execute_call(call)
    
    assert result["ok"]
    assert result["target"] == "macro"
    assert result["path"] == "tasks/open/1-my-integrated-task.md"


def test_resolve_task_file_edge_cases(tmp_path: Path) -> None:
    adapter = LocalMarkdownAdapter(tmp_path)
    assert adapter._resolve_task_file("") is None
    
    assert adapter._resolve_task_file("tasks/open/nonexistent.md") is None
    
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True)
    test_file = open_dir / "test.md"
    test_file.write_text("hello", encoding="utf-8")
    
    assert adapter._resolve_task_file("tasks/open/test.md") == test_file.resolve()
    assert adapter._resolve_task_file("some_other_dir/test.md") == test_file.resolve()


def test_edit_task_section_edge_cases(tmp_path: Path) -> None:
    adapter = LocalMarkdownAdapter(tmp_path)
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True)
    task_file = open_dir / "1-test.md"
    
    # Next header exists
    task_file.write_text("# 1 test\n\n## Section A\n\n- item A\n\n## Section B\n\n- item B\n", encoding="utf-8")
    assert adapter.edit_task_section("1", "Section A", "item A2")
    content = task_file.read_text(encoding="utf-8")
    assert "## Section A\n\n- item A\n- [ ] item A2\n\n## Section B" in content
    
    # Content doesn't end with \n
    task_file.write_text("# 1 test\n\n## Goal\nSome goal", encoding="utf-8")
    assert adapter.edit_task_section("1", "Risks", "my risk")
    content = task_file.read_text(encoding="utf-8")
    assert content.startswith("# 1 test\n\n## Goal\nSome goal\n\n## Risks\n\n- [ ] my risk\n")


def test_mark_task_blocked_edge_cases(tmp_path: Path) -> None:
    adapter = LocalMarkdownAdapter(tmp_path)
    # Parent missing
    assert not adapter.mark_task_blocked("5", "tasks/open/6.md", "why", "cap1")
    
    # Parent has no H1 header
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True, exist_ok=True)
    parent_file = open_dir / "5-parent.md"
    parent_file.write_text("## No H1\n\nJust goal", encoding="utf-8")
    assert not adapter.mark_task_blocked("5", "tasks/open/6.md", "why", "cap1")


def test_route_to_inbox_edge_cases(tmp_path: Path) -> None:
    adapter = LocalMarkdownAdapter(tmp_path)
    long_evidence = "A" * 100
    path = adapter.route_to_inbox("Unclear", "unknown", long_evidence)
    p = tmp_path / path
    content = p.read_text(encoding="utf-8")
    truncated = "A" * 77 + "..."
    assert truncated in content


def test_resolve_active_message_id_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import toas.tasks
    # Make events file exist but mock read_log to fail
    toas_dir = tmp_path / ".toas"
    toas_dir.mkdir(parents=True)
    (toas_dir / "events.jsonl").write_text("{}", encoding="utf-8")
    
    def mock_read_log(path: str):
        raise ValueError("corrupt")
        
    monkeypatch.setattr(toas.tasks, "read_log", mock_read_log)
    assert resolve_active_message_id(tmp_path) is None


def test_route_and_capture_edge_cases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Blocks progress but no active task id -> inbox
    res = route_and_capture(tmp_path, "Blocked", "blocker", blocks_progress=True)
    assert res["target"] == "inbox"
    
    # Create parent task for subsequent tests
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True, exist_ok=True)
    parent_file = open_dir / "5-parent.md"
    parent_file.write_text("# 5 Parent\n\n## Unknowns\n\n", encoding="utf-8")
    
    # 2. active_task_id present, kind="feature", scope_hint="" -> target="macro"
    res = route_and_capture(tmp_path, "New Feature", "feature", active_task_id="5")
    assert res["target"] == "macro"
    
    # 3. kind="unknown", micro -> insert under Unknowns
    res = route_and_capture(tmp_path, "Unknown Item", "unknown", active_task_id="5", scope_hint="micro")
    assert res["target"] == "micro"
    content = parent_file.read_text(encoding="utf-8")
    assert "## Unknowns\n\n- [ ] Unknown Item" in content
    
    # 4. micro with evidence -> title (evidence_first_line)
    parent_file.write_text("# 5 Parent\n\n## Next Actions\n\n", encoding="utf-8")
    res = route_and_capture(tmp_path, "Action Item", "todo", active_task_id="5", scope_hint="micro", evidence="first line\nsecond line")
    assert res["target"] == "micro"
    content = parent_file.read_text(encoding="utf-8")
    assert "- [ ] Action Item (first line)" in content
    
    # 5. micro but editing fails -> inbox
    parent_file.write_text("# 5 Parent\n\n## Next Actions\n\n", encoding="utf-8")
    monkeypatch.setattr(LocalMarkdownAdapter, "edit_task_section", lambda *args, **kwargs: False)
    res = route_and_capture(tmp_path, "Failing item", "todo", active_task_id="5", scope_hint="micro")
    assert res["target"] == "inbox"
    
    # 6. Blocker with evidence -> why_blocked has first line of evidence
    res = route_and_capture(tmp_path, "Blocked on database", "blocker", blocks_progress=True, active_task_id="5", evidence="db credentials missing\ncheck config")
    assert res["target"] == "blocker"
    content = parent_file.read_text(encoding="utf-8")
    assert "- **Why Blocked:** Blocked on database - db credentials missing" in content
    
    # 7. Blocker but parent marking fails (parent lacks H1)
    parent_file.write_text("## No H1", encoding="utf-8")
    res = route_and_capture(tmp_path, "Blocked again", "blocker", blocks_progress=True, active_task_id="5")
    assert res["target"] == "inbox"


def test_task_capture_dataclasses_validation() -> None:
    from toas.tasks import TaskCapturePayload, TaskCaptureOutcome, TaskCaptureEvent
    
    # 1. Payload validation
    with pytest.raises(TypeError, match="title must be a string"):
        TaskCapturePayload(title=123, kind="todo").validate()  # type: ignore
    with pytest.raises(TypeError, match="kind must be a string"):
        TaskCapturePayload(title="A", kind=123).validate()  # type: ignore
    with pytest.raises(TypeError, match="evidence must be a string"):
        TaskCapturePayload(title="A", kind="todo", evidence=123).validate()  # type: ignore
    with pytest.raises(TypeError, match="blocks_progress must be a boolean"):
        TaskCapturePayload(title="A", kind="todo", blocks_progress="yes").validate()  # type: ignore
    with pytest.raises(TypeError, match="active_task_id must be a string or None"):
        TaskCapturePayload(title="A", kind="todo", active_task_id=123).validate()  # type: ignore
    with pytest.raises(TypeError, match="scope_hint must be a string"):
        TaskCapturePayload(title="A", kind="todo", scope_hint=123).validate()  # type: ignore

    # 2. Outcome validation
    with pytest.raises(TypeError, match="target must be a string"):
        TaskCaptureOutcome(target=123, file_path="a", directive="b", summary="c").validate()  # type: ignore
    with pytest.raises(TypeError, match="file_path must be a string"):
        TaskCaptureOutcome(target="a", file_path=123, directive="b", summary="c").validate()  # type: ignore
    with pytest.raises(TypeError, match="directive must be a string"):
        TaskCaptureOutcome(target="a", file_path="b", directive=123, summary="c").validate()  # type: ignore
    with pytest.raises(TypeError, match="summary must be a string"):
        TaskCaptureOutcome(target="a", file_path="b", directive="c", summary=123).validate()  # type: ignore
    with pytest.raises(TypeError, match="active_message_id must be a string or None"):
        TaskCaptureOutcome(target="a", file_path="b", directive="c", summary="d", active_message_id=123).validate()  # type: ignore

    # 3. Event validation
    p = TaskCapturePayload("A", "todo")
    o = TaskCaptureOutcome("macro", "path", "continue", "summary")
    with pytest.raises(TypeError, match="capture_id must be a string"):
        TaskCaptureEvent(capture_id=123, timestamp="time", payload=p, outcome=o).validate()  # type: ignore
    with pytest.raises(TypeError, match="timestamp must be a string"):
        TaskCaptureEvent(capture_id="id", timestamp=123, payload=p, outcome=o).validate()  # type: ignore
    with pytest.raises(TypeError, match="version must be a string"):
        TaskCaptureEvent(capture_id="id", timestamp="time", payload=p, outcome=o, version=123).validate()  # type: ignore
    with pytest.raises(TypeError, match="payload must be a TaskCapturePayload"):
        TaskCaptureEvent(capture_id="id", timestamp="time", payload=123, outcome=o).validate()  # type: ignore
    with pytest.raises(TypeError, match="outcome must be a TaskCaptureOutcome"):
        TaskCaptureEvent(capture_id="id", timestamp="time", payload=p, outcome=123).validate()  # type: ignore

    # 4. dict serialization & deserialization
    e = TaskCaptureEvent(capture_id="id", timestamp="time", payload=p, outcome=o)
    d = e.to_dict()
    assert d["capture_id"] == "id"
    assert d["payload"]["title"] == "A"
    assert d["outcome"]["target"] == "macro"
    
    e2 = TaskCaptureEvent.from_dict(d)
    assert e2.capture_id == "id"
    assert e2.payload.title == "A"
    assert e2.outcome.target == "macro"
    assert e2.version == "1"

    # edge cases of from_dict
    with pytest.raises(TypeError, match="event data must be a dictionary"):
        TaskCaptureEvent.from_dict(123)  # type: ignore
    with pytest.raises(TypeError, match="payload must be a dictionary"):
        TaskCaptureEvent.from_dict({"capture_id": "id", "timestamp": "time", "payload": 123})
    with pytest.raises(TypeError, match="outcome must be a dictionary"):
        TaskCaptureEvent.from_dict({"capture_id": "id", "timestamp": "time", "payload": {}, "outcome": 123})


def test_route_and_capture_idempotency_and_recovery(tmp_path: Path) -> None:
    # 1. Macro capture idempotency (Standalone task)
    res1 = route_and_capture(tmp_path, "Clean task", "cleanup", scope_hint="macro")
    assert res1["ok"]
    assert res1["target"] == "macro"
    p1 = tmp_path / res1["path"]
    assert p1.exists()

    # Read events file
    events_file = tmp_path / "tasks" / "events.jsonl"
    assert events_file.exists()
    lines_before = events_file.read_text(encoding="utf-8").splitlines()
    assert len(lines_before) == 1

    # Second call - completely identical (idempotency signature match)
    res2 = route_and_capture(tmp_path, "Clean task", "cleanup", scope_hint="macro")
    assert res2["ok"]
    assert res2["capture_id"] == res1["capture_id"]
    assert res2["path"] == res1["path"]

    lines_after = events_file.read_text(encoding="utf-8").splitlines()
    assert len(lines_after) == 1  # No duplicate events logged

    # 2. Rollback recovery (Standalone task file deleted)
    p1.unlink()
    assert not p1.exists()

    res3 = route_and_capture(tmp_path, "Clean task", "cleanup", scope_hint="macro")
    assert res3["ok"]
    assert res3["capture_id"] == res1["capture_id"]
    assert p1.exists()  # Recreated!
    
    lines_after_recovery = events_file.read_text(encoding="utf-8").splitlines()
    assert len(lines_after_recovery) == 1  # Still no duplicate events logged

    # 3. Micro task checklists idempotency and recovery
    # Setup parent task
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True, exist_ok=True)
    parent_file = open_dir / "10-parent.md"
    parent_file.write_text("# 10 Parent\n\n## Next Actions\n\n", encoding="utf-8")

    res_micro1 = route_and_capture(tmp_path, "Sub action", "todo", active_task_id="10", scope_hint="micro")
    assert res_micro1["ok"]
    assert res_micro1["target"] == "micro"
    
    content = parent_file.read_text(encoding="utf-8")
    assert "## Next Actions\n\n- [ ] Sub action" in content

    # Second call micro
    res_micro2 = route_and_capture(tmp_path, "Sub action", "todo", active_task_id="10", scope_hint="micro")
    assert res_micro2["ok"]
    assert res_micro2["capture_id"] == res_micro1["capture_id"]
    # Check it was not duplicated in file
    content = parent_file.read_text(encoding="utf-8")
    assert content.count("- [ ] Sub action") == 1

    # Micro task recovery (checklist item deleted from file)
    parent_file.write_text("# 10 Parent\n\n## Next Actions\n\n", encoding="utf-8")
    res_micro3 = route_and_capture(tmp_path, "Sub action", "todo", active_task_id="10", scope_hint="micro")
    assert res_micro3["ok"]
    assert res_micro3["capture_id"] == res_micro1["capture_id"]
    content = parent_file.read_text(encoding="utf-8")
    assert "- [ ] Sub action" in content  # Recreated!

    # 4. Inbox idempotency and recovery
    res_inb1 = route_and_capture(tmp_path, "", "todo")  # No title -> routes to inbox
    assert res_inb1["ok"]
    assert res_inb1["target"] == "inbox"
    
    inbox_file = tmp_path / "tasks" / "open" / "inbox.md"
    assert inbox_file.exists()
    
    # Second call inbox
    res_inb2 = route_and_capture(tmp_path, "", "todo")
    assert res_inb2["ok"]
    assert res_inb2["capture_id"] == res_inb1["capture_id"]
    
    # Inbox recovery
    inbox_file.unlink()
    res_inb3 = route_and_capture(tmp_path, "", "todo")
    assert res_inb3["ok"]
    assert inbox_file.exists()


def test_route_and_capture_explicit_capture_id(tmp_path: Path) -> None:
    # Pass explicit capture_id
    my_id = "cap_custom123"
    res1 = route_and_capture(tmp_path, "Explicit task", "cleanup", capture_id=my_id)
    assert res1["ok"]
    assert res1["capture_id"] == my_id
    
    # Idempotent match using capture_id
    res2 = route_and_capture(tmp_path, "Explicit task", "cleanup", capture_id=my_id)
    assert res2["ok"]
    assert res2["capture_id"] == my_id


def test_permissive_ledger_parsing(tmp_path: Path) -> None:
    # Create events file with some corrupt JSON lines
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = tasks_dir / "events.jsonl"
    ledger_path.write_text("{invalid json}\n\n", encoding="utf-8")

    # Run capture - should not crash, should parse permissively
    res = route_and_capture(tmp_path, "Robust task", "cleanup")
    assert res["ok"]
    assert ledger_path.exists()


def test_verify_physical_event_edge_cases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from toas.tasks import TaskCapturePayload, TaskCaptureOutcome, TaskCaptureEvent, LocalMarkdownAdapter
    
    adapter = LocalMarkdownAdapter(tmp_path)
    
    # 1. Empty file path
    payload = TaskCapturePayload("T", "todo")
    outcome = TaskCaptureOutcome("macro", "", "continue", "sum")
    event = TaskCaptureEvent("cap1", "time", payload, outcome)
    assert not adapter.verify_physical_event(event)

    # 2. Unknown target
    outcome2 = TaskCaptureOutcome("unknown_target", "tasks/open/inbox.md", "continue", "sum")
    event2 = TaskCaptureEvent("cap1", "time", payload, outcome2)
    inbox_file = tmp_path / "tasks" / "open" / "inbox.md"
    inbox_file.parent.mkdir(parents=True, exist_ok=True)
    inbox_file.write_text("hello")
    assert not adapter.verify_physical_event(event2)

    # 3. Micro with evidence and read failure
    payload_micro = TaskCapturePayload("Sub", "todo", evidence="some evidence line\nline 2", active_task_id="10")
    outcome_micro = TaskCaptureOutcome("micro", "tasks/open/10-parent.md", "continue", "sum")
    event_micro = TaskCaptureEvent("cap1", "time", payload_micro, outcome_micro)
    
    parent_file = tmp_path / "tasks" / "open" / "10-parent.md"
    parent_file.write_text("# 10 Parent\n\n## Next Actions\n\n- [ ] Sub (some evidence line)\n")
    assert adapter.verify_physical_event(event_micro)

    # Read failure on micro
    def mock_read_text(*args, **kwargs):
        raise IOError("permission denied")
    monkeypatch.setattr(Path, "read_text", mock_read_text)
    assert not adapter.verify_physical_event(event_micro)
    monkeypatch.undo()

    # 4. Inbox with long evidence and read failure
    payload_inb = TaskCapturePayload("Inb", "todo", evidence="A" * 100, active_task_id="10")
    outcome_inb = TaskCaptureOutcome("inbox", "tasks/open/inbox.md", "continue", "sum")
    event_inb = TaskCaptureEvent("cap1", "time", payload_inb, outcome_inb)
    
    inbox_file.write_text(f"- [ ] Review captured item: Inb (kind: todo, active_task_id: 10) - Evidence: {'A'*77}...\n")
    assert adapter.verify_physical_event(event_inb)

    # Read failure on inbox
    monkeypatch.setattr(Path, "read_text", mock_read_text)
    assert not adapter.verify_physical_event(event_inb)


def test_route_and_capture_syncs_workboard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Create a dummy WORKBOARD.md in tmp_path
    workboard_file = tmp_path / "tasks" / "WORKBOARD.md"
    workboard_file.parent.mkdir(parents=True, exist_ok=True)
    initial_content = """# Workboard

## 0. Manual Triage
### Relationship Roots
<!-- WORKBOARD:RELATIONSHIP_ROOTS:START -->
- `1-clean-code`
<!-- WORKBOARD:RELATIONSHIP_ROOTS:END -->

### Active Arc Map
<!-- WORKBOARD:RELATIONSHIP_TREE:START -->
<!-- WORKBOARD:RELATIONSHIP_TREE:END -->

## 1. Now
<!-- WORKBOARD:NOW:START -->
<!-- WORKBOARD:NOW:END -->

## 2. Task Inbox
<!-- WORKBOARD:INBOX:START -->
<!-- WORKBOARD:INBOX:END -->

## 3. Recent Closures
<!-- WORKBOARD:CLOSED:START -->
<!-- WORKBOARD:CLOSED:END -->
"""
    workboard_file.write_text(initial_content, encoding="utf-8")

    # Copy sync_workboard.py into tmp_path so it can run
    scripts_dir = tmp_path / "tasks" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    original_script_path = Path(__file__).resolve().parent.parent / "tasks" / "scripts" / "sync_workboard.py"
    
    script_content = original_script_path.read_text(encoding="utf-8")
    (scripts_dir / "sync_workboard.py").write_text(script_content, encoding="utf-8")

    # 2. Run route_and_capture for standalone task
    res = route_and_capture(tmp_path, "Clean code", "cleanup", scope_hint="macro")
    assert res["ok"]
    
    # Assert WORKBOARD.md has the standalone task synced under NOW
    wb_content = workboard_file.read_text(encoding="utf-8")
    assert "- **[T1-clean-code]** Clean code" in wb_content
    assert "- 1-clean-code Clean code" in wb_content

    # 3. Run route_and_capture for inbox item
    res_inb = route_and_capture(tmp_path, "", "todo") # Empty title -> inbox
    assert res_inb["ok"]
    
    # Assert WORKBOARD.md has the inbox item synced under Task Inbox
    wb_content_2 = workboard_file.read_text(encoding="utf-8")
    assert "- **[Inbox]** Review captured item:  (kind: todo)" in wb_content_2

    # 4. Trigger exception in _sync_workboard
    import subprocess
    def mock_run(*args, **kwargs):
        raise RuntimeError("simulated sync error")
    monkeypatch.setattr(subprocess, "run", mock_run)
    res_err = route_and_capture(tmp_path, "Error task", "cleanup", scope_hint="macro")
    assert res_err["ok"]

def test_sync_workboard_helpers_relationship_roots_and_tree(tmp_path: Path) -> None:
    module = _load_sync_workboard_module()

    root = tmp_path / "260614-root.md"
    root.write_text(
        "\n".join(
            [
                "Filed as: 260614-root",
                "FKA:",
                "AKA:",
                "Legacy index:",
                "",
                "# Root",
                "",
                "## Goal",
                "Coordinate the tree",
            ]
        ),
        encoding="utf-8",
    )
    child = tmp_path / "260615-child.md"
    child.write_text(
        "\n".join(
            [
                "Filed as: 260615-child",
                "FKA:",
                "AKA:",
                "Legacy index:",
                "Parent: `260614-root`",
                "Blocked by: `260620-prereq`; `260621-other`",
                "Blocks: `260630-next`",
                "Related: `400`; `260624-adjacent`",
                "",
                "# Child",
                "",
                "## Goal",
                "Implement the child slice",
            ]
        ),
        encoding="utf-8",
    )
    closed = tmp_path / "260620-prereq.md"
    closed.write_text(
        "\n".join(
            [
                "Filed as: 260620-prereq",
                "FKA:",
                "AKA:",
                "Legacy index:",
                "",
                "# Prereq",
                "",
                "## Goal",
                "Already closed",
            ]
        ),
        encoding="utf-8",
    )

    parsed_child = module.parse_task(child)
    assert parsed_child is not None
    assert parsed_child.parent == "260614-root"
    assert parsed_child.blocked_by == ["260620-prereq", "260621-other"]
    assert parsed_child.blocks == ["260630-next"]
    assert parsed_child.related == ["400", "260624-adjacent"]

    roots = module.extract_relationship_roots(
        "\n".join(
            [
                "before",
                "<!-- WORKBOARD:RELATIONSHIP_ROOTS:START -->",
                "- `260614-root`",
                "- `260699-missing`",
                "<!-- WORKBOARD:RELATIONSHIP_ROOTS:END -->",
                "after",
            ]
        )
    )
    assert roots == ["260614-root", "260699-missing"]

    open_tasks = [module.parse_task(root), parsed_child]
    relationship_tree = module.build_relationship_tree(
        roots,
        open_tasks,
        [module.parse_task(closed)],
    )
    assert "- 260614-root Coordinate the tree" in relationship_tree
    assert "260615-child Implement the child slice" in relationship_tree
    assert "blocked by `260620-prereq`, `260621-other`" in relationship_tree
    assert "blocks `260630-next`" in relationship_tree
    assert "related `400`, `260624-adjacent`" in relationship_tree
    assert "Warning: root `260699-missing` not rendered (missing task)." in relationship_tree


def test_sync_workboard_reuses_first_mention_as_at_reference(tmp_path: Path) -> None:
    module = _load_sync_workboard_module()

    first = module.TaskRecord(
        id="260614-root",
        title="260614-root",
        objective="Root task",
        path=tmp_path / "260614-root.md",
    )
    second = module.TaskRecord(
        id="260615-other-root",
        title="260615-other-root",
        objective="Other root",
        path=tmp_path / "260615-other-root.md",
    )
    shared = module.TaskRecord(
        id="260616-shared",
        title="260616-shared",
        objective="Shared child",
        path=tmp_path / "260616-shared.md",
        parent="260614-root",
    )

    relationship_tree = module.build_relationship_tree(
        ["260614-root", "260616-shared", "260615-other-root"],
        [first, second, shared],
        [],
    )
    assert relationship_tree.count("260616-shared Shared child") == 1
    assert "`@260616-shared`" in relationship_tree


def test_markdown_document_unit_and_blocker_idempotency(tmp_path: Path) -> None:
    adapter = LocalMarkdownAdapter(tmp_path)
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True, exist_ok=True)
    task_file = open_dir / "1-test.md"

    # 1. Nested list indentation matching
    task_file.write_text("# 1 test\n\n## Section A\n  - item 1\n", encoding="utf-8")
    assert adapter.edit_task_section("1", "Section A", "item 2")
    content = task_file.read_text(encoding="utf-8")
    assert "## Section A\n  - item 1\n  - [ ] item 2\n" in content

    # 2. Section with no list items but paragraph content
    task_file.write_text("# 1 test\n\n## Section A\nSome paragraph text here.\n", encoding="utf-8")
    assert adapter.edit_task_section("1", "Section A", "item 2")
    content = task_file.read_text(encoding="utf-8")
    assert "## Section A\nSome paragraph text here.\n\n- [ ] item 2\n" in content

    # 3. Section completely empty
    task_file.write_text("# 1 test\n\n## Section A\n\n\n", encoding="utf-8")
    assert adapter.edit_task_section("1", "Section A", "item 2")
    content = task_file.read_text(encoding="utf-8")
    assert "## Section A\n\n- [ ] item 2\n" in content

    # 4. mark_task_blocked idempotency / replacement
    task_file.write_text("# 1 test\n\n## Goal\nSome goal\n", encoding="utf-8")
    assert adapter.mark_task_blocked("1", "tasks/open/2.md", "why 1", "cap1")
    content1 = task_file.read_text(encoding="utf-8")
    assert "- **Status:** blocked\n- **Blocked By:** tasks/open/2.md\n- **Why Blocked:** why 1\n" in content1

    # Call again with updated blocker - should replace old block instead of duplicating
    assert adapter.mark_task_blocked("1", "tasks/open/3.md", "why 2", "cap2")
    content2 = task_file.read_text(encoding="utf-8")
    assert "- **Status:** blocked\n- **Blocked By:** tasks/open/3.md\n- **Why Blocked:** why 2\n" in content2
    assert "- **Blocked By:** tasks/open/2.md" not in content2
    assert content2.count("Status:") == 1

    # 5. Coverage for empty lines pop when section doesn't exist
    task_file.write_text("# 1 test\n\n\n", encoding="utf-8")
    assert adapter.edit_task_section("1", "Section C", "item C")
    content3 = task_file.read_text(encoding="utf-8")
    assert content3 == "# 1 test\n\n## Section C\n\n- [ ] item C\n"

    # 6. Coverage for MarkdownDocument empty serialize and invalid level in get_section_bounds
    from toas.tasks import MarkdownDocument
    doc_empty = MarkdownDocument("")
    assert doc_empty.serialize() == ""

    doc_invalid = MarkdownDocument("# H1")
    assert doc_invalid.get_section_bounds(999) == (1000, 1)
