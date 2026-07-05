import abc
import datetime
import json
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from .graph import bind_parent_id, read_log


@dataclass
class TaskCapturePayload:
    title: str
    kind: str
    evidence: str = ""
    blocks_progress: bool = False
    active_task_id: str | None = None
    scope_hint: str = ""

    def validate(self) -> None:
        if not isinstance(self.title, str):
            raise TypeError("title must be a string")
        if not isinstance(self.kind, str):
            raise TypeError("kind must be a string")
        if not isinstance(self.evidence, str):
            raise TypeError("evidence must be a string")
        if not isinstance(self.blocks_progress, bool):
            raise TypeError("blocks_progress must be a boolean")
        if self.active_task_id is not None and not isinstance(self.active_task_id, str):
            raise TypeError("active_task_id must be a string or None")
        if not isinstance(self.scope_hint, str):
            raise TypeError("scope_hint must be a string")


@dataclass
class TaskCaptureOutcome:
    target: str
    file_path: str
    directive: str
    summary: str
    active_message_id: str | None = None

    def validate(self) -> None:
        if not isinstance(self.target, str):
            raise TypeError("target must be a string")
        if not isinstance(self.file_path, str):
            raise TypeError("file_path must be a string")
        if not isinstance(self.directive, str):
            raise TypeError("directive must be a string")
        if not isinstance(self.summary, str):
            raise TypeError("summary must be a string")
        if self.active_message_id is not None and not isinstance(self.active_message_id, str):
            raise TypeError("active_message_id must be a string or None")


@dataclass
class TaskCaptureEvent:
    capture_id: str
    timestamp: str
    payload: TaskCapturePayload
    outcome: TaskCaptureOutcome
    version: str = "1"

    def validate(self) -> None:
        if not isinstance(self.capture_id, str):
            raise TypeError("capture_id must be a string")
        if not isinstance(self.timestamp, str):
            raise TypeError("timestamp must be a string")
        if not isinstance(self.version, str):
            raise TypeError("version must be a string")
        if not isinstance(self.payload, TaskCapturePayload):
            raise TypeError("payload must be a TaskCapturePayload")
        if not isinstance(self.outcome, TaskCaptureOutcome):
            raise TypeError("outcome must be a TaskCaptureOutcome")
        self.payload.validate()
        self.outcome.validate()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskCaptureEvent":
        if not isinstance(data, dict):
            raise TypeError("event data must be a dictionary")
        version = data.get("version", "1")
        p_data = data.get("payload")
        if not isinstance(p_data, dict):
            raise TypeError("payload must be a dictionary")
        payload = TaskCapturePayload(
            title=p_data.get("title", ""),
            kind=p_data.get("kind", ""),
            evidence=p_data.get("evidence", ""),
            blocks_progress=p_data.get("blocks_progress", False),
            active_task_id=p_data.get("active_task_id"),
            scope_hint=p_data.get("scope_hint", ""),
        )
        o_data = data.get("outcome")
        if not isinstance(o_data, dict):
            raise TypeError("outcome must be a dictionary")
        outcome = TaskCaptureOutcome(
            target=o_data.get("target", ""),
            file_path=o_data.get("file_path", ""),
            directive=o_data.get("directive", ""),
            summary=o_data.get("summary", ""),
            active_message_id=o_data.get("active_message_id"),
        )

        event = cls(
            capture_id=data.get("capture_id", ""),
            timestamp=data.get("timestamp", ""),
            payload=payload,
            outcome=outcome,
            version=version,
        )
        event.validate()
        return event


class TaskTrackerAdapter(abc.ABC):
    @abc.abstractmethod
    def log_event(self, event: TaskCaptureEvent) -> None:
        """Log the capture event to the ledger."""
        pass

    @abc.abstractmethod
    def find_existing_event(
        self,
        title: str,
        kind: str,
        active_task_id: str | None,
        capture_id: str | None = None,
    ) -> TaskCaptureEvent | None:
        """Find an existing capture event in the ledger matching the signature or capture_id."""
        pass

    @abc.abstractmethod
    def verify_physical_event(self, event: TaskCaptureEvent) -> bool:
        """Verify if the physical changes of the event exist on the filesystem."""
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
        active_task_id: str | None = None,
        active_message_id: str | None = None,
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
        active_message_id: str | None = None,
        resume_condition: str | None = None,
        suggested_resume_action: str | None = None,
    ) -> bool:
        """Mark parent task as blocked and inject blocker / resume metadata."""
        pass

    @abc.abstractmethod
    def route_to_inbox(
        self,
        title: str,
        kind: str,
        evidence: str,
        active_task_id: str | None = None,
    ) -> str:
        """Route to a review inbox task (e.g. tasks/open/inbox.md) and return path."""
        pass


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "task"


