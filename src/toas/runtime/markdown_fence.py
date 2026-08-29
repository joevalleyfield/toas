"""Structural Markdown backtick-fence scanning without potency decisions."""
from __future__ import annotations

import re
from dataclasses import dataclass

_OPENING_RE = re.compile(r"^(?P<indent> {0,3})(?P<ticks>`{3,})(?P<info>[^\r\n]*)$")
_CLOSING_RE = re.compile(r"^(?P<indent> {0,3})(?P<ticks>`{3,})[ \t]*$")


@dataclass(frozen=True)
class MarkdownFence:
    """One structurally closed backtick fence and its source locations."""

    info_string: str
    info_tokens: tuple[str, ...]
    body: str
    opening_offset: int
    closing_offset: int
    opening_line: int
    closing_line: int
    fence_length: int


def scan_markdown_fences(content: str) -> list[MarkdownFence]:
    """Return closed fences; ignore unterminated openings conservatively."""
    lines = content.splitlines(keepends=True)
    fences: list[MarkdownFence] = []
    offset = 0
    index = 0
    while index < len(lines):
        raw_line = lines[index].rstrip("\r\n")
        opening = _OPENING_RE.match(raw_line)
        if opening is None:
            offset += len(lines[index])
            index += 1
            continue

        fence_length = len(opening.group("ticks"))
        body_start = offset + len(lines[index])
        body_end = None
        closing_offset = None
        closing_line = None
        cursor = body_start
        for closing_index in range(index + 1, len(lines)):
            closing_line_text = lines[closing_index].rstrip("\r\n")
            closing = _CLOSING_RE.match(closing_line_text)
            if closing is not None and len(closing.group("ticks")) >= fence_length:
                body_end = cursor
                closing_offset = cursor
                closing_line = closing_index + 1
                break
            cursor += len(lines[closing_index])

        if body_end is not None and closing_offset is not None and closing_line is not None:
            body = content[body_start:body_end]
            info_string = opening.group("info").strip()
            fences.append(
                MarkdownFence(
                    info_string=info_string,
                    info_tokens=tuple(info_string.split()),
                    body=body,
                    opening_offset=offset,
                    closing_offset=closing_offset,
                    opening_line=index + 1,
                    closing_line=closing_line,
                    fence_length=fence_length,
                )
            )
            offset = cursor + len(lines[closing_line - 1])
            index = closing_line
            continue

        offset += len(lines[index])
        index += 1

    return fences
