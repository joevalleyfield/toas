#!/usr/bin/env python3
"""
Syncs tasks/open and tasks/closed into tasks/WORKBOARD.md.
Uses markers <!-- WORKBOARD:NOW:START --> and <!-- WORKBOARD:CLOSED:START -->.
"""
import os
import re
from pathlib import Path
from datetime import datetime, timedelta

# Resolve paths relative to this script's location (tasks/scripts/)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent  # tasks/
TASKS_DIR = PROJECT_ROOT
WORKBOARD_PATH = PROJECT_ROOT / "WORKBOARD.md"

# Threshold for stale tasks (days)
STALE_THRESHOLD_DAYS = 30

def get_open_task_ids():
    """Return set of open task IDs."""
    open_dir = TASKS_DIR / "open"
    if not open_dir.exists():
        return set()
    return {f.stem.split('-')[0] for f in open_dir.iterdir() if f.suffix == '.md'}

def check_stale_tasks(task_ids):
    """Check for stale tasks using git log."""
    import subprocess
    stale_ids = set()
    if not task_ids:
        return stale_ids
    
    try:
        # Get list of files modified in the last STALE_THRESHOLD_DAYS
        # This is a bit aggressive: if ANY file in open/ was modified, we assume the task is active.
        # Instead, we want to find tasks that have NOT been modified.
        # A simpler heuristic: if a task ID is NOT in the list of tasks touched recently, it might be stale.
        # But git log --since doesn't tell us which tasks were touched, just commits.
        # Let's use git log to find the last commit touching each open task file.
        
        # Optimization: Get all open task files
        open_files = [str(TASKS_DIR / "open" / f"{tid}.md") for tid in task_ids]
        
        for f in open_files:
            if not Path(f).exists():
                continue
            try:
                # Get the last commit date for this file
                result = subprocess.run(
                    ["git", "log", "-1", "--format=%ct", f],
                    capture_output=True,
                    text=True,
                    cwd=str(PROJECT_ROOT)
                )
                if result.returncode == 0 and result.stdout.strip():
                    last_modified = int(result.stdout.strip())
                    now = datetime.now().timestamp()
                    days_old = (now - last_modified) / 86400
                    if days_old > STALE_THRESHOLD_DAYS:
                        # Extract ID from filename
                        tid = Path(f).stem.split('-')[0]
                        stale_ids.add(tid)
            except Exception:
                pass
    except Exception:
        pass
    return stale_ids

# Markers in WORKBOARD.md
NOW_START = "<!-- WORKBOARD:NOW:START -->"
NOW_END = "<!-- WORKBOARD:NOW:END -->"
CLOSED_START = "<!-- WORKBOARD:CLOSED:START -->"
CLOSED_END = "<!-- WORKBOARD:CLOSED:END -->"

def parse_task(filepath):
    try:
        content = filepath.read_text()
        lines = content.split('\n')
        title = filepath.stem
        objective = ""
        
        # Priority 1: Objective or Goal
        pattern = r"## (?:Objective|Goal)"
        match = re.search(pattern, content)
        if match:
            section_lines = []
            start_line_idx = lines.index(next(line for line in lines if re.search(pattern, line)))
            for line in lines[start_line_idx + 1:]:
                if re.match(r"## ", line):
                    break
                section_lines.append(line)
            objective = "\n".join(section_lines).strip()
        
        # Priority 2: Problem Statement
        elif "## Problem Statement" in content:
            pattern = r"## Problem Statement"
            match = re.search(pattern, content)
            if match:
                section_lines = []
                start_line_idx = lines.index(next(line for line in lines if re.search(pattern, line)))
                for line in lines[start_line_idx + 1:]:
                    if re.match(r"## ", line):
                        break
                    section_lines.append(line)
                objective = "\n".join(section_lines).strip()

        # Priority 3: Why
        elif "## Why" in content:
            pattern = r"## Why"
            match = re.search(pattern, content)
            if match:
                section_lines = []
                start_line_idx = lines.index(next(line for line in lines if re.search(pattern, line)))
                for line in lines[start_line_idx + 1:]:
                    if re.match(r"## ", line):
                        break
                    section_lines.append(line)
                objective = "\n".join(section_lines).strip()

        # Fallback: First paragraph after title
        if not objective:
            for i, line in enumerate(lines[1:], 1):
                if line.strip():
                    objective = line.strip()[:150]
                    break
        
        # Clean up objective: remove lists/bullets for brevity if it's too long
        if objective:
            # Remove markdown list characters at start of lines
            clean_lines = []
            for line in objective.split('\n'):
                clean_line = re.sub(r'^(\s*[-*]\s|\s*\d+\.\s)', '', line)
                clean_lines.append(clean_line)
            objective = " ".join(clean_lines).strip()[:150]
            if len(" ".join(clean_lines).strip()) > 150:
                objective += "..."

        return {
            "id": title.split('-')[0],
            "title": title,
            "objective": objective,
            "path": filepath
        }
    except Exception as e:
        return None

