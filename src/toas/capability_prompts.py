from importlib import resources

from .backend_policy import BackendGenerationPolicy, default_backend_policy
from .tools import REGISTRY, SHELL_ALLOWED

_CORE_TOOLS = ("read_file", "search", "replace_block", "apply_patch", "shell", "shell_script", "capability_help", "capture_task_thread")
_DEBUG_TOOLS = ("capability_help", "echo_block", "get_structure", "code_survey", "replace_range")


def _tool_summary(name: str) -> str:
    if name == "echo":
        return "echo back provided text"
    if name == "read_file":
        return "read UTF-8 files inside the workspace, optionally by line range"
    if name == "search":
        return "search workspace text with rg"
    if name == "write_file":
        return "create, append, or overwrite a workspace file with explicit content; writes obey tool_writes.newline_style"
    if name == "echo_block":
        return "echo multiline block payload for YAML/debug diagnostics"
    if name == "get_structure":
        return "map Python def/class structure for a file or directory"
    if name == "code_survey":
        return "report largest Python files/functions/classes for decomposition planning"
    if name == "replace_range":
        return "replace an explicit line range in a workspace file; writes obey tool_writes.newline_style"
    if name == "shell":
        return "run bounded shell commands inside the workspace"
    if name == "shell_script":
        return "run bounded shell scripts inside the workspace"
    if name == "replace_block":
        return "replace a block of text in a workspace file; writes obey tool_writes.newline_style"
    if name == "apply_patch":
        return "apply structured multi-file patches with strict context matching; add/update writes obey tool_writes.newline_style"
    if name == "capture_task_thread":
        return "synchronously defer side threads, cleanup, risks, or blockers to the task tracker"
    return name


def _shell_limits() -> str:
    allowed = ", ".join(sorted(SHELL_ALLOWED))
    return f"shell/shell_script are workspace-bounded with timeout_s max 30s; allowed commands: {allowed}"


def _load_template(name: str) -> str:
    path = resources.files("toas").joinpath("prompts").joinpath("dynamic").joinpath("capabilities").joinpath(f"{name}.txt")
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("---\n"):
        marker = "\n---\n"
        end = raw.find(marker, 4)
        if end != -1:
            return raw[end + len(marker):].strip()
    return raw.strip()


def _tool_shape_hint(name: str) -> str:
    if name == "echo":
        return "- operation: echo\n  arguments:\n    text: hello"
    if name == "read_file":
        return (
            "- operation: read_file\n"
            "  arguments:\n"
            "    path: src/toas/step.py\n"
            "    start_line: 10\n"
            "    end_line: 14\n"
            "    number_lines: true"
        )
    if name == "search":
        return "- operation: search\n  arguments:\n    query: TODO\n    path: ."
    if name == "shell":
        return "- operation: shell\n  arguments:\n    argv: [\"pwd\"]"
    if name == "shell_script":
        return (
            "- operation: shell_script\n"
            "  arguments:\n"
            "    script: |\n"
            "      find tasks/open -maxdepth 1 -type f | head -20"
        )
    if name == "write_file":
        return (
            "- operation: write_file\n"
            "  arguments:\n"
            "    path: notes.txt\n"
            "    content: hello\n"
            "    append: false\n"
            "    force: false"
        )
    if name == "echo_block":
        return "- operation: echo_block\n  arguments:\n    block: |\n      line one\n      line two"
    if name == "get_structure":
        return "- operation: get_structure\n  arguments:\n    path: src"
    if name == "code_survey":
        return (
            "- operation: code_survey\n"
            "  arguments:\n"
            "    path: src/toas\n"
            "    top_n: 15"
        )
    if name == "replace_range":
        return (
            "- operation: replace_range\n"
            "  arguments:\n"
            "    path: src/app.py\n"
            "    start_line: 10\n"
            "    end_line: 14\n"
            "    replacement_block: |\n"
            "      def new_fn():\n"
            "          return 1\n"
        )
    if name == "replace_block":
        return (
            "- operation: replace_block\n"
            "  arguments:\n"
            "    path: src/app.py\n"
            "    search_block: old\n"
            "    replacement_block: new\n"
            "    match_mode: default"
        )
    if name == "apply_patch":
        return (
            "- operation: apply_patch\n"
            "  arguments:\n"
            "    patch: |\n"
            "      *** Begin Patch\n"
            "      *** Update File: src/app.py\n"
            "      @@\n"
            "      -old\n"
            "      +new\n"
            "      *** End Patch"
        )
    if name == "capture_task_thread":
        return (
            "- operation: capture_task_thread\n"
            "  arguments:\n"
            "    title: \"refactor session path resolution\"\n"
            "    kind: \"cleanup\"\n"
            "    evidence: \"duplicate logic in cli.py and operator_api.py\"\n"
            "    active_task_id: 677\n"
            "    scope_hint: \"micro\""
        )
    return f"- operation: {name}\n  arguments: {{}}"


