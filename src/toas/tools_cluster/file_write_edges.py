from __future__ import annotations

from pathlib import Path

from ..runtime.rendering_edges import apply_newline_style, detect_newline_style
from ..runtime.session_file_edges import read_text_preserve_newlines


def resolve_tool_write_newline(*, path: Path, newline_style_policy: str) -> str:
    if newline_style_policy == "crlf":
        return "\r\n"
    if newline_style_policy == "lf":
        return "\n"
    if path.exists() and path.is_file():
        return detect_newline_style(read_text_preserve_newlines(path))
    return "\n"


def write_text_with_tool_newline_policy(*, path: Path, text: str, newline_style_policy: str) -> str:
    newline = resolve_tool_write_newline(path=path, newline_style_policy=newline_style_policy)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(apply_newline_style(text, newline))
    return newline
