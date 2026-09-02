"""Structural Markdown backtick-fence scanning without potency decisions."""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

_OPENING_RE = re.compile(r"^(?P<indent> {0,3})(?P<ticks>`{3,})(?P<info>[^\r\n]*)$")
_CLOSING_RE = re.compile(r"^(?P<indent> {0,3})(?P<ticks>`{3,})[ \t]*$")
_INFO_TOKEN_RE = re.compile(r'''(?:(?:"(?:\\.|[^"\\])*")|(?:'(?:\\.|[^'\\])*')|[^\s"'])+''')


@dataclass(frozen=True)
class FenceAttribute:
    """One parsed ``name=value`` fence-header attribute with raw source spans."""

    name: str
    value: str
    value_start: int
    value_end: int
    quote: str | None


@dataclass(frozen=True)
class MarkdownFence:
    """One structurally closed backtick fence and its source locations."""

    info_string: str
    info_tokens: tuple[str, ...]
    body: str
    opening_offset: int
    info_offset: int
    opening_line_end: int
    closing_offset: int
    closing_line_end: int
    opening_line: int
    closing_line: int
    fence_length: int


def fence_attributes(fence: MarkdownFence) -> tuple[FenceAttribute, ...] | None:
    """Parse executable-header attributes while retaining value source spans.

    ``None`` means the information string is not safely tokenizable; callers
    should not attempt a lossy header rewrite in that case.
    """
    opening = fence.info_string
    try:
        tokens = list(_INFO_TOKEN_RE.finditer(opening))
        if tuple(shlex.split(opening)) != fence.info_tokens:  # pragma: no cover - scanner establishes this equivalence
            return None
    except ValueError:  # pragma: no cover - malformed headers have no active fence lane
        return None
    attributes: list[FenceAttribute] = []
    for token in tokens[2:]:
        raw = token.group(0)
        if "=" not in raw:  # pragma: no cover - active headers require attributes
            return None
        name, raw_value = raw.split("=", 1)
        if not name:  # pragma: no cover - active headers require names
            return None
        value_start = fence.info_offset + token.start() + len(name) + 1
        value_end = value_start + len(raw_value)
        quote = raw_value[0] if raw_value[:1] in {"'", '"'} else None
        if quote is not None:
            if len(raw_value) < 2 or raw_value[-1] != quote:  # pragma: no cover - shlex rejects it first
                return None
            value_start += 1
            value_end -= 1
        try:
            value = shlex.split(raw_value)[0]
        except (IndexError, ValueError):  # pragma: no cover - shlex validates active values above
            return None
        attributes.append(FenceAttribute(name=name, value=value, value_start=value_start, value_end=value_end, quote=quote))
    return tuple(attributes)


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
            raw_info = opening.group("info")
            leading_info = len(raw_info) - len(raw_info.lstrip())
            info_string = raw_info.strip()
            try:
                info_tokens = tuple(shlex.split(info_string))
            except ValueError:
                info_tokens = ()
            fences.append(
                MarkdownFence(
                    info_string=info_string,
                    info_tokens=info_tokens,
                    body=body,
                    opening_offset=offset,
                    info_offset=offset + opening.start("info") + leading_info,
                    opening_line_end=offset + len(raw_line),
                    closing_offset=closing_offset,
                    closing_line_end=cursor + len(lines[closing_line - 1]),
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
