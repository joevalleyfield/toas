import abc
import datetime
import json
import re
import uuid
from pathlib import Path
from typing import Any, Optional

from .graph import bind_parent_id, read_log


class TaskTrackerAdapter(abc.ABC):
    @abc.abstractmethod
    def log_event(self, event_data: dict) -> None:
        """Log the capture event to the ledger."""
        pass

    @abc.abstractmethod
    def get_next_task_id(self) -> int:
        """Return the next unique task ID (1-based integer)."""
        pass

    @abc.abstractmethod
    def edit_task_section(self, task_file: str, section: str, item_text: str) -> bool:
        """Insert a checklist item into a target section of a task markdown file."""
        pass

    @abc.abstractmethod
    def create_standalone_task(
        self,
        task_id: int,
        title: str,
        kind: str,
        evidence: str,
        active_task_id: Optional[str] = None,
        active_message_id: Optional[str] = None,
    ) -> str:
        """Create a new standalone task file and return its relative path."""
        pass

    @abc.abstractmethod
    def mark_task_blocked(
        self,
        parent_task_file: str,
        blocker_task_file: str,
        why_blocked: str,
        capture_id: str,
        active_message_id: Optional[str] = None,
        resume_condition: Optional[str] = None,
        suggested_resume_action: Optional[str] = None,
    ) -> bool:
        """Mark parent task as blocked and inject blocker / resume metadata."""
        pass

    @abc.abstractmethod
    def route_to_inbox(
        self,
        title: str,
        kind: str,
        evidence: str,
        active_task_id: Optional[str] = None,
    ) -> str:
        """Route to a review inbox task (e.g. tasks/open/inbox.md) and return path."""
        pass


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "task"


