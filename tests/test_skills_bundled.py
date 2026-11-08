import importlib.util
from pathlib import Path

from toas.skills import discover_skills
from toas.tools import execute_call, validate_call


def _load_record_task_module():
    script_path = Path(__file__).resolve().parent.parent / "src" / "toas" / "assets" / "skills" / "record-task" / "scripts" / "record_task.py"
    spec = importlib.util.spec_from_file_location("record_task", script_path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


record_task_mod = _load_record_task_module()
detect_naming_scheme = record_task_mod.detect_naming_scheme
find_next_numeric_id = record_task_mod.find_next_numeric_id
record_task = record_task_mod.record_task
record_task_main = record_task_mod.main
slugify = record_task_mod.slugify


def test_bundled_skills_catalog_presence():
    catalog = discover_skills()
    assert "record-task" in catalog.skills
    assert "jj-scratch-workspace" in catalog.skills
    assert "code-review" in catalog.skills

    rt = catalog.skills["record-task"]
    assert rt.scope == "bundled"
    assert "rt" in rt.aliases
    assert len(rt.scripts) >= 1
    assert any("record_task.py" in str(s) for s in rt.scripts)

    jj_skill = catalog.skills["jj-scratch-workspace"]
    assert jj_skill.scope == "bundled"
    assert "scratch" in jj_skill.aliases

    cr = catalog.skills["code-review"]
    assert cr.scope == "bundled"
    assert "review" in cr.aliases


def test_record_task_slugify():
    assert slugify("Add new feature!") == "add-new-feature"
    assert slugify("   --Complex $ Name --  ") == "complex-name"
    assert slugify("") == "task"


def test_record_task_naming_scheme_detection(tmp_path: Path):
    # Default is date
    assert detect_naming_scheme(tmp_path) == "date"

    # tasks/README.md with YYMMDD
    readme_dir = tmp_path / "tasks"
    readme_dir.mkdir()
    (readme_dir / "README.md").write_text("# Tasks\nUse YYMMDD-intent.md\n", encoding="utf-8")
    assert detect_naming_scheme(tmp_path) == "date"

    # Directory with numeric files
    num_ws = tmp_path / "num_ws"
    num_open = num_ws / "tasks" / "open"
    num_open.mkdir(parents=True)
    (num_open / "101-legacy-task.md").write_text("# 101", encoding="utf-8")
    assert detect_naming_scheme(num_ws) == "numeric"

    # Directory with date files
    date_ws = tmp_path / "date_ws"
    date_open = date_ws / "tasks" / "open"
    date_open.mkdir(parents=True)
    (date_open / "261101-date-task.md").write_text("# Date task", encoding="utf-8")
    assert detect_naming_scheme(date_ws) == "date"


def test_find_next_numeric_id(tmp_path: Path):
    open_dir = tmp_path / "tasks" / "open"
    assert find_next_numeric_id(tmp_path) == 1

    open_dir.mkdir(parents=True)
    (open_dir / "5-task.md").write_text("", encoding="utf-8")
    (open_dir / "12-task.md").write_text("", encoding="utf-8")
    (open_dir / "invalid.md").write_text("", encoding="utf-8")
    assert find_next_numeric_id(tmp_path) == 13


def test_record_task_execution_date_scheme(tmp_path: Path):
    readme_dir = tmp_path / "tasks"
    readme_dir.mkdir()
    (readme_dir / "README.md").write_text("Use YYMMDD-scheme\n", encoding="utf-8")

    # Dry run
    target = record_task(
        title="Test Task Title",
        intent="Test intent description",
        kind="tooling",
        workspace=tmp_path,
        dry_run=True,
    )
    assert not target.exists()
    assert target.name.endswith("-test-task-title.md")

    # Real run
    written = record_task(
        title="Test Task Title",
        intent="Test intent description",
        kind="tooling",
        evidence="Observed during test run",
        workspace=tmp_path,
        dry_run=False,
    )
    assert written.exists()
    content = written.read_text(encoding="utf-8")
    assert "Filed as: " in content
    assert "keywords: tooling, open" in content
    assert "# Test Task Title" in content
    assert "## Intent\n\nTest intent description" in content
    assert "## Context & Motivation\n\nObserved during test run" in content
    assert "## Acceptance Criteria" in content


def test_record_task_execution_numeric_scheme(tmp_path: Path):
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True)
    (open_dir / "42-prior-task.md").write_text("", encoding="utf-8")

    written = record_task(
        title="Numeric Follow-up",
        intent="Continue work",
        workspace=tmp_path,
    )
    assert written.exists()
    assert written.name == "43-numeric-follow-up.md"
    content = written.read_text(encoding="utf-8")
    assert "# 43 Numeric Follow-up" in content
    assert "## Goal\n\nNumeric Follow-up" in content


def test_record_task_runs_sync_script_if_present(tmp_path: Path):
    scripts_dir = tmp_path / "tasks" / "scripts"
    scripts_dir.mkdir(parents=True)
    marker = tmp_path / "sync_ran.txt"
    sync_script = scripts_dir / "sync_workboard.py"
    sync_script.write_text(f"from pathlib import Path\nPath('{marker}').write_text('synced', encoding='utf-8')\n", encoding="utf-8")

    record_task(title="Sync Test", workspace=tmp_path)
    assert marker.exists()
    assert marker.read_text(encoding="utf-8") == "synced"


def test_record_task_main_cli(tmp_path: Path, monkeypatch, capsys):
    ret = record_task_main(["--title", "CLI Task", "--workspace", str(tmp_path), "--dry-run"])
    assert ret == 0
    captured = capsys.readouterr().out
    assert "[dry-run] Recorded task: tasks/open/" in captured


def test_capture_task_thread_legacy_facade(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    call = {
        "tool_name": "capture_task_thread",
        "args": {
            "title": "Legacy thread capture",
            "kind": "cleanup",
            "evidence": "Observed test evidence",
        },
    }
    tool, args = validate_call(call)
    assert tool.name == "capture_task_thread"

    res = execute_call(call)
    assert res["ok"] is True
    assert res["tool_name"] == "capture_task_thread"
    assert "Created standalone task" in res["summary"]
