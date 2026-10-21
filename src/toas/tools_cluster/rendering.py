import os
import re
import shlex
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
from pathlib import Path, PurePosixPath

_SINGLE_TURN_EPHEMERAL: ContextVar[bool] = ContextVar("toas_single_turn_ephemeral", default=False)


def is_single_turn_ephemeral() -> bool:
    if os.environ.get("TOAS_SINGLE_TURN_EPHEMERAL", "").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    return _SINGLE_TURN_EPHEMERAL.get()


@contextmanager
def active_single_turn_ephemeral(enabled: bool = True) -> Iterator[None]:
    token = _SINGLE_TURN_EPHEMERAL.set(enabled)
    try:
        yield
    finally:
        _SINGLE_TURN_EPHEMERAL.reset(token)

_LANGUAGE_BY_EXTENSION = {
    ".bash": "bash",
    ".c": "c",
    ".cc": "cpp",
    ".cfg": "ini",
    ".conf": "ini",
    ".cpp": "cpp",
    ".css": "css",
    ".csv": "csv",
    ".go": "go",
    ".h": "c",
    ".hpp": "cpp",
    ".html": "html",
    ".ini": "ini",
    ".java": "java",
    ".js": "javascript",
    ".json": "json",
    ".jsx": "jsx",
    ".md": "markdown",
    ".py": "python",
    ".rs": "rust",
    ".sh": "bash",
    ".sql": "sql",
    ".toml": "toml",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".txt": "text",
    ".vim": "vim",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".zsh": "zsh",
}

_LANGUAGE_BY_NAME = {
    "Dockerfile": "dockerfile",
    "Makefile": "makefile",
}


def render_shell_result(result: dict, *, status: str, tool_name: str) -> str:
    lines = [f"[{status}] {tool_name}: {result['summary']}"]
    if status == "ERROR":
        detail = str(result.get("error") or result.get("summary") or "")
        hint = _repair_hint_for_error(tool_name=tool_name, detail=detail)
        if hint:
            lines.append("next valid shape:")
            lines.append(hint)
    if result.get("stdout"):
        lines.append("stdout:")
        rendered_stdout = render_shell_stdout_import_block(result)
        if rendered_stdout is not None:
            lines.append(rendered_stdout)
        else:
            lines.append(
                render_fenced_output(
                    content=result["stdout"],
                    kind="stdout",
                    source=f"tool.{tool_name}",
                    potency="inert",
                )
            )
    if result.get("stderr"):
        lines.append("stderr:")
        lines.append(
            render_fenced_output(
                content=result["stderr"],
                kind="stderr",
                source=f"tool.{tool_name}",
                potency="inert",
            )
        )
    return "\n".join(lines)


def render_read_file_success(
    result: dict,
    *,
    status: str,
    tool_name: str,
    allow_spill: bool = True,
    scratch_dir: Path | None = None,
) -> str:
    path = str(result["path"])
    rendered_path = str(result.get("summary") or path)
    content = str(result.get("display_content", result["content"]))
    is_bounded = (
        result.get("bounded") is True
        or result.get("start_line") is not None
        or result.get("end_line") is not None
        or result.get("max_lines") is not None
        or result.get("line_start") is not None
        or result.get("line_end") is not None
        or (isinstance(result.get("summary"), str) and ":" in result["summary"] and "-" in result["summary"])
    )
    is_scratch = Path(path).resolve().is_relative_to((scratch_dir or default_scratch_dir()).resolve())
    ingestion_read = is_bounded or is_scratch
    threshold_lines = DEFAULT_BOUNDED_SPILL_THRESHOLD_LINES if ingestion_read else DEFAULT_SPILL_THRESHOLD_LINES
    threshold_bytes = DEFAULT_BOUNDED_SPILL_THRESHOLD_BYTES if ingestion_read else DEFAULT_SPILL_THRESHOLD_BYTES
    return (
        f"[{status}] {tool_name}: {path}\n"
        f"{render_import_block(content=content, path=rendered_path, source='workspace', line_start=result.get('line_start'), line_end=result.get('line_end'), allow_spill=allow_spill, threshold_lines=threshold_lines, threshold_bytes=threshold_bytes, scratch_dir=scratch_dir)}"
    )