class LocalMarkdownAdapter(TaskTrackerAdapter):
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()

    def log_event(self, event_data: dict) -> None:
        tasks_dir = self.workspace_root / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        ledger_path = tasks_dir / "events.jsonl"
        with ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event_data) + "\n")

    def get_next_task_id(self) -> int:
        open_dir = self.workspace_root / "tasks" / "open"
        if not open_dir.exists():
            return 1
        max_id = 0
        for p in open_dir.glob("*.md"):
            match = re.match(r"^(\d+)-", p.name)
            if match:
                try:
                    val = int(match.group(1))
                    if val > max_id:
                        max_id = val
                except ValueError:
                    continue
        return max_id + 1

    def _resolve_task_file(self, task_id_or_file: str) -> Optional[Path]:
        if not task_id_or_file:
            return None
        # If it looks like a path already (contains slashes or ends with .md)
        if "/" in task_id_or_file or task_id_or_file.endswith(".md"):
            p = self.workspace_root / task_id_or_file
            if p.exists():
                return p.resolve()
            name = Path(task_id_or_file).name
            p = self.workspace_root / "tasks" / "open" / name
            if p.exists():
                return p.resolve()
            return None

        # Numeric search
        open_dir = self.workspace_root / "tasks" / "open"
        if not open_dir.exists():
            return None
        for p in open_dir.glob("*.md"):
            match = re.match(r"^(\d+)-", p.name)
            if match and match.group(1) == str(task_id_or_file):
                return p.resolve()
            if p.stem == str(task_id_or_file):
                return p.resolve()
        return None

    def edit_task_section(self, task_file: str, section: str, item_text: str) -> bool:
        p = self._resolve_task_file(task_file)
        if not p or not p.exists():
            return False

        content = p.read_text(encoding="utf-8")
        
        pattern = rf"(?:^|\n)(#+)\s*{re.escape(section)}\s*\n"
        match = re.search(pattern, content, re.IGNORECASE)
        
        if match:
            header_level_hashes = match.group(1)
            start_idx = match.end()
            
            next_header_pattern = rf"\n#{{1,{len(header_level_hashes)}}}\s"
            next_match = re.search(next_header_pattern, content[start_idx:])
            
            if next_match:
                end_idx = start_idx + next_match.start()
            else:
                end_idx = len(content)
                
            section_content = content[start_idx:end_idx]
            
            trimmed = section_content.rstrip("\n")
            if trimmed:
                new_section_content = trimmed + f"\n- [ ] {item_text}\n"
            else:
                new_section_content = f"- [ ] {item_text}\n"
                
            suffix = section_content[len(trimmed):]
            new_content = content[:start_idx] + new_section_content + suffix + content[end_idx:]
        else:
            if content and not content.endswith("\n"):
                content += "\n"
            new_content = content + f"\n## {section}\n\n- [ ] {item_text}\n"
            
        p.write_text(new_content, encoding="utf-8")
        return True

    def create_standalone_task(
        self,
        task_id: int,
        title: str,
        kind: str,
        evidence: str,
        active_task_id: Optional[str] = None,
        active_message_id: Optional[str] = None,
    ) -> str:
        open_dir = self.workspace_root / "tasks" / "open"
        open_dir.mkdir(parents=True, exist_ok=True)
        
        slug = slugify(title)
        filename = f"{task_id}-{slug}.md"
        file_path = open_dir / filename
        
        kw_line = f"keywords: {kind}, captured"
        if active_message_id:
            kw_line += f", active_message_id={active_message_id}"
            
        why_text = "Captured from active execution thread."
        if active_task_id:
            why_text = f"Captured during execution of active task {active_task_id}."
            
        evidence_block = ""
        if evidence:
            evidence_block = f"\n## Evidence\n\n{evidence}\n"
            
        content = f"""# {task_id} {title}
{kw_line}

## Goal

{title}

## Why

{why_text}

## Scope

- [ ] Implement {title}
{evidence_block}"""
        
        file_path.write_text(content, encoding="utf-8")
        return f"tasks/open/{filename}"

    def mark_task_blocked(
        self,
        parent_task_file: str,
        blocker_task_file: str,
        why_blocked: str,
        capture_id: str,
        active_message_id: Optional[str] = None,
        resume_condition: Optional[str] = None,
        suggested_resume_action: Optional[str] = None,
    ) -> bool:
        p = self._resolve_task_file(parent_task_file)
        if not p or not p.exists():
            return False
            
        content = p.read_text(encoding="utf-8")
        
        h1_match = re.search(r"^(#\s+[^\n]+)", content)
        if not h1_match:
            return False
            
        h1_line = h1_match.group(1)
        
        cond = resume_condition or f"Blocker task at {blocker_task_file} is completed."
        act = suggested_resume_action or "Verify the blocker is resolved and mark parent task status as active."
        
        metadata_lines = [
            f"- **Status:** blocked",
            f"- **Blocked By:** {blocker_task_file}",
            f"- **Why Blocked:** {why_blocked}",
            f"- **Source Capture ID:** {capture_id}",
        ]
        if active_message_id:
            metadata_lines.append(f"- **Active Message ID:** {active_message_id}")
        metadata_lines.extend([
            f"- **Resume Condition:** {cond}",
            f"- **Suggested Resume Action:** {act}",
        ])
        
        metadata_block = "\n" + "\n".join(metadata_lines) + "\n"
        
        new_content = content[:h1_match.start()] + h1_line + metadata_block + content[h1_match.end():]
        p.write_text(new_content, encoding="utf-8")
        return True

    def route_to_inbox(
        self,
        title: str,
        kind: str,
        evidence: str,
        active_task_id: Optional[str] = None,
    ) -> str:
        open_dir = self.workspace_root / "tasks" / "open"
        open_dir.mkdir(parents=True, exist_ok=True)
        
        inbox_path = open_dir / "inbox.md"
        if not inbox_path.exists():
            initial_content = """# Task Review Inbox

This file tracks low-confidence task capture events for manual review.

## Items

"""
            inbox_path.write_text(initial_content, encoding="utf-8")
            
        content = inbox_path.read_text(encoding="utf-8")
        
        parent_suffix = f", active_task_id: {active_task_id}" if active_task_id else ""
        item_text = f"Review captured item: {title} (kind: {kind}{parent_suffix})"
        if evidence:
            ev_summary = evidence.strip().replace("\n", " ")
            if len(ev_summary) > 80:
                ev_summary = ev_summary[:77] + "..."
            item_text += f" - Evidence: {ev_summary}"
            
        self.edit_task_section("tasks/open/inbox.md", "Items", item_text)
        return "tasks/open/inbox.md"


def resolve_active_message_id(workspace_root: Path) -> Optional[str]:
    preferred = workspace_root / ".toas" / "events.jsonl"
    legacy = workspace_root / "events.jsonl"
    events_path = preferred if preferred.exists() else (legacy if legacy.exists() else preferred)
    
    if not events_path.exists():
        return None
        
    try:
        events = read_log(str(events_path))
        return bind_parent_id(events, None)
    except Exception:
        return None


