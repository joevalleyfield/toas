"""Hierarchical Agent Skills discovery engine for TOAS."""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

_BUILTIN_SLASH_COMMANDS = {
    "step",
    "history",
    "heads",
    "head",
    "transcript",
    "llm-input",
    "prompt",
    "prompts",
    "diff",
    "ancestry",
    "session-path",
    "skills",
    "skill",
}


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    content: str
    path: Path
    skill_dir: Path
    scope: str  # "workspace", "global", or "bundled"
    aliases: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    scripts: tuple[Path, ...] = ()


@dataclass(frozen=True)
class SkillRecord:
    skill: Skill
    is_active: bool
    shadowed_by: str | None = None
    shadows: tuple[str, ...] = ()
    alias_collisions: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillCatalog:
    skills: dict[str, Skill]
    aliases: dict[str, str]
    records: list[SkillRecord]

    def get(self, name_or_alias: str) -> Skill | None:
        cleaned = name_or_alias.strip().lstrip("/")
        if cleaned in self.skills:
            return self.skills[cleaned]
        if cleaned in self.aliases:
            target_name = self.aliases[cleaned]
            return self.skills.get(target_name)
        return None

    def filter(self, query: str | None = None) -> list[Skill]:
        if not query or not query.strip():
            return list(self.skills.values())
        needle = query.strip().lower()
        results: list[Skill] = []
        for skill in self.skills.values():
            if (
                needle in skill.name.lower()
                or needle in skill.description.lower()
                or any(needle in alias.lower() for alias in skill.aliases)
            ):
                results.append(skill)
        return results


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text.strip()
    body = text[match.end():].strip()
    raw_yaml = match.group(1)
    try:
        data = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError:
        return {}, body
    if not isinstance(data, dict):
        return {}, body
    return data, body


def _parse_skill_file(skill_file: Path, skill_dir: Path, scope: str) -> Skill | None:
    try:
        raw_text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    metadata, body = _split_frontmatter(raw_text)

    # Resolve name
    raw_name = metadata.get("name")
    if isinstance(raw_name, str) and raw_name.strip():
        name = raw_name.strip()
    else:
        name = skill_dir.name.strip()

    if not name or ".." in name or "/" in name or "\\" in name:
        return None

    description = ""
    raw_desc = metadata.get("description")
    if isinstance(raw_desc, str):
        description = raw_desc.strip()

    # Collect aliases
    alias_set: list[str] = [name]
    raw_aliases: list[Any] = []
    if "alias" in metadata:
        val = metadata["alias"]
        if isinstance(val, (list, tuple)):
            raw_aliases.extend(val)
        elif val:
            raw_aliases.append(val)
    if "aliases" in metadata:
        val = metadata["aliases"]
        if isinstance(val, (list, tuple)):
            raw_aliases.extend(val)
        elif val:
            raw_aliases.append(val)

    for item in raw_aliases:
        if isinstance(item, str):
            cleaned = item.strip().lstrip("/")
            if cleaned and cleaned not in alias_set:
                alias_set.append(cleaned)

    # Collect scripts in skill_dir / "scripts"
    scripts: list[Path] = []
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.is_dir():
        for script_file in sorted(scripts_dir.iterdir()):
            if script_file.is_file() and not script_file.name.startswith("."):
                scripts.append(script_file)

    return Skill(
        name=name,
        description=description,
        content=body,
        path=skill_file.resolve(),
        skill_dir=skill_dir.resolve(),
        scope=scope,
        aliases=tuple(alias_set),
        metadata=metadata,
        scripts=tuple(scripts),
    )