class MarkdownDocument:
    def __init__(self, content: str):
        self.lines = content.splitlines()
        # Parse headers
        self.headers = []  # list of (line_idx, level, title)
        for idx, line in enumerate(self.lines):
            stripped = line.strip()
            # Standard ATX header: 1-6 '#' followed by space
            m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()
                self.headers.append((idx, level, title))

    def find_section(self, section_name: str) -> int | None:
        for idx, _level, title in self.headers:
            if title.lower() == section_name.lower():
                return idx
        return None

    def get_section_bounds(self, header_idx: int) -> tuple[int, int]:
        level = None
        for idx, lvl, _ in self.headers:
            if idx == header_idx:
                level = lvl
                break
        if level is None:
            return header_idx + 1, len(self.lines)

        start_idx = header_idx + 1
        end_idx = len(self.lines)
        for idx, lvl, _ in self.headers:
            if idx > header_idx and lvl <= level:
                end_idx = idx
                break
        return start_idx, end_idx

    def edit_task_section(self, section_name: str, item_text: str) -> None:
        header_idx = self.find_section(section_name)
        if header_idx is not None:
            start_idx, end_idx = self.get_section_bounds(header_idx)
            # Find list items
            list_items = []
            for idx in range(start_idx, end_idx):
                line = self.lines[idx]
                if re.match(r"^\s*([-*+]|\d+\.)(\s|$)", line):
                    list_items.append(idx)
            
            if list_items:
                last_list_idx = list_items[-1]
                # Determine indentation of the list item if possible
                first_list_line = self.lines[list_items[0]]
                indent_match = re.match(r"^(\s*)", first_list_line)
                indent = indent_match.group(1) if indent_match else ""
                self.lines.insert(last_list_idx + 1, f"{indent}- [ ] {item_text}")
            else:
                # No list items. Find last non-blank line in the section
                last_non_blank = None
                for idx in range(start_idx, end_idx):
                    if self.lines[idx].strip() != "":
                        last_non_blank = idx
                
                if last_non_blank is not None:
                    # Insert after the last non-blank line, with a blank line in between
                    self.lines.insert(last_non_blank + 1, "")
                    self.lines.insert(last_non_blank + 2, f"- [ ] {item_text}")
                else:
                    # Section has no non-blank lines.
                    if start_idx == end_idx:
                        # Completely empty section (no lines). Insert immediately after header.
                        self.lines.insert(start_idx, f"- [ ] {item_text}")
                    else:
                        # Only blank lines in range. Replace them with exactly one blank line then list item.
                        del self.lines[start_idx:end_idx]
                        self.lines.insert(start_idx, "")
                        self.lines.insert(start_idx + 1, f"- [ ] {item_text}")
        else:
            # Section not found, append at the bottom
            if self.lines:
                while self.lines and self.lines[-1].strip() == "":
                    self.lines.pop()
                self.lines.append("")
            self.lines.extend([f"## {section_name}", "", f"- [ ] {item_text}"])

    def mark_blocked(self, metadata_lines: list[str]) -> bool:
        # Find H1 header index
        h1_idx = None
        for idx, level, _ in self.headers:
            if level == 1:
                h1_idx = idx
                break
        if h1_idx is None:
            return False

        # Scan forward for existing metadata block starting at h1_idx + 1
        # It's consecutive lines starting with '- **' or similar that match metadata keys
        meta_keys = {"status", "blocked by", "why blocked", "source capture id", "active message id", "resume condition", "suggested resume action"}
        
        insert_idx = h1_idx + 1
        remove_count = 0
        
        # Check if there are existing metadata lines right below H1
        while insert_idx + remove_count < len(self.lines):
            line = self.lines[insert_idx + remove_count]
            m = re.match(r"^\s*-\s+\*\*([^*]+):\*\*\s+.*$", line)
            if m:
                key = m.group(1).strip().lower()
                if key in meta_keys:
                    remove_count += 1
                    continue
            break
        
        # Replace or insert
        new_lines = [f"- {line}" for line in metadata_lines]
        if remove_count > 0:
            self.lines[insert_idx : insert_idx + remove_count] = new_lines
        else:
            self.lines[insert_idx : insert_idx] = new_lines
            
        return True

    def serialize(self) -> str:
        if not self.lines:
            return ""
        return "\n".join(self.lines) + "\n"


