from pathlib import Path

from toas.skills.discovery import (
    _bundled_skills_dir,
    _parse_skill_file,
    _scan_skill_directory,
    _split_frontmatter,
    discover_skills,
)


def test_split_frontmatter_valid():
    text = """---
name: my-skill
description: Does things.
alias: [ms, mine]
---
# Instructions
Do the thing.
"""
    meta, body = _split_frontmatter(text)
    assert meta["name"] == "my-skill"
    assert meta["description"] == "Does things."
    assert meta["alias"] == ["ms", "mine"]
    assert body == "# Instructions\nDo the thing."


def test_split_frontmatter_no_frontmatter():
    text = "# Just markdown"
    meta, body = _split_frontmatter(text)
    assert meta == {}
    assert body == "# Just markdown"


def test_split_frontmatter_invalid_yaml():
    text = """---
: invalid: yaml:
---
Body
"""
    meta, body = _split_frontmatter(text)
    assert meta == {}
    assert body == "Body"


def test_split_frontmatter_non_dict_yaml():
    text = """---
- a
- b
---
Body
"""
    meta, body = _split_frontmatter(text)
    assert meta == {}
    assert body == "Body"


def test_parse_skill_file_fallback_to_dir_name(tmp_path: Path):
    skill_dir = tmp_path / "fallback-name"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("No frontmatter body here.", encoding="utf-8")

    skill = _parse_skill_file(skill_file, skill_dir, scope="workspace")
    assert skill is not None
    assert skill.name == "fallback-name"
    assert skill.description == ""
    assert skill.content == "No frontmatter body here."
    assert skill.scope == "workspace"
    assert skill.aliases == ("fallback-name",)
    assert skill.scripts == ()


def test_parse_skill_file_invalid_names(tmp_path: Path):
    skill_dir = tmp_path / "valid-dir"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"

    # Name containing ..
    skill_file.write_text("---\nname: ../escape\n---\nBody", encoding="utf-8")
    assert _parse_skill_file(skill_file, skill_dir, scope="workspace") is None

    # Name containing /
    skill_file.write_text("---\nname: sub/dir\n---\nBody", encoding="utf-8")
    assert _parse_skill_file(skill_file, skill_dir, scope="workspace") is None

    # Name containing \
    skill_file.write_text("---\nname: sub\\dir\n---\nBody", encoding="utf-8")
    assert _parse_skill_file(skill_file, skill_dir, scope="workspace") is None


def test_parse_skill_file_unreadable(tmp_path: Path):
    non_existent = tmp_path / "ghost" / "SKILL.md"
    assert _parse_skill_file(non_existent, tmp_path / "ghost", scope="workspace") is None


def test_parse_skill_file_with_aliases_and_scripts(tmp_path: Path):
    skill_dir = tmp_path / "fancy-skill"
    skill_dir.mkdir()
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "tool_a.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (scripts_dir / "tool_b.py").write_text("#!/usr/bin/env python\n", encoding="utf-8")
    (scripts_dir / ".hidden").write_text("skip me", encoding="utf-8")

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        """---
name: fancy-skill
description: A very fancy skill.
alias: /fs
aliases:
  - fancy
  - /fs-alt
---
Instructions here.
""",
        encoding="utf-8",
    )

    skill = _parse_skill_file(skill_file, skill_dir, scope="global")
    assert skill is not None
    assert skill.name == "fancy-skill"
    assert skill.description == "A very fancy skill."
    assert skill.scope == "global"
    assert "fancy-skill" in skill.aliases
    assert "fs" in skill.aliases
    assert "fancy" in skill.aliases
    assert "fs-alt" in skill.aliases
    assert len(skill.scripts) == 2
    assert any(s.name == "tool_a.sh" for s in skill.scripts)
    assert any(s.name == "tool_b.py" for s in skill.scripts)


def test_scan_skill_directory_non_dir(tmp_path: Path):
    assert _scan_skill_directory(tmp_path / "not-there", scope="workspace") == []


