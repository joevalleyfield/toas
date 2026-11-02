"""Generates starter executable grant policies from harvested command profiles."""

from __future__ import annotations

from pathlib import Path

from .command_harvester import HarvestReport

# Known single-purpose inspection tools that safely default to allow_all
READ_ONLY_INSPECTION_TOOLS = {
    "cat",
    "echo",
    "find",
    "head",
    "ls",
    "pwd",
    "rg",
    "tail",
    "wc",
}


def scaffold_policy_from_report(
    report: HarvestReport,
    *,
    default: bool = False,
) -> str:
    """Generate Python source for .toas/policy.py based on a HarvestReport."""
    lines: list[str] = [
        '"""Workspace executable grant policy.',
        "",
        f"Scaffolded from {report.total_invocations} observed invocations across {report.total_events_scanned} event log records.",
        '"""',
        "from __future__ import annotations",
        "",
        "from toas.runtime.executable_grants import ExecutableGrantPolicy",
        "from toas.runtime.matchers import (",
        "    allow_all,",
        "    allow_subcommands,",
        "    deny_flags,",
        ")",
        "",
        f"default = {default}",
        "",
        "prefix_matchers = {",
    ]

    sorted_profiles = sorted(
        report.profiles.values(),
        key=lambda p: p.total_calls,
        reverse=True,
    )

    for p in sorted_profiles:
        lines.append(
            f"    # Observed {p.total_calls} calls (assistant: {p.assistant_calls}, user: {p.user_calls})"
        )
        if p.prefix in READ_ONLY_INSPECTION_TOOLS:
            lines.append(f'    "{p.prefix}": (allow_all(),),')
        elif p.subcommands:
            sorted_subs = sorted(p.subcommands.keys())
            subs_repr = ", ".join(f'"{s}"' for s in sorted_subs)
            lines.append(f'    "{p.prefix}": (')
            lines.append('        deny_flags("--force", "-f"),')
            lines.append(f"        allow_subcommands({subs_repr}),")
            lines.append("    ),")
        else:
            lines.append(f'    "{p.prefix}": (')
            lines.append("        allow_all(),")
            lines.append("    ),")
        lines.append("")

    lines.append("}")
    lines.append("")
    lines.append("policy = ExecutableGrantPolicy(default=default, prefix_matchers=prefix_matchers)")
    lines.append("")
    return "\n".join(lines)


def write_scaffolded_policy(
    output_path: Path | str,
    content: str,
    *,
    force: bool = False,
) -> Path:
    """Write scaffolded policy content to file with safety overwrite check."""
    target = Path(output_path).resolve()
    if target.is_file() and not force:
        raise FileExistsError(
            f"policy file already exists at {target}; pass force=True to overwrite"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content.encode("utf-8"))
    return target