class LocalMarkdownAdapter(TaskTrackerAdapter):
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()

    def log_event(self, event: TaskCaptureEvent) -> None:
        tasks_dir = self.workspace_root / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)
        ledger_path = tasks_dir / "events.jsonl"
        with ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    def find_existing_event(
        self,
        title: str,
        kind: str,
        active_task_id: str | None,
        capture_id: str | None = None,
    ) -> TaskCaptureEvent | None:
        tasks_dir = self.workspace_root / "tasks"
        ledger_path = tasks_dir / "events.jsonl"
        if not ledger_path.exists():
            return None

        best_match = None
        with ledger_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    event = TaskCaptureEvent.from_dict(data)
                    if capture_id and event.capture_id == capture_id:
                        return event
                    if (
                        event.payload.title == title
                        and event.payload.kind == kind
                        and event.payload.active_task_id == active_task_id
                    ):
                        best_match = event
                except Exception:
                    continue
        return best_match

    def verify_physical_event(self, event: TaskCaptureEvent) -> bool:
        target = event.outcome.target
        file_path = event.outcome.file_path
        if not file_path:
            return False

        full_path = self.workspace_root / file_path
        if not full_path.exists():
            return False

        if target in ("macro", "blocker"):
            return True

        if target == "micro":
            title = event.payload.title
            evidence = event.payload.evidence
            item_text = title
            if evidence:
                ev_line = evidence.strip().splitlines()[0] if evidence.strip() else ""
                if ev_line:
                    item_text += f" ({ev_line})"

            try:
                content = full_path.read_text(encoding="utf-8")
                pattern = rf"-\s*\[[ xX/]\]\s*{re.escape(item_text)}"
                return bool(re.search(pattern, content))
            except Exception:
                return False

        if target == "inbox":
            title = event.payload.title
            kind = event.payload.kind
            active_task_id = event.payload.active_task_id
            evidence = event.payload.evidence

            parent_suffix = f", active_task_id: {active_task_id}" if active_task_id else ""
            inbox_item = f"Review captured item: {title} (kind: {kind}{parent_suffix})"
            if evidence:
                ev_summary = evidence.strip().replace("\n", " ")
                if len(ev_summary) > 80:
                    ev_summary = ev_summary[:77] + "..."
                inbox_item += f" - Evidence: {ev_summary}"

            try:
                content = full_path.read_text(encoding="utf-8")
                pattern = rf"-\s*\[[ xX/]\]\s*{re.escape(inbox_item)}"
                return bool(re.search(pattern, content))
            except Exception:
                return False

        return False

    def _sync_workboard(self) -> None:
        import subprocess
        import sys
        script_path = self.workspace_root / "tasks" / "scripts" / "sync_workboard.py"
        if script_path.exists():
            try:
                subprocess.run(
                    [sys.executable, str(script_path)],
                    cwd=str(self.workspace_root),
                    capture_output=True,
                    text=True,
                    check=False
                )
            except Exception:
                pass

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

    def _resolve_task_file(self, task_id_or_file: str) -> Path | None:
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
        doc = MarkdownDocument(content)
        doc.edit_task_section(section, item_text)
        p.write_text(doc.serialize(), encoding="utf-8")
        return True

    def create_standalone_task(
        self,
        task_id: int,
        title: str,
        kind: str,
        evidence: str,
        active_task_id: str | None = None,
        active_message_id: str | None = None,
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
        active_message_id: str | None = None,
        resume_condition: str | None = None,
        suggested_resume_action: str | None = None,
    ) -> bool:
        p = self._resolve_task_file(parent_task_file)
        if not p or not p.exists():
            return False
            
        content = p.read_text(encoding="utf-8")
        doc = MarkdownDocument(content)
        
        cond = resume_condition or f"Blocker task at {blocker_task_file} is completed."
        act = suggested_resume_action or "Verify the blocker is resolved and mark parent task status as active."
        
        metadata_lines = [
            "**Status:** blocked",
            f"**Blocked By:** {blocker_task_file}",
            f"**Why Blocked:** {why_blocked}",
            f"**Source Capture ID:** {capture_id}",
        ]
        if active_message_id:
            metadata_lines.append(f"**Active Message ID:** {active_message_id}")
        metadata_lines.extend([
            f"**Resume Condition:** {cond}",
            f"**Suggested Resume Action:** {act}",
        ])
        
        if doc.mark_blocked(metadata_lines):
            p.write_text(doc.serialize(), encoding="utf-8")
            return True
        return False

    def route_to_inbox(
        self,
        title: str,
        kind: str,
        evidence: str,
        active_task_id: str | None = None,
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
            
        inbox_path.read_text(encoding="utf-8")
        
        parent_suffix = f", active_task_id: {active_task_id}" if active_task_id else ""
        item_text = f"Review captured item: {title} (kind: {kind}{parent_suffix})"
        if evidence:
            ev_summary = evidence.strip().replace("\n", " ")
            if len(ev_summary) > 80:
                ev_summary = ev_summary[:77] + "..."
            item_text += f" - Evidence: {ev_summary}"
            
        self.edit_task_section("tasks/open/inbox.md", "Items", item_text)
        return "tasks/open/inbox.md"


def resolve_active_message_id(workspace_root: Path) -> str | None:
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
    active_task_id: str | None = None,
    scope_hint: str = "",
    capture_id: str | None = None,
) -> dict:
    # 1. Validate payload early
    payload = TaskCapturePayload(
        title=title,
        kind=kind,
        evidence=evidence,
        blocks_progress=blocks_progress,
        active_task_id=active_task_id,
        scope_hint=scope_hint,
    )
    payload.validate()

    adapter = LocalMarkdownAdapter(workspace_root)

    # 2. Check for existing event (Idempotency)
    existing = adapter.find_existing_event(
        title=title,
        kind=kind,
        active_task_id=active_task_id,
        capture_id=capture_id,
    )

    if existing:
        # Check if physical changes are present
        if adapter.verify_physical_event(existing):
            # Completely idempotent bypass
            return {
                "tool_name": "capture_task_thread",
                "ok": True,
                "summary": existing.outcome.summary,
                "directive": existing.outcome.directive,
                "capture_id": existing.capture_id,
                "target": existing.outcome.target,
                "path": existing.outcome.file_path,
            }
        else:
            # Physical changes are missing - we recreate/re-run but DO NOT re-log to the ledger
            actual_capture_id = existing.capture_id
            target = existing.outcome.target
            existing_file_path = existing.outcome.file_path
            task_id = None
            if existing_file_path:
                match = re.match(r"^tasks/open/(\d+)-", existing_file_path)
                if match:
                    task_id = int(match.group(1))
    else:
        # Full run - generate/use capture_id
        actual_capture_id = capture_id if capture_id else f"cap_{uuid.uuid4().hex[:12]}"
        target = None
        task_id = None

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    active_message_id = resolve_active_message_id(workspace_root)

    # 3. Determine routing target if not already known
    if target is None:
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

        assert active_task_id is not None
        success = adapter.edit_task_section(active_task_id, section, item_text)
        if success:
            file_path = parent_path or ""
            summary = f"Appended checklist item under section {section} in active task {active_task_id}"
        else:
            target = "inbox"
            file_path = adapter.route_to_inbox(title, kind, evidence, active_task_id)
            summary = f"Editing active task failed, routed task to review inbox: {file_path}"
    elif target == "macro":
        if task_id is None:
            task_id = adapter.get_next_task_id()
        file_path = adapter.create_standalone_task(
            task_id, title, kind, evidence, active_task_id, active_message_id
        )
        summary = f"Created standalone task {task_id}: {file_path}"
    elif target == "blocker":
        if task_id is None:
            task_id = adapter.get_next_task_id()
        blocker_path = adapter.create_standalone_task(
            task_id, title, kind, evidence, active_task_id, active_message_id
        )

        why = title
        if evidence:
            why += f" - {evidence.strip().splitlines()[0]}"

        assert active_task_id is not None
        success = adapter.mark_task_blocked(
            parent_task_file=active_task_id,
            blocker_task_file=blocker_path,
            why_blocked=why,
            capture_id=actual_capture_id,
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

    # 4. Create and validate outcome and event
    outcome = TaskCaptureOutcome(
        target=target,
        file_path=file_path,
        directive=directive,
        summary=summary,
        active_message_id=active_message_id,
    )
    outcome.validate()

    if not existing:
        event = TaskCaptureEvent(
            capture_id=actual_capture_id,
            timestamp=timestamp,
            payload=payload,
            outcome=outcome,
        )
        event.validate()
        adapter.log_event(event)

    if hasattr(adapter, "_sync_workboard"):
        adapter._sync_workboard()

    return {
        "tool_name": "capture_task_thread",
        "ok": True,
        "summary": summary,
        "directive": directive,
        "capture_id": actual_capture_id,
        "target": target,
        "path": file_path,
    }