def infer_fence_language(path: str | None) -> str:
    if not isinstance(path, str) or not path:
        return "text"
    name = PurePosixPath(path).name
    if name in _LANGUAGE_BY_NAME:
        return _LANGUAGE_BY_NAME[name]
    return _LANGUAGE_BY_EXTENSION.get(PurePosixPath(path).suffix.lower(), "text")


DEFAULT_SPILL_THRESHOLD_LINES = 40
DEFAULT_SPILL_THRESHOLD_BYTES = 4000
DEFAULT_SPILL_PREVIEW_LINES = 30
DEFAULT_BOUNDED_SPILL_THRESHOLD_LINES = 500
DEFAULT_BOUNDED_SPILL_THRESHOLD_BYTES = 50_000
DEFAULT_SPILL_SAFETY_BRAKE_LINES = 1000
DEFAULT_SPILL_SAFETY_BRAKE_BYTES = 100_000


def _format_size(byte_count: int) -> str:
    if byte_count >= 1024 * 1024:
        return f"{byte_count / (1024 * 1024):.1f} MB"
    if byte_count >= 1024:
        return f"{round(byte_count / 1024)} KB"
    return f"{byte_count} B"


def default_scratch_dir() -> Path:
    return Path(".toas/scratch")


def spill_inert_block(
    content: str,
    *,
    kind: str,
    language: str = "text",
    scratch_dir: Path | None = None,
    threshold_lines: int = DEFAULT_SPILL_THRESHOLD_LINES,
    threshold_bytes: int = DEFAULT_SPILL_THRESHOLD_BYTES,
    preview_lines: int = DEFAULT_SPILL_PREVIEW_LINES,
    block_id: str | None = None,
    single_turn_ephemeral: bool | None = None,
    ephemeral: bool | None = None,
) -> tuple[str, str, str]:
    """Spill an oversized inert block to a scratch file and return (spilled_text, rel_path, block_id)."""
    if single_turn_ephemeral is None:
        single_turn_ephemeral = ephemeral
    if single_turn_ephemeral is None:
        is_ephemeral = is_single_turn_ephemeral()
    else:
        is_ephemeral = bool(single_turn_ephemeral)

    effective_block_id = block_id or f"ib_{sha256(content.encode('utf-8')).hexdigest()[:16]}"
    target_dir = scratch_dir or default_scratch_dir()
    try:
        scratch_rel_path = str(target_dir.resolve().relative_to(Path.cwd().resolve()) / f"{effective_block_id}.txt")
    except Exception:
        scratch_rel_path = f".toas/scratch/{effective_block_id}.txt"

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / f"{effective_block_id}.txt").write_text(content, encoding="utf-8")
    except OSError:
        pass

    lines = content.splitlines()
    total_lines = len(lines)
    total_bytes = len(content.encode("utf-8"))
    size_str = _format_size(total_bytes)

    preview_slice = lines[:preview_lines]
    preview_body = "\n".join(preview_slice) + "\n" if preview_slice else ""
    preview_count = len(preview_slice)
    remaining_lines = max(0, total_lines - preview_count)

    banner = f"Output exceeded threshold ({size_str}, {total_lines} lines); spilled to `{scratch_rel_path}`."
    fence = _sized_backtick_fence(preview_body)
    info_parts = [
        language,
        "toas-output",
        f"kind={kind}",
        f"block_id={effective_block_id}",
        f'path="{scratch_rel_path}"',
        f"lines=1..{preview_count} of {total_lines}",
    ]
    if remaining_lines > 0:
        base_trailer = (
            f"[{remaining_lines} lines remaining. "
            f"Read full output (up to 500 lines without spilling) or inspect with `read_file`, `grep`, or script via path=\"{scratch_rel_path}\""
        )
        if is_ephemeral:
            trailer = (
                f"{base_trailer}; "
                "under single-turn ephemerality, sipping only the tail drops the previewed head unless persisted into state]"
            )
        else:
            trailer = f"{base_trailer}]"
    else:
        trailer = (
            f"[Output truncated by byte size ({size_str}). "
            f"Read full output (up to 500 lines without spilling) or inspect with `read_file`, `grep`, or script via path=\"{scratch_rel_path}\"]"
        )

    spilled_text = f"{banner}\n\n{fence}{' '.join(info_parts)}\n{preview_body}{fence}\n{trailer}"
    return spilled_text, scratch_rel_path, effective_block_id