def test_scan_skill_directory_case_variants_and_skips(tmp_path: Path):
    root = tmp_path / "skills"
    root.mkdir()

    # Hidden dir skipped
    hidden = root / ".hidden_skill"
    hidden.mkdir()
    (hidden / "SKILL.md").write_text("hidden", encoding="utf-8")

    # Regular file skipped
    (root / "regular_file.txt").write_text("skip", encoding="utf-8")

    # Lowercase skill.md supported
    lower_dir = root / "lower-skill"
    lower_dir.mkdir()
    (lower_dir / "skill.md").write_text("---\nname: lower-skill\n---\nLower", encoding="utf-8")

    # Directory with no SKILL.md
    empty_dir = root / "empty-skill"
    empty_dir.mkdir()

    skills = _scan_skill_directory(root, scope="workspace")
    assert len(skills) == 1
    assert skills[0].name == "lower-skill"


def test_discover_skills_hierarchical_precedence(tmp_path: Path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    home = tmp_path / "home"
    home.mkdir()

    # Create skills in different precedence levels:
    # 1. ws/.agents/skills/alpha (highest workspace)
    agents_alpha = ws / ".agents" / "skills" / "alpha"
    agents_alpha.mkdir(parents=True)
    (agents_alpha / "SKILL.md").write_text("---\nname: alpha\ndescription: Agents Alpha\n---\nBody", encoding="utf-8")

    # 2. ws/.toas/skills/alpha (shadowed by .agents)
    toas_alpha = ws / ".toas" / "skills" / "alpha"
    toas_alpha.mkdir(parents=True)
    (toas_alpha / "SKILL.md").write_text("---\nname: alpha\ndescription: Toas Alpha\n---\nBody", encoding="utf-8")

    # 3. ws/skills/beta (workspace beta)
    ws_beta = ws / "skills" / "beta"
    ws_beta.mkdir(parents=True)
    (ws_beta / "SKILL.md").write_text("---\nname: beta\ndescription: Workspace Beta\n---\nBody", encoding="utf-8")

    # 4. home/.config/toas/skills/beta (shadowed by workspace beta)
    home_beta = home / ".config" / "toas" / "skills" / "beta"
    home_beta.mkdir(parents=True)
    (home_beta / "SKILL.md").write_text("---\nname: beta\ndescription: Home Beta\n---\nBody", encoding="utf-8")

    # 5. home/.gemini/antigravity/skills/gamma (global gamma)
    home_gamma = home / ".gemini" / "antigravity" / "skills" / "gamma"
    home_gamma.mkdir(parents=True)
    (home_gamma / "SKILL.md").write_text("---\nname: gamma\ndescription: Home Gamma\n---\nBody", encoding="utf-8")

    catalog = discover_skills(workspace_root=ws, home_dir=home)

    # Check active skills
    assert "alpha" in catalog.skills
    assert catalog.skills["alpha"].description == "Agents Alpha"
    assert catalog.skills["alpha"].scope == "workspace"

    assert "beta" in catalog.skills
    assert catalog.skills["beta"].description == "Workspace Beta"
    assert catalog.skills["beta"].scope == "workspace"

    assert "gamma" in catalog.skills
    assert catalog.skills["gamma"].description == "Home Gamma"
    assert catalog.skills["gamma"].scope == "global"

    # Bundled skills should also be discovered
    assert "record-task" in catalog.skills
    assert "jj-scratch-workspace" in catalog.skills
    assert "code-review" in catalog.skills

    # Check shadowing records
    alpha_active_rec = next(r for r in catalog.records if r.skill.name == "alpha" and r.is_active)
    assert len(alpha_active_rec.shadows) == 1
    assert str(toas_alpha / "SKILL.md") in alpha_active_rec.shadows[0]

    alpha_shadowed_rec = next(r for r in catalog.records if r.skill.name == "alpha" and not r.is_active)
    assert alpha_shadowed_rec.shadowed_by == str((agents_alpha / "SKILL.md").resolve())

    beta_active_rec = next(r for r in catalog.records if r.skill.name == "beta" and r.is_active)
    assert len(beta_active_rec.shadows) == 1


def test_discover_skills_alias_collisions(tmp_path: Path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    skills_dir = ws / "skills"
    skills_dir.mkdir()

    # Skill 1 defines alias "step" (built-in command) and alias "shared_alias"
    s1 = skills_dir / "s1"
    s1.mkdir()
    (s1 / "SKILL.md").write_text(
        "---\nname: s1\ndescription: S1\nalias: [step, shared_alias]\n---\nContent",
        encoding="utf-8",
    )

    # Skill 2 defines alias "shared_alias" (claimed by S1)
    s2 = skills_dir / "s2"
    s2.mkdir()
    (s2 / "SKILL.md").write_text(
        "---\nname: s2\ndescription: S2\nalias: shared_alias\n---\nContent",
        encoding="utf-8",
    )

    catalog = discover_skills(workspace_root=ws, home_dir=tmp_path / "empty_home")
    assert catalog.aliases["shared_alias"] == "s1"
    assert "step" not in catalog.aliases

    rec_s1 = next(r for r in catalog.records if r.skill.name == "s1")
    assert any("step (collides with built-in)" in col for col in rec_s1.alias_collisions)

    rec_s2 = next(r for r in catalog.records if r.skill.name == "s2")
    assert any("shared_alias (claimed by s1)" in col for col in rec_s2.alias_collisions)


def test_skill_catalog_get_and_filter(tmp_path: Path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    skills_dir = ws / "skills"
    skills_dir.mkdir()

    s = skills_dir / "my-task"
    s.mkdir()
    (s / "SKILL.md").write_text(
        "---\nname: my-task\ndescription: Manage tasks effortlessly.\nalias: mt\n---\nContent",
        encoding="utf-8",
    )

    catalog = discover_skills(workspace_root=ws, home_dir=tmp_path / "empty_home")

    # Get by exact name
    assert catalog.get("my-task") is not None
    assert catalog.get("my-task").name == "my-task"

    # Get by slash name
    assert catalog.get("/my-task") is not None

    # Get by alias
    assert catalog.get("mt") is not None
    assert catalog.get("/mt") is not None

    # Get unknown
    assert catalog.get("non-existent") is None

    # Filter
    matched = catalog.filter("effortlessly")
    assert len(matched) == 1
    assert matched[0].name == "my-task"

    # Filter with alias match
    matched_alias = catalog.filter("mt")
    assert len(matched_alias) >= 1
    assert any(m.name == "my-task" for m in matched_alias)

    # Empty filter returns all active
    all_active = catalog.filter(None)
    assert len(all_active) >= 1
    assert any(m.name == "my-task" for m in all_active)


def test_discover_skills_extra_dirs(tmp_path: Path):
    extra = tmp_path / "custom_dir"
    extra.mkdir()
    s = extra / "custom-skill"
    s.mkdir()
    (s / "SKILL.md").write_text("---\nname: custom-skill\ndescription: Custom\n---\nCustom body", encoding="utf-8")

    catalog = discover_skills(
        workspace_root=tmp_path / "ws",
        home_dir=tmp_path / "home",
        extra_dirs=[extra],
    )
    assert "custom-skill" in catalog.skills
    assert catalog.skills["custom-skill"].description == "Custom"


def test_parse_skill_file_aliases_as_string(tmp_path: Path):
    skill_dir = tmp_path / "str-aliases"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\nname: str-skill\naliases: single-alias\n---\nBody",
        encoding="utf-8",
    )
    skill = _parse_skill_file(skill_file, skill_dir, scope="workspace")
    assert skill is not None
    assert "single-alias" in skill.aliases


def test_bundled_skills_dir_exception(monkeypatch):
    import importlib.resources as res

    monkeypatch.setattr(res, "files", lambda mod: (_ for _ in ()).throw(FileNotFoundError("not found")))
    assert _bundled_skills_dir() is None
