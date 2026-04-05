from .backend_policy import BackendGenerationPolicy, default_backend_policy
from .tools import REGISTRY


def _tool_summary(name: str) -> str:
    if name == "echo":
        return "echo back provided text"
    if name == "read_file":
        return "read UTF-8 files inside the workspace"
    if name == "search":
        return "search workspace text with rg"
    if name == "shell":
        return "run bounded shell commands inside the workspace"
    return name


def _shell_limits() -> str:
    shell = REGISTRY["shell"]
    _ = shell
    return "shell is workspace-bounded, allowlisted, and limited to timeout_s <= 30"


def render_capability_overview(policy: BackendGenerationPolicy | None = None) -> str:
    policy = policy or default_backend_policy()
    tool_lines = "\n".join(
        f"- `{name}`: {_tool_summary(name)}"
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
