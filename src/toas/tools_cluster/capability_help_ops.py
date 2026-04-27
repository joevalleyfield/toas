from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

CAPABILITY_TOPICS: dict[str, tuple[str, ...]] = {
    "core": ("read_file", "search", "replace_block", "apply_patch", "shell", "shell_script", "procedure"),
    "editing": ("read_file", "search", "replace_block", "apply_patch", "replace_range", "write_file"),
    "shell": ("shell", "shell_script"),
    "debug": ("capability_help", "echo_block", "get_structure", "code_survey", "replace_range"),
}

TOOL_EXAMPLES: dict[str, str] = {
    "read_file": '- operation: read_file\n  arguments:\n    path: src/toas/step.py',
    "search": '- operation: search\n  arguments:\n    query: TODO\n    path: .',
    "replace_block": (
        "- operation: replace_block\n"
        "  arguments:\n"
        "    path: src/app.py\n"
        "    search_block: old\n"
        "    replacement_block: new\n"
        "    match_mode: default"
    ),
    "replace_range": (
        "- operation: replace_range\n"
        "  arguments:\n"
        "    path: src/app.py\n"
        "    start_line: 10\n"
        "    end_line: 14\n"
        "    replacement_block: |\n"
        "      def new_fn():\n"
        "          return 1"
    ),
    "shell": '- operation: shell\n  arguments:\n    argv: ["pwd"]',
    "shell_script": (
        "- operation: shell_script\n"
        "  arguments:\n"
        "    script: |\n"
        "      find tasks/open -maxdepth 1 -type f | head -20"
    ),
    "write_file": '- operation: write_file\n  arguments:\n    path: notes.txt\n    content: hello',
    "apply_patch": (
        "- operation: apply_patch\n"
        "  arguments:\n"
        "    patch: |\n"
        "      *** Begin Patch\n"
        "      *** Update File: notes.txt\n"
        "      @@\n"
        "      -old line\n"
        "      +new line\n"
        "      *** End Patch"
    ),
    "echo_block": '- operation: echo_block\n  arguments:\n    block: |\n      line one\n      line two',
    "get_structure": '- operation: get_structure\n  arguments:\n    path: src',
    "code_survey": (
        "- operation: code_survey\n"
        "  arguments:\n"
        "    path: src/toas\n"
        "    top_n: 15"
    ),
    "capability_help": '- operation: capability_help\n  arguments:\n    topic: core',
    "procedure": '- operation: procedure\n  arguments:\n    name: repo_discovery_triage_v1',
}


@dataclass(frozen=True)
class CapabilityHelpDeps:
    registry: dict
    shell_allowed: set[str]


def tool_summary(name: str) -> str:
    if name == "echo":
        return "echo back provided text"
    if name == "read_file":
        return "read UTF-8 files inside the workspace"
    if name == "search":
        return "search workspace text with rg"
    if name == "write_file":
        return "create or overwrite a workspace file with explicit content"
    if name == "echo_block":
        return "echo multiline block payload for YAML/debug diagnostics"
    if name == "get_structure":
        return "map Python def/class structure for a file or directory"
    if name == "code_survey":
        return "report largest Python files/functions/classes for decomposition planning"
    if name == "replace_range":
        return "replace an explicit line range in a workspace file"
    if name == "shell":
        return "run bounded shell commands inside the workspace"
    if name == "shell_script":
        return "run bounded shell scripts inside the workspace"
    if name == "replace_block":
        return "replace a block of text in a workspace file"
    if name == "apply_patch":
        return "apply structured multi-file patches with strict context matching"
    if name == "capability_help":
        return "return capability/tool detail by topic or tool name"
    if name == "procedure":
        return "load and execute a named reusable procedure asset"
    return name


def tool_detail_lines(name: str, *, deps: CapabilityHelpDeps) -> list[str]:
    if name not in deps.registry:
        raise RuntimeError(f"unknown tool for capability help: {name}")
    required = ", ".join(deps.registry[name].required_args) or "none"
    lines = [f"- `{name}`: {tool_summary(name)}", f"  required args: {required}"]
    if name == "shell":
        allowed = ", ".join(sorted(deps.shell_allowed))
        lines.append("  callable shape: use `arguments.argv` as list[str] (not `command`/`cmd` in action lane)")
        lines.append(f"  limits: workspace-bounded, timeout_s <= 30, allowed commands: {allowed}")
    if name == "shell_script":
        allowed = ", ".join(sorted(deps.shell_allowed))
        lines.append("  callable shape: use `arguments.script` as shell text for multiline/operators")
        lines.append(f"  limits: workspace-bounded, timeout_s <= 30, leading command must be allowed: {allowed}")
    if name == "capability_help":
        lines.append("  topics: core, editing, shell, debug, all, or any single tool name")
    if name == "apply_patch":
        lines.append("  callable shape: use `arguments.patch` with *** Begin Patch / *** End Patch envelope")
        lines.append("  behavior: fails on context mismatch; does not silently relocate edits")
    if name == "code_survey":
        lines.append("  callable shape: use `arguments.path` (optional, default `src`) and `arguments.top_n` (optional, default 20)")
        lines.append("  behavior: Python-only AST survey; skips files with parse errors and reports them")
    example = TOOL_EXAMPLES.get(name)
    if example:
        lines.extend(["  example:", f"```yaml\n{example}\n```"])
    return lines


def resolve_capability_topic(topic: str, *, deps: CapabilityHelpDeps) -> str:
    if topic in CAPABILITY_TOPICS or topic == "all" or topic in deps.registry:
        return topic
    aliases = {
        "capabilities": "core",
        "capability": "core",
        "help": "core",
        "tools": "all",
    }
    if topic in aliases:
        return aliases[topic]

    candidates = sorted(set(CAPABILITY_TOPICS) | set(deps.registry) | {"all"})
    best_name = ""
    best_ratio = 0.0
    for candidate in candidates:
        ratio = SequenceMatcher(a=topic, b=candidate).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_name = candidate
    if best_name and best_ratio >= 0.72:
        return best_name
    raise RuntimeError(f"unknown capability_help topic: {topic}")


def select_tools_for_topic(topic: str, *, deps: CapabilityHelpDeps) -> tuple[str, ...]:
    if topic in CAPABILITY_TOPICS:
        return tuple(name for name in CAPABILITY_TOPICS[topic] if name in deps.registry)
    if topic == "all":
        return tuple(sorted(deps.registry))
    if topic in deps.registry:
        return (topic,)
    raise RuntimeError(f"unknown capability_help topic: {topic}")


def run_capability_help(args: dict, *, deps: CapabilityHelpDeps) -> dict:
    topic = args.get("topic", "core")
    if not isinstance(topic, str) or not topic.strip():
        raise RuntimeError("invalid arguments for tool capability_help: topic must be a non-empty string")
    requested = topic.strip().lower()
    normalized = resolve_capability_topic(requested, deps=deps)
    selected = select_tools_for_topic(normalized, deps=deps)
    lines = [f"capability help: {normalized}"]
    if normalized != requested:
        lines.append(f"normalized from topic: {requested}")
    lines.append("aliases accepted: operation/tool_name, arguments/args/params, intent/intention")
    for name in selected:
        lines.extend(tool_detail_lines(name, deps=deps))
    return {
        "tool_name": "capability_help",
        "ok": True,
        "summary": f"{normalized}: {len(selected)} tool(s)",
        "topic": normalized,
        "tools": list(selected),
        "content": "\n".join(lines),
    }
