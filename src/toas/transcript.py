import re

_TRANSCRIPT_ROLE_MARKER_RE = re.compile(r"^## TOAS:(SYSTEM|USER|ASSISTANT)$")
_MARKER_PREFIX = "## TOAS:"
_ESCAPED_MARKER_PREFIX = r"\## TOAS:"
_THINKING_START_MARKER = "## TOAS:THINKING"
_THINKING_END_MARKER = "## /TOAS:THINKING"


def escape_transcript_content(content: str) -> str:
    return re.sub(rf"(?m)^{re.escape(_MARKER_PREFIX)}", _ESCAPED_MARKER_PREFIX, content)


def unescape_transcript_content(content: str) -> str:
    return re.sub(rf"(?m)^{re.escape(_ESCAPED_MARKER_PREFIX)}", _MARKER_PREFIX, content)


def render_transcript_marker(role: str) -> str:
    upper_role = role.upper()
    if upper_role not in {"SYSTEM", "USER", "ASSISTANT"}:
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