def render_fenced_output(  # noqa: PLR0913
    *,
    content: str,

    kind: str,
    source: str = "",
    potency: str = "inert",
    language: str = "text",
    path: str | None = None,
    status: str | None = None,
    line_start: int | None = None,
    line_end: int | None = None,
    block_id: str | None = None,
    allow_spill: bool | None = None,
    scratch_dir: Path | None = None,
    threshold_lines: int = DEFAULT_SPILL_THRESHOLD_LINES,
    threshold_bytes: int = DEFAULT_SPILL_THRESHOLD_BYTES,
    preview_lines: int = DEFAULT_SPILL_PREVIEW_LINES,
    single_turn_ephemeral: bool | None = None,
    ephemeral: bool | None = None,
) -> str:
    lines = content.splitlines()
    total_lines = len(lines)
    total_bytes = len(content.encode("utf-8"))
    effective_threshold_lines = min(threshold_lines, DEFAULT_SPILL_SAFETY_BRAKE_LINES)
    effective_threshold_bytes = min(threshold_bytes, DEFAULT_SPILL_SAFETY_BRAKE_BYTES)
    should_allow_spill = (kind in {"result", "stdout", "stderr"} and not source.startswith("command.")) if allow_spill is None else allow_spill
    if should_allow_spill and (total_lines > effective_threshold_lines or total_bytes > effective_threshold_bytes):
        spilled_text, _, _ = spill_inert_block(
            content,
            kind=kind,
            language=language,
            scratch_dir=scratch_dir,
            threshold_lines=effective_threshold_lines,
            threshold_bytes=effective_threshold_bytes,
            preview_lines=preview_lines,
            block_id=block_id,
            single_turn_ephemeral=single_turn_ephemeral,
            ephemeral=ephemeral,
        )
        return spilled_text

    if block_id:
        target_dir = scratch_dir or default_scratch_dir()
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            scratch_file = target_dir / f"{block_id}.txt"
            if not scratch_file.exists():
                scratch_file.write_text(content, encoding="utf-8")
        except OSError:
            pass

    fence = _sized_backtick_fence(content)
    info_parts = [
        language,
        "toas-output",
        f"kind={kind}",
        f"source={_format_fence_attr(source)}",
        f"potency={potency}",
    ]
    if path:
        info_parts.append(f"path={_format_fence_attr(path)}")
    if line_start is not None:
        info_parts.append(f"line_start={line_start}")
    if line_end is not None:
        info_parts.append(f"line_end={line_end}")
    if block_id:
        info_parts.append(f"block_id={_format_fence_attr(block_id)}")
    if status:
        info_parts.append(f"status={status}")
    body = content if content.endswith("\n") else f"{content}\n"
    return f"{fence}{' '.join(info_parts)}\n{body}{fence}"


def render_import_block(  # noqa: PLR0913
    *,
    content: str,
    path: str | None = None,
    source: str | None = None,
    language: str | None = None,
    kind: str = "file",
    line_start: int | None = None,
    line_end: int | None = None,
    block_id: str | None = None,
    allow_spill: bool | None = None,
    scratch_dir: Path | None = None,
    threshold_lines: int | None = None,
    threshold_bytes: int | None = None,
    preview_lines: int = DEFAULT_SPILL_PREVIEW_LINES,
    single_turn_ephemeral: bool | None = None,
    ephemeral: bool | None = None,
) -> str:
    effective_source = source or "workspace"
    is_bounded = line_start is not None or line_end is not None or (isinstance(path, str) and ":" in path and "-" in path)
    effective_threshold_lines = (
        threshold_lines
        if threshold_lines is not None
        else (DEFAULT_BOUNDED_SPILL_THRESHOLD_LINES if is_bounded else DEFAULT_SPILL_THRESHOLD_LINES)
    )
    effective_threshold_bytes = (
        threshold_bytes
        if threshold_bytes is not None
        else (DEFAULT_BOUNDED_SPILL_THRESHOLD_BYTES if is_bounded else DEFAULT_SPILL_THRESHOLD_BYTES)
    )
    return render_fenced_output(
        content=content,
        kind=kind,
        source=effective_source,
        potency="inert",
        language=language or infer_fence_language(path),
        path=path,
        line_start=line_start,
        line_end=line_end,
        block_id=block_id or stable_import_block_id(
            kind=kind,
            path=path,
            source=effective_source,
            line_start=line_start,
            line_end=line_end,
            content=content,
        ),
        allow_spill=allow_spill,
        scratch_dir=scratch_dir,
        threshold_lines=effective_threshold_lines,
        threshold_bytes=effective_threshold_bytes,
        preview_lines=preview_lines,
        single_turn_ephemeral=single_turn_ephemeral,
        ephemeral=ephemeral,
    )


