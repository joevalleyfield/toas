import json
from pathlib import Path
import pytest

from toas.tasks import (
    LocalMarkdownAdapter,
    slugify,
    route_and_capture,
    resolve_active_message_id,
)
from toas.tools import REGISTRY, execute_call


def test_slugify() -> None:
    assert slugify("My Cool Task!") == "my-cool-task"
    assert slugify("  Refactor Codebase  ") == "refactor-codebase"
    assert slugify("!!!") == "task"


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
    assert "## Section A\n\n- item A\n- [ ] item A2\n\n\n## Section B" in content
    
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