def _scan_skill_directory(root_dir: Path, scope: str) -> list[Skill]:
    if not root_dir.is_dir():
        return []
    skills: list[Skill] = []
    for item in sorted(root_dir.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
        skill_file = item / "SKILL.md"
        if not skill_file.is_file():
            skill_file = item / "skill.md"
        if skill_file.is_file():
            skill = _parse_skill_file(skill_file, item, scope)
            if skill is not None:
                skills.append(skill)
    return skills


def _bundled_skills_dir() -> Path | None:
    try:
        packaged_root = resources.files("toas").joinpath("assets", "skills")
        with resources.as_file(packaged_root) as root_path:
            if root_path.is_dir():
                return root_path
    except (TypeError, FileNotFoundError, ModuleNotFoundError):
        pass
    return None


def discover_skills(
    *,
    workspace_root: Path | None = None,
    home_dir: Path | None = None,
    extra_dirs: Sequence[Path] | None = None,
) -> SkillCatalog:
    ws = (workspace_root or Path.cwd()).resolve()
    home = (home_dir or Path.home()).resolve()

    # Priority order:
    # 1. Extra explicit dirs (if provided)
    # 2. Workspace dirs:
    #    - .agents/skills
    #    - .gemini/skills
    #    - .toas/skills
    #    - skills
    # 3. Global user dirs:
    #    - ~/.gemini/antigravity/skills
    #    - ~/.config/toas/skills
    # 4. Bundled TOAS skills

    candidates: list[tuple[Path, str]] = []

    if extra_dirs:
        for ed in extra_dirs:
            candidates.append((ed.resolve(), "workspace"))

    candidates.extend([
        (ws / ".agents" / "skills", "workspace"),
        (ws / ".gemini" / "skills", "workspace"),
        (ws / ".toas" / "skills", "workspace"),
        (ws / "skills", "workspace"),
        (home / ".gemini" / "antigravity" / "skills", "global"),
        (home / ".config" / "toas" / "skills", "global"),
    ])

    bundled_dir = _bundled_skills_dir()
    if bundled_dir and bundled_dir.is_dir():
        candidates.append((bundled_dir, "bundled"))

    discovered_skills: list[Skill] = []
    for search_dir, scope in candidates:
        discovered_skills.extend(_scan_skill_directory(search_dir, scope))

    # Precedence & collision resolution
    active_skills: dict[str, Skill] = {}
    skill_shadows: dict[str, list[str]] = {}
    records: list[SkillRecord] = []

    for skill in discovered_skills:
        name = skill.name
        if name not in active_skills:
            active_skills[name] = skill
            skill_shadows[name] = []
            records.append(
                SkillRecord(
                    skill=skill,
                    is_active=True,
                    shadowed_by=None,
                    shadows=(),
                    alias_collisions=(),
                )
            )
        else:
            primary = active_skills[name]
            skill_shadows[name].append(str(skill.path))
            records.append(
                SkillRecord(
                    skill=skill,
                    is_active=False,
                    shadowed_by=str(primary.path),
                    shadows=(),
                    alias_collisions=(),
                )
            )

    # Update active records with shadows
    final_records: list[SkillRecord] = []
    for rec in records:
        if rec.is_active:
            shadows_tuple = tuple(skill_shadows.get(rec.skill.name, []))
            final_records.append(
                SkillRecord(
                    skill=rec.skill,
                    is_active=True,
                    shadowed_by=None,
                    shadows=shadows_tuple,
                    alias_collisions=(),
                )
            )
        else:
            final_records.append(rec)

    # Register aliases
    resolved_aliases: dict[str, str] = {}
    alias_collisions: dict[str, list[str]] = {}

    for name, skill in active_skills.items():
        for alias in skill.aliases:
            if alias in _BUILTIN_SLASH_COMMANDS:
                alias_collisions.setdefault(name, []).append(f"{alias} (collides with built-in)")
                continue
            if alias in resolved_aliases:
                existing_name = resolved_aliases[alias]
                alias_collisions.setdefault(name, []).append(f"{alias} (claimed by {existing_name})")
            else:
                resolved_aliases[alias] = name

    # Update records with alias collision info
    adjusted_records: list[SkillRecord] = []
    for rec in final_records:
        if rec.is_active and rec.skill.name in alias_collisions:
            adjusted_records.append(
                SkillRecord(
                    skill=rec.skill,
                    is_active=rec.is_active,
                    shadowed_by=rec.shadowed_by,
                    shadows=rec.shadows,
                    alias_collisions=tuple(alias_collisions[rec.skill.name]),
                )
            )
        else:
            adjusted_records.append(rec)

    return SkillCatalog(
        skills=active_skills,
        aliases=resolved_aliases,
        records=adjusted_records,
    )
