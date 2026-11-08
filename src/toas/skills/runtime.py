"""Runtime activation, progressive disclosure projection, and command handling for Agent Skills."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .discovery import Skill, SkillCatalog, discover_skills


def activate_skill(
    name_or_alias: str = "",
    *,
    name: str | None = None,
    catalog: SkillCatalog | None = None,
    workspace_root: Path | None = None,
    arguments: str = "",
) -> dict[str, Any]:
    target_identifier = name if name is not None else name_or_alias
    active_catalog = catalog or discover_skills(workspace_root=workspace_root)
    skill: Skill | None = active_catalog.get(target_identifier)
    if skill is None:
        raise RuntimeError(f"skill not found: {target_identifier}")

    lines: list[str] = [
        f"# Activated Skill: {skill.name}",
        skill.description if skill.description else "No description provided.",
        "",
        f"Scope: {skill.scope}",
        f"Source: {skill.path}",
    ]

    if skill.aliases:
        alias_strs = [f"/{a}" for a in skill.aliases]
        lines.append(f"Aliases: {', '.join(alias_strs)}")

    if skill.scripts:
        lines.append("Companion Scripts:")
        for script_path in skill.scripts:
            lines.append(f"- {script_path}")

    if arguments and arguments.strip():
        lines.extend(["", "Invocation Arguments:", arguments.strip()])

    lines.extend(["", "## Instructions", "", skill.content])
    rendered_text = "\n".join(lines).strip()

    return {
        "tool_name": "skill",
        "ok": True,
        "summary": f"Activated skill: {skill.name}",
        "skill": skill.name,
        "description": skill.description,
        "scope": skill.scope,
        "source": str(skill.path),
        "scripts": [str(p) for p in skill.scripts],
        "content": rendered_text,
    }


def render_skills_catalog(
    catalog: SkillCatalog | None = None,
    *,
    workspace_root: Path | None = None,
) -> str:
    active_catalog = catalog or discover_skills(workspace_root=workspace_root)
    skills = list(active_catalog.skills.values())
    if not skills:
        return "```skills block_id=skills_catalog\nNo skills available.\n```"

    lines = ["```skills block_id=skills_catalog", "Available Skills:"]
    for skill in sorted(skills, key=lambda s: s.name):
        desc = skill.description if skill.description else "No description."
        lines.append(f"- {skill.name}: {desc}")
    lines.extend([
        "Activate a skill on-demand using `/skill <name>` or `operation: skill` with argument `name`.",
        "```",
    ])
    return "\n".join(lines)


def handle_skills_commands(
    command: str,
    args: list[str],
    *,
    step_mod,
    context,
) -> list[dict] | None:
    ws_root = Path(context.command_cwd).resolve() if context.command_cwd else Path.cwd().resolve()
    catalog = discover_skills(workspace_root=ws_root)

    if command == "skills":
        skills = list(catalog.skills.values())
        if not skills:
            return [
                step_mod.make_result_node(
                    "No skills discovered.",
                    origin_role=context.frontier_role,
                    origin_kind="slash_command",
                )
            ]
        lines = ["Available Skills:"]
        for skill in sorted(skills, key=lambda s: s.name):
            other_aliases = [a for a in skill.aliases if a != skill.name]
            alias_suffix = f" (aliases: {', '.join('/' + a for a in other_aliases)})" if other_aliases else ""
            desc = f": {skill.description}" if skill.description else ""
            lines.append(f"- /{skill.name}{alias_suffix}{desc}")
        lines.extend([
            "",
            "Use `/skill <name> [args]` or `/<skill-name> [args]` to activate a skill.",
        ])
        return [
            step_mod.make_result_node(
                "\n".join(lines),
                origin_role=context.frontier_role,
                origin_kind="slash_command",
            )
        ]

    if command == "skill":
        if not args:
            return [
                step_mod.make_result_node(
                    "usage: /skill <name> [args]",
                    origin_role=context.frontier_role,
                    origin_kind="slash_command",
                )
            ]
        skill_name = args[0]
        arguments_str = " ".join(args[1:]).strip()
        try:
            outcome = activate_skill(
                skill_name,
                catalog=catalog,
                workspace_root=ws_root,
                arguments=arguments_str,
            )
            return [
                step_mod.make_result_node(
                    outcome["content"],
                    origin_role=context.frontier_role,
                    origin_kind="slash_command",
                    payload=outcome,
                )
            ]
        except RuntimeError as exc:
            return [
                step_mod.make_result_node(
                    f"[ERROR] /skill: {exc}",
                    origin_role=context.frontier_role,
                    origin_kind="slash_command",
                )
            ]

    # Check if command is a registered skill name or alias
    target_skill = catalog.get(command)
    if target_skill is not None:
        arguments_str = " ".join(args).strip()
        outcome = activate_skill(
            target_skill.name,
            catalog=catalog,
            workspace_root=ws_root,
            arguments=arguments_str,
        )
        return [
            step_mod.make_result_node(
                outcome["content"],
                origin_role=context.frontier_role,
                origin_kind="slash_command",
                payload=outcome,
            )
        ]

    return None