def get_open_tasks():
    open_dir = TASKS_DIR / "open"
    if not open_dir.exists():
        return []
    tasks = []
    for f in open_dir.iterdir():
        if f.suffix == '.md':
            task = parse_task(f)
            if task:
                tasks.append(task)
    # Sort by ID
    tasks.sort(key=lambda x: int(x['id']) if x['id'].isdigit() else 0)
    return tasks

def get_closed_tasks(n=5):
    closed_dir = TASKS_DIR / "closed"
    if not closed_dir.exists():
        return []
    tasks = []
    for f in closed_dir.iterdir():
        if f.suffix == '.md':
            task = parse_task(f)
            if task:
                tasks.append(task)
    # Sort by ID descending to get most recent (assuming numeric IDs)
    tasks.sort(key=lambda x: int(x['id']) if x['id'].isdigit() else 0, reverse=True)
    return tasks[:n]

INBOX_START = "<!-- WORKBOARD:INBOX:START -->"
INBOX_END = "<!-- WORKBOARD:INBOX:END -->"

def get_inbox_items():
    inbox_path = TASKS_DIR / "open" / "inbox.md"
    if not inbox_path.exists():
        return []
    items = []
    try:
        content = inbox_path.read_text(encoding="utf-8")
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith("- [ ]"):
                item_text = line[5:].strip()
                if item_text:
                    items.append(item_text)
    except Exception:
        pass
    return items

def generate_inbox_section(items):
    lines = []
    for item in items:
        lines.append(f"- **[Inbox]** {item}")
    return "\n".join(lines)

def generate_now_section(tasks, stale_ids):
    lines = []
    for t in tasks:
        stale_flag = " ⚠️ Stale" if t['id'] in stale_ids else ""
        lines.append(f"- **[T{t['id']}]** {t['objective']}{stale_flag}")
    return "\n".join(lines)

def generate_closed_section(tasks):
    lines = []
    for t in tasks:
        # Try to find "Done When" or just use the objective/summary
        content = t['path'].read_text()
        done_when = ""
        if "## Done When" in content:
            # Extract first sentence of Done When
            match = re.search(r"## Done When\n(.*?)(?=\n\n|\Z)", content, re.DOTALL)
            if match:
                done_when = match.group(1).strip().split('\n')[0][:100]
        if not done_when:
            done_when = t['objective']
        lines.append(f"- **[T{t['id']}]** {done_when}")
    return "\n".join(lines)

def sync():
    if not WORKBOARD_PATH.exists():
        print(f"Error: {WORKBOARD_PATH} not found.")
        return

    content = WORKBOARD_PATH.read_text()

    open_tasks = get_open_tasks()
    closed_tasks = get_closed_tasks(5)
    inbox_items = get_inbox_items()

    open_task_ids = get_open_task_ids()
    stale_ids = check_stale_tasks(open_task_ids)

    now_section = generate_now_section(open_tasks, stale_ids)
    closed_section = generate_closed_section(closed_tasks)
    inbox_section = generate_inbox_section(inbox_items)

    # Replace Now Section
    now_start_idx = content.find(NOW_START)
    now_end_idx = content.find(NOW_END)
    if now_start_idx != -1 and now_end_idx != -1:
        content = content[:now_start_idx + len(NOW_START)] + "\n" + now_section + "\n" + content[now_end_idx:]
    else:
        print("Warning: Now markers not found.")

    # Replace Inbox Section
    inbox_start_idx = content.find(INBOX_START)
    inbox_end_idx = content.find(INBOX_END)
    if inbox_start_idx != -1 and inbox_end_idx != -1:
        content = content[:inbox_start_idx + len(INBOX_START)] + "\n" + inbox_section + "\n" + content[inbox_end_idx:]
    else:
        print("Warning: Inbox markers not found.")

    # Replace Closed Section
    closed_start_idx = content.find(CLOSED_START)
    closed_end_idx = content.find(CLOSED_END)
    if closed_start_idx != -1 and closed_end_idx != -1:
        content = content[:closed_start_idx + len(CLOSED_START)] + "\n" + closed_section + "\n" + content[closed_end_idx:]
    else:
        print("Warning: Closed markers not found.")

    WORKBOARD_PATH.write_text(content)
    print(f"Synced {len(open_tasks)} open, {len(inbox_items)} inbox, and {len(closed_tasks)} closed tasks.")
    if stale_ids:
        print(f"Stale tasks (>30 days no change): {', '.join(stale_ids)}")

if __name__ == "__main__":
    sync()