from ..transcript import escape_transcript_content, render_transcript_marker


def detect_newline_style(text: str) -> str:
    if "\r\n" in text and "\n" not in text.replace("\r\n", ""):
        return "\r\n"
    return "\n"


def apply_newline_style(text: str, newline: str) -> str:
    normalized = text.replace("\r\n", "\n")
    if newline == "\r\n":
        return normalized.replace("\n", "\r\n")
    return normalized


def render_transcript_blocks(nodes: list[dict]) -> str:
    lines: list[str] = []
    for node in nodes:
        if node["role"] == "result":
            lines.append("## RESULT")
            lines.append("")
            if node.get("transcript_render") == "raw":
                lines.append(node["content"])
            else:
                lines.append(escape_transcript_content(node["content"]))
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