def _profile_tool_names(profile: str) -> list[str]:
    if profile == "core":
        return [name for name in _CORE_TOOLS if name in REGISTRY]
    if profile == "debug":
        names = set(_CORE_TOOLS) | set(_DEBUG_TOOLS)
        return [name for name in sorted(names) if name in REGISTRY]
    return sorted(REGISTRY)


def _visible_tool_names(profile: str, hidden_tools: tuple[str, ...]) -> list[str]:
    hidden = {name for name in hidden_tools if isinstance(name, str)}
    return [name for name in _profile_tool_names(profile) if name not in hidden]


def render_capability_overview(
    policy: BackendGenerationPolicy | None = None,
    *,
    profile: str = "core",
    hidden_tools: tuple[str, ...] = (),
) -> str:
    policy = policy or default_backend_policy()
    visible_tools = _visible_tool_names(profile, hidden_tools)
    tool_lines = "\n".join(
        f"- `{name}`: {_tool_summary(name)} (required args: {', '.join(REGISTRY[name].required_args) or 'none'})"
        for name in visible_tools
    )
    shape_lines = "\n".join(
        f"`{name}` example:\n```yaml\n{_tool_shape_hint(name)}\n```"
        for name in visible_tools
    )
    avoid_terms = ", ".join(f"`{term}`" for term in policy.avoid_terms)

    capture_task_thread_policy = ""
    if "capture_task_thread" in visible_tools:
        capture_task_thread_policy = """

Task Capture Policy (when using `capture_task_thread`):
- Trigger: Call when encountering a tangent, cleanup, follow-up, blocker, missing test, or risk that is outside the immediate scope of the primary task.
- Fork Rule: The tool call acts as a fork marker that transfers the side thread out of the current conversation. Do not pursue the side thread inline.
- Payloads: Keep arguments minimal and concise (concise title, short explanation of evidence).
- Resume: On receiving a `continue` directive in the tool outcome, immediately return to the primary task in your next response. Do not bloat the conversation context with details of the captured task."""

    template = _load_template("overview_v1")
    return template.format(
        profile=profile,
        tool_lines=tool_lines,
        shape_lines=shape_lines,
        shell_limits=_shell_limits(),
        avoid_terms=avoid_terms,
        capture_task_thread_policy=capture_task_thread_policy,
    )


def render_capability_repo_work(
    *,
    profile: str = "core",
    hidden_tools: tuple[str, ...] = (),
) -> str:
    visible = set(_visible_tool_names(profile, hidden_tools))
    lines: list[str] = []
    if "read_file" in visible:
        lines.append("- `read_file` for reading workspace files (`arguments.path`), optionally bounded by `arguments.start_line` and `arguments.end_line` and optionally numbered with `arguments.number_lines`.")
    if "search" in visible:
        lines.append("- `search` for searching workspace text (`arguments.query`, optional `arguments.path`) when explicit structured matches/limits are needed.")
    if "shell" in visible:
        lines.append("- `shell` for bounded workspace-local commands (`arguments.argv` list[str], not `command`).")
        lines.append("- for fast first-pass repo discovery, prefer `$ rg ...` via user-shell shorthand before switching to structured `search`.")
    if "shell_script" in visible:
        lines.append("- `shell_script` for bounded multiline/pipeline shell text (`arguments.script`).")
    if "replace_block" in visible:
        lines.append("- `replace_block` for targeted text replacements (`arguments.path`, `arguments.search_block`, `arguments.replacement_block`).")
    if "apply_patch" in visible:
        lines.append("- `apply_patch` for structured multi-file edits (`arguments.patch`); strict context matching, no silent relocation on mismatch.")
    if "code_survey" in visible:
        lines.append("- `code_survey` for ranked module/function/class size diagnostics (`arguments.path`, optional `arguments.top_n`).")
    if "write_file" in visible:
        lines.append("- `write_file` for explicit file creation, append, or overwrite (`arguments.path`, `arguments.content`, optional `arguments.append`, optional `arguments.force`).")
    if {"write_file", "replace_range", "replace_block", "apply_patch"} & visible:
        lines.append("- file-writing tools honor `tool_writes.newline_style`: `auto` preserves an existing file's newline style and defaults new files to LF; `lf` and `crlf` force those styles.")
    if "capture_task_thread" in visible:
        lines.append("- `capture_task_thread` for synchronously deferring side threads, cleanup, blockers, or missing tests (`arguments.title`, `arguments.kind`).")
    if "capability_help" in visible:
        lines.append("- `capability_help` for compact on-demand tool/policy detail by topic or tool name (`arguments.topic`).")
        lines.append("- if argument shape is uncertain before first callable action, run `capability_help` first (for example topic `shell`).")
    lines.append("- transcript/history inspection through transcript projection, LLM-input projection, and history/head controls.")
    template = _load_template("repo-work_v1")
    return template.format(capability_lines="\n".join(lines))


def render_capability_start_here() -> str:
    return _load_template("start-here_v1")
