from .backend_policy import BackendGenerationPolicy, default_backend_policy
from .tools import REGISTRY, SHELL_ALLOWED


def _tool_summary(name: str) -> str:
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
    if name == "shell":
        return "run bounded shell commands inside the workspace"
    if name == "replace_block":
        return "replace a block of text in a workspace file"
    return name


def _shell_limits() -> str:
    allowed = ", ".join(sorted(SHELL_ALLOWED))
    return f"shell is workspace-bounded and limited to timeout_s <= 30; allowed commands: {allowed}"


def _tool_shape_hint(name: str) -> str:
    if name == "echo":
        return "- operation: echo\n  arguments:\n    text: hello"
    if name == "read_file":
        return "- operation: read_file\n  arguments:\n    path: src/toas/step.py"
    if name == "search":
        return "- operation: search\n  arguments:\n    query: TODO\n    path: ."
    if name == "shell":
        return "- operation: shell\n  arguments:\n    argv: [\"pwd\"]"
    if name == "write_file":
        return "- operation: write_file\n  arguments:\n    path: notes.txt\n    content: hello"
    if name == "echo_block":
        return "- operation: echo_block\n  arguments:\n    block: |\n      line one\n      line two"
    if name == "replace_block":
        return (
            "- operation: replace_block\n"
            "  arguments:\n"
            "    path: src/app.py\n"
            "    search_block: old\n"
            "    replacement_block: new"
        )
    return f"- operation: {name}\n  arguments: {{}}"


def render_capability_overview(policy: BackendGenerationPolicy | None = None) -> str:
    policy = policy or default_backend_policy()
    tool_lines = "\n".join(
        f"- `{name}`: {_tool_summary(name)} (required args: {', '.join(REGISTRY[name].required_args) or 'none'})"
        for name in sorted(REGISTRY)
    )
    shape_lines = "\n".join(
        f"`{name}` example:\n```yaml\n{_tool_shape_hint(name)}\n```"
        for name in sorted(REGISTRY)
    )
    avoid_terms = ", ".join(f"`{term}`" for term in policy.avoid_terms)

    return (
        "Capabilities available in this TOAS session:\n"
        "- I can inspect and shape transcript/history state, including selected head, jump binding, transcript projection, LLM-input inspection, and rebuild.\n"
        "- I can use explicit prompt-library material that you choose to surface.\n"
        "- I can use local action blocks instead of provider-native tool protocols when needed.\n"
        "- I can use these local tools:\n"
        f"{tool_lines}\n"
        "Callable shape:\n"
        "- aliases accepted: `operation`/`tool_name`, `arguments`/`args`\n"
        "- use single operation by default\n"
        "- use an operation list only for tightly coupled work (for example, coherent multi-file edits)\n"
        "Multi-op example:\n"
        "```yaml\n"
        "- operation: replace_block\n"
        "  arguments:\n"
        "    path: src/a.py\n"
        "    search_block: OLD_A\n"
        "    replace_block: NEW_A\n"
        "- operation: replace_block\n"
        "  arguments:\n"
        "    path: src/b.py\n"
        "    search_block: OLD_B\n"
        "    replace_block: NEW_B\n"
        "```\n"
        f"{shape_lines}\n"
        "Important limits:\n"
        f"- {_shell_limits()}.\n"
        "- I only have the capabilities explicitly available in this runtime; I should not imply hidden tools or provider-native tool access.\n"
        f"- For awkward backends, neutral action language is safer than {avoid_terms}."
    )


def render_capability_repo_work() -> str:
    return (
        "For repo and local-runtime work in this session, you can rely on these capabilities:\n"
        "- `read_file` for reading workspace files.\n"
        "- `search` for searching workspace text.\n"
        "- `shell` for bounded workspace-local commands.\n"
        "- `replace_block` for making targeted text replacements in workspace files.\n"
        "- `write_file` for explicit file creation or full overwrite.\n"
        "- `echo_block` for debugging YAML block payload shape.\n"
        "- transcript/history inspection through transcript projection, LLM-input projection, and history/head controls.\n"
        "When asking for actions, prefer local action blocks or neutral operation language rather than provider-native tool wording."
    )


def render_capability_start_here() -> str:
    return (
        "If you are not sure how to start, you can begin by asking me to:\n"
        "- clarify the task before solutioning,\n"
        "- inspect the current transcript/history state,\n"
        "- search or read files in the workspace,\n"
        "- run a bounded shell command,\n"
        "- or operate within a local action protocol instead of provider-native tool calling.\n"
        "I should stay within the capabilities explicitly surfaced in this session."
    )
