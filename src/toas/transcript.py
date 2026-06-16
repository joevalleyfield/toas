import re

_TRANSCRIPT_ROLE_MARKER_RE = re.compile(r"^## TOAS:(SYSTEM|USER|ASSISTANT|CONTROL)$")
_MARKER_PREFIX = "## TOAS:"
_ESCAPED_ROLE_MARKER_RE = re.compile(r"(?m)^\\## TOAS:(SYSTEM|USER|ASSISTANT|CONTROL)$")
_ROLE_MARKER_LINE_RE = re.compile(r"(?m)^## TOAS:(SYSTEM|USER|ASSISTANT|CONTROL)$")
_THINKING_START_MARKER = "## TOAS:THINKING"
_THINKING_END_MARKER = "## /TOAS:THINKING"


def escape_transcript_content(content: str) -> str:
    return _ROLE_MARKER_LINE_RE.sub(r"\\## TOAS:\1", content)


def unescape_transcript_content(content: str) -> str:
    return _ESCAPED_ROLE_MARKER_RE.sub(r"## TOAS:\1", content)


def render_transcript_marker(role: str) -> str:
    upper_role = role.upper()
    if upper_role not in {"SYSTEM", "USER", "ASSISTANT", "CONTROL"}:
        raise ValueError(f"invalid transcript role: {role}")
    return f"## TOAS:{upper_role}"


def render_transcript(messages: list[dict], *, spaced: bool = False) -> str:
    blocks = []
    for message in messages:
        separator = "\n\n" if spaced else "\n"
        blocks.append(
            f"{render_transcript_marker(message['role'])}{separator}"
            f"{escape_transcript_content(message['content'])}\n"
        )
    return "\n".join(blocks)


def parse_transcript(text: str) -> list[dict]:
    messages: list[dict[str, str]] = []
    current_role = None
    current_lines: list[str] = []
    seen_system = False
    in_projection_thinking = False

    def flush() -> None:
        nonlocal current_role, current_lines
        if not current_role:
            current_lines = []
            return

        messages.append(
            {
                "role": current_role,
                "content": unescape_transcript_content("\n".join(current_lines).strip()),
            }
        )
        current_lines = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        if in_projection_thinking:
            if line == _THINKING_END_MARKER:
                in_projection_thinking = False
            continue
        if line == _THINKING_START_MARKER:
            in_projection_thinking = True
            continue
        marker_match = _TRANSCRIPT_ROLE_MARKER_RE.fullmatch(line)
        if marker_match is not None:
            flush()
            role = marker_match.group(1).lower()
            if role == "system":
                if seen_system or messages:
                    raise ValueError("SYSTEM block must appear only once at the top of transcript")
                seen_system = True
            current_role = role
            continue
        if line.startswith(_MARKER_PREFIX):
            raise ValueError(
                f"invalid transcript marker at line {line_number}: {line!r}"
            )

        if current_role is not None:
            current_lines.append(line)

    flush()
    return messages


def _eq(a, b):
    return (
        a["role"] == b["role"]
        and a["content"].strip() == b["content"].strip()
    )


def _lcp(a, b):
    i = 0
    for x, y in zip(a, b, strict=False):
        if _eq(x, y):
            i += 1
        else:
            break
    return i


def _normalize_bind_index(bind_index: int | None, log: list[dict]) -> int:
    if bind_index is None:
        return 0
    if bind_index < 0 or bind_index > len(log):
        raise ValueError(f"bind index out of range: {bind_index}")
    return bind_index


def _normalize_anchor_index(anchor_index: int | None, nodes: list[dict], log: list[dict]) -> int:
    if anchor_index is None:
        return 0
    if anchor_index < 0 or anchor_index > len(nodes) or anchor_index > len(log):
        raise ValueError(f"anchor index out of range: {anchor_index}")
    return anchor_index