def render_shell_stdout_import_block(result: dict) -> str | None:
    if not result.get("ok"):
        return None
    stdout = result.get("stdout")
    if not isinstance(stdout, str) or not stdout:
        return None
    path = _infer_shell_file_output_path(result.get("argv"))
    if path is None:
        return None
    return render_import_block(
        content=stdout,
        path=path,
        source=_shell_source_text(result.get("argv")),
    )


def _sized_backtick_fence(content: str) -> str:
    max_run = max((len(match.group(0)) for match in re.finditer(r"`+", content)), default=0)
    return "`" * max(3, max_run + 1)


def _format_fence_attr(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:@+-]+", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def stable_import_block_id(
    *,
    kind: str,
    path: str | None,
    source: str,
    line_start: int | None,
    line_end: int | None,
    content: str,
) -> str:
    payload = "\x1f".join(
        [
            kind,
            path or "",
            source,
            "" if line_start is None else str(line_start),
            "" if line_end is None else str(line_end),
            content,
        ]
    )
    return f"ib_{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _infer_shell_file_output_path(argv: object) -> str | None:
    if not isinstance(argv, list) or not all(isinstance(part, str) for part in argv):
        return None
    command = _shell_command_parts(argv)
    if not command:
        return None
    if command[0] == "cat" and len(command) == 2:
        return command[1]
    if command[0] == "sed" and len(command) == 4 and command[1] == "-n":
        return command[3]
    if command[0] in {"head", "tail"} and len(command) >= 2:
        candidate = command[-1]
        return candidate if not candidate.startswith("-") and not candidate.isdigit() else None
    return None


def _shell_command_parts(argv: list[str]) -> list[str]:
    if len(argv) >= 3 and argv[0] in {"sh", "bash", "zsh"} and argv[1] in {"-lc", "-ic", "-c"}:
        try:
            return shlex.split(argv[2])
        except ValueError:
            return []
    return argv


def _shell_source_text(argv: object) -> str:
    if not isinstance(argv, list) or not all(isinstance(part, str) for part in argv):
        return "shell"
    command = _shell_command_parts(argv)
    return shlex.join(command or argv)


def render_search_success(result: dict, *, status: str, tool_name: str) -> str:
    content = result.get("content", "")
    if content:
        excerpt_blocks = render_search_excerpt_blocks(result)
        if excerpt_blocks:
            return f"[{status}] {tool_name}: {result['summary']}\n" + "\n".join(excerpt_blocks)
        fenced_content = render_fenced_output(
            content=content,
            kind="result",
            source=f"tool.{tool_name}",
            potency="inert",
        )
        return f"[{status}] {tool_name}: {result['summary']}\n{fenced_content}"
    return f"[{status}] {tool_name}: {result['summary']}"


def render_search_error(result: dict, *, status: str, tool_name: str) -> str:
    rendered_error = render_default_error(result, status=status, tool_name=tool_name)
    excerpt_blocks = render_search_excerpt_blocks(result)
    if not excerpt_blocks:
        return rendered_error
    return f"{rendered_error}\npartial matches:\n" + "\n".join(excerpt_blocks)


def _make_relative(path: str, base: str | None) -> str:
    if not isinstance(path, str) or not isinstance(base, str):
        return path
    try:
        if os.path.isfile(base):
            return os.path.relpath(path, os.path.dirname(base))
        return os.path.relpath(path, base)
    except (ValueError, OSError):
        return path


def render_search_excerpt_blocks(result: dict) -> list[str]:
    matches = result.get("matches")
    if not isinstance(matches, list):
        content = result.get("content")
        matches = content.splitlines() if isinstance(content, str) else []

    if not matches:
        return []

    groups: dict[str, list[tuple[int, str]]] = {}
    search_base = result.get("path", ".")

    for raw_match in matches:
        parsed = _parse_search_match(raw_match)
        if parsed is None:
            return []
        path, line_no, text = parsed
        rel_path = Path(_make_relative(path, search_base)).as_posix()

        groups.setdefault(rel_path, []).append((line_no, text))

    if not groups:
        return []

    sorted_paths = sorted(groups.keys())
    lines: list[str] = []
    for path in sorted_paths:
        if lines:
            lines.append("")
        lines.append(path)
        for line_no, text in sorted(groups[path], key=lambda x: x[0]):
            lines.append(f"    {line_no}: {text}")

    content = "\n".join(lines) + "\n"

    block_id = f"ib_{sha256(content.encode('utf-8')).hexdigest()[:16]}"

    return [
        render_fenced_output(
            content=content,
            kind="result",
            source="tool.search",
            potency="inert",
            language="python",
            path=None,
            block_id=block_id,
        )
    ]


