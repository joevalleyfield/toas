from pathlib import Path
from unittest.mock import MagicMock

import pytest

from toas.skills import (
    SkillCatalog,
    activate_skill,
    discover_skills,
    handle_skills_commands,
    render_skills_catalog,
)


def test_activate_skill_by_name_and_alias(tmp_path: Path):
    skill_dir = tmp_path / "skills" / "demo-skill"
    skill_dir.mkdir(parents=True)
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()
    script_file = scripts_dir / "run.py"
    script_file.write_text("#!/usr/bin/env python\nprint('hi')", encoding="utf-8")

    (skill_dir / "SKILL.md").write_text(
        """---
name: demo-skill
description: A demo skill for testing.
alias: ds
---
# Demo Instructions
Step 1: run the script.
Step 2: celebrate.
""",
        encoding="utf-8",
    )

    catalog = discover_skills(workspace_root=tmp_path, home_dir=tmp_path / "home")

    # Activate by name
    res1 = activate_skill("demo-skill", catalog=catalog, arguments="target=foo")
    assert res1["ok"] is True
    assert res1["skill"] == "demo-skill"
    assert res1["description"] == "A demo skill for testing."
    assert "target=foo" in res1["content"]
    assert "# Activated Skill: demo-skill" in res1["content"]
    assert "Step 1: run the script." in res1["content"]
    assert str(script_file.resolve()) in res1["content"]
    assert "/ds" in res1["content"]

    # Activate by alias
    res2 = activate_skill("/ds", catalog=catalog)
    assert res2["ok"] is True
    assert res2["skill"] == "demo-skill"

    # Activate unknown
    with pytest.raises(RuntimeError, match="skill not found: non-existent"):
        activate_skill("non-existent", catalog=catalog)


def test_activate_skill_fallback_description_and_no_scripts(tmp_path: Path):
    skill_dir = tmp_path / "skills" / "bare-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("Bare instructions without frontmatter.", encoding="utf-8")

    catalog = discover_skills(workspace_root=tmp_path, home_dir=tmp_path / "home")
    res = activate_skill("bare-skill", catalog=catalog)
    assert res["ok"] is True
    assert "No description provided." in res["content"]
    assert "Bare instructions without frontmatter." in res["content"]
    assert "Companion Scripts:" not in res["content"]


def test_render_skills_catalog_compact_inert_block(tmp_path: Path):
    skill_dir = tmp_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: test-skill
description: Tests things thoroughly.
---
# Instructions
Do not include these instructions in the compact catalog.
""",
        encoding="utf-8",
    )

    catalog = discover_skills(workspace_root=tmp_path, home_dir=tmp_path / "home")
    out = render_skills_catalog(catalog)

    assert "```skills block_id=skills_catalog" in out
    assert "test-skill: Tests things thoroughly." in out
    assert "Do not include these instructions" not in out
    assert out.endswith("```")


def test_render_skills_catalog_empty():
    empty_catalog = SkillCatalog(skills={}, aliases={}, records=[])
    out = render_skills_catalog(empty_catalog)
    assert "No skills available." in out


def test_handle_skills_commands_skills_listing(tmp_path: Path):
    step_mod = MagicMock()
    step_mod.make_result_node = lambda text, **kwargs: {"content": text, **kwargs}
    context = MagicMock()
    context.command_cwd = str(tmp_path)
    context.frontier_role = "user"

    # 1. With bundled skills present
    nodes = handle_skills_commands("skills", [], step_mod=step_mod, context=context)
    assert nodes is not None
    assert len(nodes) == 1
    assert "Available Skills:" in nodes[0]["content"]
    assert "/record-task" in nodes[0]["content"]

    # 2. When empty
    empty_catalog = SkillCatalog(skills={}, aliases={}, records=[])
    import toas.skills.runtime as s_rt
    orig_discover = s_rt.discover_skills
    try:
        s_rt.discover_skills = lambda **kw: empty_catalog
        nodes_empty = handle_skills_commands("skills", [], step_mod=step_mod, context=context)
        assert nodes_empty is not None
        assert "No skills discovered." in nodes_empty[0]["content"]
    finally:
        s_rt.discover_skills = orig_discover


def test_handle_skills_commands_skill_activation(tmp_path: Path):
    step_mod = MagicMock()
    step_mod.make_result_node = lambda text, **kwargs: {"content": text, **kwargs}
    context = MagicMock()
    context.command_cwd = str(tmp_path)
    context.frontier_role = "user"

    # Usage when no args
    res_usage = handle_skills_commands("skill", [], step_mod=step_mod, context=context)
    assert res_usage is not None
    assert "usage: /skill <name> [args]" in res_usage[0]["content"]

    # Valid activation
    res_valid = handle_skills_commands("skill", ["record-task", "refactor", "session"], step_mod=step_mod, context=context)
    assert res_valid is not None
    assert "# Activated Skill: record-task" in res_valid[0]["content"]
    assert "refactor session" in res_valid[0]["content"]

    # Error activation
    res_err = handle_skills_commands("skill", ["unknown-skill"], step_mod=step_mod, context=context)
    assert res_err is not None
    assert "[ERROR] /skill: skill not found: unknown-skill" in res_err[0]["content"]


def test_handle_skills_commands_dynamic_aliases(tmp_path: Path):
    step_mod = MagicMock()
    step_mod.make_result_node = lambda text, **kwargs: {"content": text, **kwargs}
    context = MagicMock()
    context.command_cwd = str(tmp_path)
    context.frontier_role = "user"

    # Canonical name as command: /record-task
    res_canonical = handle_skills_commands("record-task", ["arg1", "arg2"], step_mod=step_mod, context=context)
    assert res_canonical is not None
    assert "# Activated Skill: record-task" in res_canonical[0]["content"]
    assert "arg1 arg2" in res_canonical[0]["content"]

    # Custom alias as command: /rt
    res_alias = handle_skills_commands("rt", ["quick", "task"], step_mod=step_mod, context=context)
    assert res_alias is not None
    assert "# Activated Skill: record-task" in res_alias[0]["content"]
    assert "quick task" in res_alias[0]["content"]

    # Unrelated command returns None
    assert handle_skills_commands("non_skill_cmd", [], step_mod=step_mod, context=context) is None
