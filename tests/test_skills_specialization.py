"""Tests for skill specialization and prompt-to-script distillation."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from toas.cli_dispatch import DispatchDeps, dispatch_main
from toas.cli_surface_commands import run_skill_specialize as run_surface_skill_specialize
from toas.operator_api import skill_specialize
from toas.skills.discovery import discover_skills
from toas.skills.runtime import handle_skills_commands
from toas.skills.specialization import (
    SpecializationError,
    inspect_tasks_conventions,
    specialize_skill,
    verify_companion_script,
)


def test_inspect_tasks_conventions_date_scheme(tmp_path: Path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "README.md").write_text("# Tasks\nUse YYMMDD-intent.md\n", encoding="utf-8")

    info = inspect_tasks_conventions(tmp_path)
    assert info["scheme"] == "date"
    assert info["has_open_dir"] is False
    assert info["has_sync_script"] is False


def test_inspect_tasks_conventions_numeric_scheme(tmp_path: Path):
    open_dir = tmp_path / "tasks" / "open"
    open_dir.mkdir(parents=True)
    (open_dir / "1-first-task.md").write_text("# 1", encoding="utf-8")

    info = inspect_tasks_conventions(tmp_path)
    assert info["scheme"] == "numeric"
    assert info["has_open_dir"] is True
    assert info["has_sync_script"] is False


def test_inspect_tasks_conventions_with_sync_script(tmp_path: Path):
    scripts_dir = tmp_path / "tasks" / "scripts"
    scripts_dir.mkdir(parents=True)
    (scripts_dir / "sync_workboard.py").write_text("# sync", encoding="utf-8")

    info = inspect_tasks_conventions(tmp_path)
    assert info["has_sync_script"] is True
    assert info["sync_script_path"] is not None


def test_verify_companion_script_valid(tmp_path: Path):
    valid_script = tmp_path / "valid.py"
    valid_script.write_text(
        "import sys\nif '--dry-run' in sys.argv:\n    print('[dry-run]')\n    sys.exit(0)\n",
        encoding="utf-8",
    )
    verify_companion_script(valid_script, workspace_root=tmp_path)


def test_verify_companion_script_syntax_error(tmp_path: Path):
    broken_script = tmp_path / "broken.py"
    broken_script.write_text("def syntax_error(\n", encoding="utf-8")
    with pytest.raises(SpecializationError, match="Syntax verification failed"):
        verify_companion_script(broken_script, workspace_root=tmp_path)


def test_verify_companion_script_dry_run_failure(tmp_path: Path):
    failing_script = tmp_path / "failing.py"
    failing_script.write_text("import sys\nsys.exit(2)\n", encoding="utf-8")
    with pytest.raises(SpecializationError, match="Dry-run verification failed"):
        verify_companion_script(failing_script, workspace_root=tmp_path)


def test_specialize_skill_unknown_skill(tmp_path: Path):
    with pytest.raises(SpecializationError, match="not found in available skills catalog"):
        specialize_skill("nonexistent-skill-xyz", workspace_root=tmp_path)


def test_specialize_skill_without_script_template(tmp_path: Path):
    # Create a prose-only workspace skill
    skill_dir = tmp_path / ".agents" / "skills" / "prose-only"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: prose-only\ndescription: Prose only\n---\nRunbook", encoding="utf-8")

    with pytest.raises(SpecializationError, match="does not provide a distillable companion script template"):
        specialize_skill("prose-only", workspace_root=tmp_path)


def test_specialize_record_task_end_to_end(tmp_path: Path):
    # Setup repo structure with tasks/open and README.md
    tasks_open = tmp_path / "tasks" / "open"
    tasks_open.mkdir(parents=True)
    (tmp_path / "tasks" / "README.md").write_text("Use YYMMDD prefix", encoding="utf-8")

    # Add mock sync script
    sync_script = tmp_path / "tasks" / "scripts" / "sync_workboard.py"
    sync_script.parent.mkdir(parents=True)
    marker = tmp_path / "synced.txt"
    sync_script.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('yes')\n", encoding="utf-8")

    # Run specialization
    res = specialize_skill("record-task", workspace_root=tmp_path)
    assert res.verified is True
    assert res.skill_name == "record-task"
    assert res.script_path.is_file()
    assert res.skill_md_path.is_file()
    assert res.target_dir == tmp_path / ".agents" / "skills" / "record-task"

    # Verify specialized skill shadows bundled skill
    catalog = discover_skills(workspace_root=tmp_path)
    active_skill = catalog.skills["record-task"]
    assert active_skill.scope == "workspace"
    assert str(active_skill.path) == str(res.skill_md_path.resolve())
    assert any("mint_task.py" in str(s) for s in active_skill.scripts)

    # Test executing the generated script: dry-run
    cmd_dry = [
        sys.executable,
        str(res.script_path),
        "--title", "Specialized Feature",
        "--intent", "Deliver specialized capability",
        "--kind", "feature",
        "--dry-run",
    ]
    proc_dry = subprocess.run(cmd_dry, cwd=str(tmp_path), capture_output=True, text=True)
    assert proc_dry.returncode == 0
    assert "[dry-run] Would create:" in proc_dry.stdout
    assert not marker.exists()

    # Test executing the generated script: real creation
    cmd_real = [
        sys.executable,
        str(res.script_path),
        "--title", "Specialized Feature",
        "--intent", "Deliver specialized capability",
        "--kind", "feature",
        "--parent", "261106-parent",
        "--keywords", "skills", "distillation",
    ]
    proc_real = subprocess.run(cmd_real, cwd=str(tmp_path), capture_output=True, text=True)
    assert proc_real.returncode == 0
    assert "Created task:" in proc_real.stdout

    # Verify task file created on disk
    task_files = list(tasks_open.glob("*-specialized-feature.md"))
    assert len(task_files) == 1
    content = task_files[0].read_text(encoding="utf-8")
    assert "Filed as: " in content
    assert "Parent: `261106-parent`" in content
    assert "keywords: active, feature, skills, distillation" in content
    assert "## Intent\n\nDeliver specialized capability" in content
    assert "## Acceptance Criteria" in content

    # Verify sync script was executed
    assert marker.exists()
    assert marker.read_text(encoding="utf-8") == "yes"


def test_operator_api_skill_specialize(tmp_path: Path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "README.md").write_text("Numeric", encoding="utf-8")

    outcome = skill_specialize(name="record-task", workspace_root=tmp_path)
    assert outcome.verified is True
    assert outcome.skill_name == "record-task"
    assert "Specialized skill: record-task" in outcome.text
    assert "Verification status: PASSED" in outcome.text
    assert Path(outcome.script_path).is_file()


def test_cli_surface_skill_specialize():
    mock_specialize = MagicMock()
    mock_specialize.return_value = MagicMock(text="Specialization output message")
    printed: list[str] = []

    run_surface_skill_specialize(
        operator_skill_specialize=mock_specialize,
        name="record-task",
        print_fn=printed.append,
    )
    mock_specialize.assert_called_once_with(name="record-task")
    assert printed == ["Specialization output message"]


def test_cli_dispatch_skill_specialize(monkeypatch):
    mock_specialize = MagicMock()
    deps = DispatchDeps(
        run_help=MagicMock(),
        run_step=MagicMock(),
        run_step_async=MagicMock(),
        run_watch=MagicMock(),
        run_cancel=MagicMock(),
        run_backend=MagicMock(),
        run_heads=MagicMock(),
        run_intents=MagicMock(),
        run_graph=MagicMock(),
        run_transcript=MagicMock(),
        run_llm_input=MagicMock(),
        run_prompt=MagicMock(),
        run_prompts=MagicMock(),
        run_history=MagicMock(),
        run_session_path=MagicMock(),
        run_surface=MagicMock(),
        run_ancestry=MagicMock(),
        run_diff=MagicMock(),
        run_index_rebuild=MagicMock(),
        run_daemon=MagicMock(),
        run_host=MagicMock(),
        run_replay_script=MagicMock(),
        run_debug_cancel_latency=MagicMock(),
        run_skill_specialize=mock_specialize,
    )

    dispatch_main(["skill", "specialize", "record-task"], deps=deps)
    mock_specialize.assert_called_once_with("record-task")

    # Missing arg
    with pytest.raises(SystemExit, match="usage: toas skill specialize <name>"):
        dispatch_main(["skill", "specialize"], deps=deps)


def test_slash_command_skill_specialize(tmp_path: Path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "README.md").write_text("Date", encoding="utf-8")

    step_mod = MagicMock()
    step_mod.make_result_node = lambda text, **kwargs: {"text": text, **kwargs}
    context = MagicMock()
    context.command_cwd = str(tmp_path)
    context.frontier_role = "user"

    # 1. /skill specialize record-task
    res = handle_skills_commands("skill", ["specialize", "record-task"], step_mod=step_mod, context=context)
    assert res is not None
    assert "Specialized skill 'record-task'" in res[0]["text"]
    assert "Verification: PASSED" in res[0]["text"]

    # 2. /skill specialize (missing argument)
    res_err = handle_skills_commands("skill", ["specialize"], step_mod=step_mod, context=context)
    assert res_err is not None
    assert "usage: /skill specialize <name>" in res_err[0]["text"]

    # 2b. /skill specialize (unknown skill error)
    res_err_unknown = handle_skills_commands("skill", ["specialize", "unknown-xyz"], step_mod=step_mod, context=context)
    assert res_err_unknown is not None
    assert "[ERROR] /skill specialize:" in res_err_unknown[0]["text"]

    # 3. /specialize record-task
    res_alias = handle_skills_commands("specialize", ["record-task"], step_mod=step_mod, context=context)
    assert res_alias is not None
    assert "Specialized skill 'record-task'" in res_alias[0]["text"]

    # 4. /specialize (missing argument)
    res_alias_err = handle_skills_commands("specialize", [], step_mod=step_mod, context=context)
    assert res_alias_err is not None
    assert "usage: /specialize <name>" in res_alias_err[0]["text"]

    # 5. /specialize unknown-skill (error handling)
    res_unknown = handle_skills_commands("specialize", ["unknown-xyz"], step_mod=step_mod, context=context)
    assert res_unknown is not None
    assert "[ERROR] /specialize:" in res_unknown[0]["text"]


def test_inspect_tasks_conventions_readme_os_error(tmp_path: Path, monkeypatch):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    readme = tasks_dir / "README.md"
    readme.write_text("unreadable", encoding="utf-8")
    monkeypatch.setattr(Path, "read_text", MagicMock(side_effect=OSError("disk read error")))

    info = inspect_tasks_conventions(tmp_path)
    assert info["scheme"] == "date"


def test_specialize_skill_generic_fallback_with_script(tmp_path: Path):
    skill_dir = tmp_path / ".agents" / "skills" / "custom-runner"
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: custom-runner\ndescription: Custom\n---\nRunbook", encoding="utf-8")
    script_file = scripts_dir / "runner.py"
    script_file.write_text("import sys\nif '--dry-run' in sys.argv:\n    sys.exit(0)\n", encoding="utf-8")

    out_base = tmp_path / "out_skills"
    res = specialize_skill("custom-runner", workspace_root=tmp_path, output_base=out_base)
    assert res.verified is True
    assert res.skill_name == "custom-runner"
    assert (out_base / "custom-runner" / "scripts" / "runner.py").is_file()


def test_specialize_skill_generic_fallback_script_os_error(tmp_path: Path, monkeypatch):
    skill_dir = tmp_path / ".agents" / "skills" / "custom-runner"
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: custom-runner\ndescription: Custom\n---\nRunbook", encoding="utf-8")
    script_file = scripts_dir / "runner.py"
    script_file.write_text("test", encoding="utf-8")

    orig_read_text = Path.read_text

    def mock_read_text(self, *args, **kwargs):
        if self.name == "runner.py":
            raise OSError("permission denied")
        return orig_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", mock_read_text)
    with pytest.raises(SpecializationError, match="Cannot read companion script"):
        specialize_skill("custom-runner", workspace_root=tmp_path)