def _parse_search_match(raw_match: object) -> tuple[str, int, str] | None:
    if not isinstance(raw_match, str):
        return None
    match = re.fullmatch(r"(.+?):([0-9]+):(.*)", raw_match)
    if match is None:
        return None
    path, line_no_text, text = match.groups()
    return path, int(line_no_text), text


def render_replace_block_success(result: dict, *, status: str, tool_name: str) -> str:
    base = f"[{status}] {tool_name}: {result.get('summary', '')}"
    path = result.get("path")
    if isinstance(path, str) and path:
        base += f" ({path})"
    changed_start = result.get("changed_line_start")
    changed_end = result.get("changed_line_end")
    if isinstance(changed_start, int) and isinstance(changed_end, int):
        base += f" lines {changed_start}-{changed_end}"

    preview = result.get("preview")
    if isinstance(preview, str) and preview.strip():
        fenced_preview = render_fenced_output(
            content=preview,
            kind="result",
            source=f"tool.{tool_name}",
            potency="inert",
            path=path,
        )
        return f"{base}\npreview:\n{fenced_preview}"

    content = result.get("content")
    if isinstance(content, str) and content.strip():
        lines = content.splitlines()
        if len(lines) > 20:
            head = "\n".join(lines[:8])
            tail = "\n".join(lines[-8:])
            preview_content = f"{head}\n...\n{tail}"
        else:
            preview_content = content.strip()
        fenced_preview = render_fenced_output(
            content=preview_content,
            kind="result",
            source=f"tool.{tool_name}",
            potency="inert",
            path=path,
        )
        return f"{base}\npreview:\n{fenced_preview}"
    return base


def render_default_success(result: dict, *, status: str, tool_name: str) -> str:
    summary = result.get("summary") or ""
    content = result.get("content")
    if isinstance(content, str):
        content = content.strip()
    if isinstance(content, str) and content and content != summary:
        if "\n" in content:
            fenced_content = render_fenced_output(
                content=content,
                kind="result",
                source=f"tool.{tool_name}",
                potency="inert",
            )
            detail = f"{summary}\n{fenced_content}" if summary else fenced_content
        else:
            detail = f"{summary}\n{content}" if summary else content
    else:
        detail = summary or content or ""
    intention = result.get("intention")
    if not isinstance(intention, str) or not intention.strip():
        intention = result.get("intent")
    if isinstance(intention, str) and intention.strip():
        return f"[{status}] {tool_name} ({intention.strip()}): {detail}"
    return f"[{status}] {tool_name}: {detail}"


def render_default_error(result: dict, *, status: str, tool_name: str) -> str:
    detail = result.get("error") or result.get("summary") or result.get("content") or ""
    if isinstance(detail, str):
        hint = _repair_hint_for_error(tool_name=tool_name, detail=detail)
        if hint:
            detail = f"{detail}\nnext valid shape:\n{hint}"
        if "\n" in detail:
            detail = render_fenced_output(
                content=detail,
                kind="result",
                source=f"tool.{tool_name}",
                potency="inert",
                status="error",
            )
    intention = result.get("intention")
    if not isinstance(intention, str) or not intention.strip():
        intention = result.get("intent")
    if isinstance(intention, str) and intention.strip():
        return f"[{status}] {tool_name} ({intention.strip()}): {detail}"
    return f"[{status}] {tool_name}: {detail}"