def route_and_capture(
    workspace_root: Path,
    title: str,
    kind: str,
    evidence: str = "",
    blocks_progress: bool = False,
    active_task_id: Optional[str] = None,
    scope_hint: str = "",
) -> dict:
    adapter = LocalMarkdownAdapter(workspace_root)
    capture_id = f"cap_{uuid.uuid4().hex[:12]}"
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    active_message_id = resolve_active_message_id(workspace_root)
    
    target = "macro"
    
    if not title.strip():
        target = "inbox"
    elif blocks_progress:
        if active_task_id:
            target = "blocker"
        else:
            target = "inbox"
    elif scope_hint.lower() in ("micro", "node") or (
        kind.lower()
        in ("risk", "risks", "unknown", "unknowns", "todo", "next_actions", "next_action", "cleanup")
        and active_task_id
        and scope_hint.lower() not in ("macro", "standalone")
    ):
        target = "micro"
    elif scope_hint.lower() in ("macro", "standalone") or not active_task_id:
        target = "macro"
    else:
        target = "macro"
        
    parent_path = None
    if target in ("micro", "blocker") and active_task_id:
        parent_file = adapter._resolve_task_file(active_task_id)
        if not parent_file or not parent_file.exists():
            target = "inbox"
        else:
            parent_path = str(parent_file.relative_to(adapter.workspace_root))
            
    file_path = ""
    directive = "continue"
    summary = ""
    
    if target == "inbox":
        file_path = adapter.route_to_inbox(title, kind, evidence, active_task_id)
        summary = f"Routed low-confidence task to review inbox: {file_path}"
    elif target == "micro":
        kind_lower = kind.lower()
        if kind_lower in ("risk", "risks"):
            section = "Risks"
        elif kind_lower in ("unknown", "unknowns"):
            section = "Unknowns"
        else:
            section = "Next Actions"
            
        item_text = title
        if evidence:
            ev_line = evidence.strip().splitlines()[0] if evidence.strip() else ""
            if ev_line:
                item_text += f" ({ev_line})"
                
        success = adapter.edit_task_section(active_task_id, section, item_text)
        if success:
            file_path = parent_path or ""
            summary = f"Appended checklist item under section {section} in active task {active_task_id}"
        else:
            target = "inbox"
            file_path = adapter.route_to_inbox(title, kind, evidence, active_task_id)
            summary = f"Editing active task failed, routed task to review inbox: {file_path}"
    elif target == "macro":
        task_id = adapter.get_next_task_id()
        file_path = adapter.create_standalone_task(
            task_id, title, kind, evidence, active_task_id, active_message_id
        )
        summary = f"Created standalone task {task_id}: {file_path}"
    elif target == "blocker":
        task_id = adapter.get_next_task_id()
        blocker_path = adapter.create_standalone_task(
            task_id, title, kind, evidence, active_task_id, active_message_id
        )
        
        why = title
        if evidence:
            why += f" - {evidence.strip().splitlines()[0]}"
            
        success = adapter.mark_task_blocked(
            parent_task_file=active_task_id,
            blocker_task_file=blocker_path,
            why_blocked=why,
            capture_id=capture_id,
            active_message_id=active_message_id,
        )
        
        if success:
            file_path = blocker_path
            directive = "pause"
            summary = f"Created blocker task {task_id} and marked parent task {active_task_id} blocked"
        else:
            target = "inbox"
            file_path = adapter.route_to_inbox(title, kind, evidence, active_task_id)
            summary = f"Failed to mark parent task blocked, routed task to review inbox: {file_path}"
            
    event_data = {
        "capture_id": capture_id,
        "timestamp": timestamp,
        "payload": {
            "title": title,
            "kind": kind,
            "evidence": evidence,
            "blocks_progress": blocks_progress,
            "active_task_id": active_task_id,
            "scope_hint": scope_hint,
        },
        "outcome": {
            "target": target,
            "file_path": file_path,
            "directive": directive,
            "summary": summary,
            "active_message_id": active_message_id,
        },
    }
    adapter.log_event(event_data)
    
    return {
        "tool_name": "capture_task_thread",
        "ok": True,
        "summary": summary,
        "directive": directive,
        "capture_id": capture_id,
        "target": target,
        "path": file_path,
    }
