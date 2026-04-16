from collections.abc import Callable


def render_shell_result(result: dict, *, status: str, tool_name: str) -> str:
    lines = [f"[{status}] {tool_name}: {result['summary']}"]
    if result.get("stdout"):
        lines.append("stdout:")
        lines.append(result["stdout"])
    if result.get("stderr"):
        lines.append("stderr:")
        lines.append(result["stderr"])
    return "\n".join(lines)


def render_read_file_success(result: dict, *, status: str, tool_name: str) -> str:
    return f"[{status}] {tool_name}: {result['path']}\n{result['content']}"


def render_search_success(result: dict, *, status: str, tool_name: str) -> str:
    content = result.get("content", "")
    if content:
        return f"[{status}] {tool_name}: {result['summary']}\n{content}"
    return f"[{status}] {tool_name}: {result['summary']}"


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
        return f"{base}\npreview:\n{preview}"

    content = result.get("content")
    if isinstance(content, str) and content.strip():
        lines = content.splitlines()
        if len(lines) > 20:
            head = "\n".join(lines[:8])
            tail = "\n".join(lines[-8:])
            return f"{base}\npreview:\n{head}\n...\n{tail}"
        return f"{base}\npreview:\n{content.strip()}"
    return base


def render_default_success(result: dict, *, status: str, tool_name: str) -> str:
    summary = result.get("summary") or ""
    content = result.get("content")
    if isinstance(content, str):
        content = content.strip()
    if isinstance(content, str) and content and content != summary:
        detail = f"{summary}\n{content}" if summary else content
    else:
        detail = summary or content or ""
    intention = result.get("intention")
    if isinstance(intention, str) and intention.strip():
        return f"[{status}] {tool_name} ({intention.strip()}): {detail}"
    return f"[{status}] {tool_name}: {detail}"


def render_default_error(result: dict, *, status: str, tool_name: str) -> str:
    detail = result.get("error") or result.get("summary") or result.get("content") or ""
    intention = result.get("intention")
    if isinstance(intention, str) and intention.strip():
        return f"[{status}] {tool_name} ({intention.strip()}): {detail}"
    return f"[{status}] {tool_name}: {detail}"


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
        + "\n".join(
            f"{item['kind']}.{item['name']} ({item['start_line']}-{item['end_line']}) {item.get('path', '')}"
            for item in result.get("structure", [])
        )
    ).rstrip(),
    "replace_range": lambda result: f"[OK] replace_range: {result.get('summary', '')}",
    "replace_block": lambda result: render_replace_block_success(
        result,
        status="OK",
        tool_name=result["tool_name"],
    ),
}


def shape_result_content(result: dict) -> str:
    tool_name = result["tool_name"]
    direct_renderer = RESULT_RENDERERS.get(tool_name)
    if direct_renderer is not None:
        return direct_renderer(result)

    status = "OK" if result["ok"] else "ERROR"
    if not result["ok"]:
        return render_default_error(result, status=status, tool_name=tool_name)

    success_renderer = SUCCESS_RENDERERS.get(tool_name)
    if success_renderer is not None:
        return success_renderer(result)
    return render_default_success(result, status=status, tool_name=tool_name)