def _repair_hint_for_error(*, tool_name: str, detail: str) -> str | None:
    missing_match = re.search(r"missing (.+)$", detail)
    if detail.startswith("invalid arguments for tool ") and missing_match is not None:
        missing = [part.strip() for part in missing_match.group(1).split(",") if part.strip()]
        if missing:
            args_lines = [f"    {name}: <value>" for name in missing]
            return "\n".join(
                [
                    f"- operation: {tool_name}",
                    "  arguments:",
                    *args_lines,
                ]
            )

    if tool_name == "shell":
        if "argv must be a non-empty list[str]" in detail:
            return (
                "- operation: shell\n"
                "  arguments:\n"
                "    argv: [\"pwd\"]"
            )
        if "cwd must be a string" in detail:
            return (
                "- operation: shell\n"
                "  arguments:\n"
                "    argv: [\"pwd\"]\n"
                "    cwd: \".\""
            )
    if tool_name == "shell_script":
        if "script must be a non-empty string" in detail:
            return (
                "- operation: shell_script\n"
                "  arguments:\n"
                "    script: |\n"
                "      pwd\n"
                "      ls -la"
            )
    if tool_name == "capability_help":
        if "topic must be a non-empty string" in detail:
            return (
                "- operation: capability_help\n"
                "  arguments:\n"
                "    topic: core"
            )
    if tool_name == "apply_patch":
        if "patch must be a non-empty string" in detail or "patch must start with" in detail:
            return (
                "- operation: apply_patch\n"
                "  arguments:\n"
                "    patch: |\n"
                "      *** Begin Patch\n"
                "      *** Update File: path/to/file.txt\n"
                "      @@\n"
                "      -old\n"
                "      +new\n"
                "      *** End Patch"
            )
    return None


RESULT_RENDERERS: dict[str, Callable[[dict], str]] = {
    "shell": lambda result: render_shell_result(
        result,
        status="OK" if result["ok"] else "ERROR",
        tool_name=result["tool_name"],
    ),
    "shell_script": lambda result: render_shell_result(
        result,
        status="OK" if result["ok"] else "ERROR",
        tool_name=result["tool_name"],
    ),
    "python_script": lambda result: render_shell_result(
        result,
        status="OK" if result["ok"] else "ERROR",
        tool_name=result["tool_name"],
    ),
    "powershell_script": lambda result: render_shell_result(
        result,
        status="OK" if result["ok"] else "ERROR",
        tool_name=result["tool_name"],
    ),
    "interpreter_script": lambda result: render_shell_result(
        result,
        status="OK" if result["ok"] else "ERROR",
        tool_name=result["tool_name"],
    ),
}

SUCCESS_RENDERERS: dict[str, Callable[[dict], str]] = {
    "read_file": lambda result: render_read_file_success(
        result,
        status="OK",
        tool_name=result["tool_name"],
    ),
    "search": lambda result: render_search_success(
        result,
        status="OK",
        tool_name=result["tool_name"],
    ),
    "get_structure": lambda result: (
        f"[OK] get_structure: {result.get('summary', '')}\n"
        + render_fenced_output(
            content="\n".join(
                f"{item['kind']}.{item['name']} ({item['start_line']}-{item['end_line']}) {item.get('path', '')}"
                for item in result.get("structure", [])
            ),
            kind="result",
            source="tool.get_structure",
            potency="inert",
        )
    ) if result.get("structure") else f"[OK] get_structure: {result.get('summary', '')}",
    "replace_range": lambda result: f"[OK] replace_range: {result.get('summary', '')}",
    "replace_block": lambda result: render_replace_block_success(
        result,
        status="OK",
        tool_name=result["tool_name"],
    ),
}


def shape_result_content(
    result: dict,
    *,
    single_turn_ephemeral: bool | None = None,
    ephemeral: bool | None = None,
) -> str:
    if single_turn_ephemeral is None:
        single_turn_ephemeral = ephemeral
    if single_turn_ephemeral is None and isinstance(result, dict):
        single_turn_ephemeral = result.get("single_turn_ephemeral", result.get("ephemeral"))

    if single_turn_ephemeral is not None:
        with active_single_turn_ephemeral(bool(single_turn_ephemeral)):
            return _shape_result_content_body(result)
    return _shape_result_content_body(result)


def _shape_result_content_body(result: dict) -> str:
    tool_name = result["tool_name"]
    direct_renderer = RESULT_RENDERERS.get(tool_name)
    if direct_renderer is not None:
        return direct_renderer(result)

    status = "OK" if result["ok"] else "ERROR"
    if not result["ok"]:
        if tool_name == "search":
            return render_search_error(result, status=status, tool_name=tool_name)
        return render_default_error(result, status=status, tool_name=tool_name)

    success_renderer = SUCCESS_RENDERERS.get(tool_name)
    if success_renderer is not None:
        return success_renderer(result)
    return render_default_success(result, status=status, tool_name=tool_name)
