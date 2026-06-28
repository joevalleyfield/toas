import re

from ..transcript import escape_transcript_content, render_transcript_marker

_CODE_FENCE_START_RE = re.compile(r"^\s*```")
_PATH_LIKE_RE = re.compile(r"^\s*/[^/\s]+/")
_SLASH_COMMAND_NAMES = {
    "help",
    "config",
    "compact",
    "extract",
    "replay",
    "head",
    "heads",
    "jump",
    "transcript",
    "llm-input",
    "history",
    "prompt",
    "prompts",
    "intent",
    "cd",
    "pwd",
    "ls",
    "shell",
}


def _is_already_inert_wrapped(content: str) -> bool:
    stripped = content.strip()
    if not stripped:
        return False
    if stripped.startswith("[[inert]]") and stripped.endswith("[[/inert]]"):
        return True
    if stripped.startswith("```inert") and stripped.endswith("```"):
        return True
    if stripped.startswith("```text (inert response)") and stripped.endswith("```"):
        return True
    return False


def _has_risky_projectable_line(content: str) -> bool:
    in_fence = False
    for line in content.splitlines():
        if _CODE_FENCE_START_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        stripped = line.lstrip()
        if not stripped:
            continue
        if stripped.startswith("$ "):
            return True
        if _PATH_LIKE_RE.match(line):
            return True
        if stripped.startswith("/"):
            name = stripped[1:].split(None, 1)[0]
            if name in _SLASH_COMMAND_NAMES:
                return True
    return False


def _inert_wrap_result_content(content: str) -> str:
    if not content.strip():
        return content
    if _is_already_inert_wrapped(content):
        return content
    if not _has_risky_projectable_line(content):
        return content
    return f"```inert\n{content}\n```"


def maybe_inert_wrap_result_content(content: str, *, transcript_inert: bool = True) -> str:
    if not transcript_inert:
        return content
    return _inert_wrap_result_content(content)


def detect_newline_style(text: str) -> str:
    if "\r\n" in text and "\n" not in text.replace("\r\n", ""):
        return "\r\n"
    return "\n"


def apply_newline_style(text: str, newline: str) -> str:
    normalized = text.replace("\r\n", "\n")
    if newline == "\r\n":
        return normalized.replace("\n", "\r\n")
    return normalized


from .result_nodes import validate_result_node


def render_transcript_blocks(nodes: list[dict]) -> str:
    # This renderer is intentionally richer than history-backed transcript
    # reprojection: fresh step-time projection may include result lanes and
    # inert-wrapped transient material, while transcript reprojection only
    # rebuilds durable message lanes.
    lines: list[str] = []
    for node in nodes:
        if node["role"] == "result":
            validate_result_node(node)
            projection_lane = str(node["projection_lane"])
            lines.append(render_transcript_marker(projection_lane))
            lines.append("")
            lines.append("## RESULT")
            lines.append("")
            transcript_inert = node.get("transcript_inert", True)
            if node.get("transcript_render") == "raw":
                lines.append(maybe_inert_wrap_result_content(node["content"], transcript_inert=transcript_inert))
            else:
                lines.append(escape_transcript_content(maybe_inert_wrap_result_content(node["content"], transcript_inert=transcript_inert)))
        else:
            lines.append(render_transcript_marker(node["role"]))
            lines.append("")
            lines.append(escape_transcript_content(node["content"]))
        lines.append("")
    return "\n".join(lines) + ("\n" if lines else "")


def format_content_preview(content: str, *, full: bool, width: int = 80) -> str:
    if full:
        return content
    lines = content.splitlines()
    first = lines[0].strip() if lines else ""
    return first[:width] + "..." if len(first) > width else first
