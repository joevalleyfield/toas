"""Agent Skills integration package for TOAS."""
from __future__ import annotations

from .discovery import Skill, SkillCatalog, SkillRecord, discover_skills
from .runtime import activate_skill, handle_skills_commands, render_skills_catalog
from .specialization import SpecializationError, SpecializationResult, specialize_skill

__all__ = [
    "Skill",
    "SkillCatalog",
    "SkillRecord",
    "SpecializationError",
    "SpecializationResult",
    "activate_skill",
    "discover_skills",
    "handle_skills_commands",
    "render_skills_catalog",
    "specialize_skill",
]
