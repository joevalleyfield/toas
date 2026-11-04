import re

_TRANSCRIPT_ROLE_MARKER_RE = re.compile(
    r"^## TOAS:(SYSTEM|USER|ASSISTANT|CONTROL|STATE|STATE-DIFF)(?:/([^ \t]+))?(?:[ \t]+(.*))?$"
)
_MARKER_PREFIX = "## TOAS:"
_ROLE_MARKER_LINE_RE = re.compile(
    r"(?m)^## TOAS:(SYSTEM|USER|ASSISTANT|CONTROL|STATE|STATE-DIFF)(?:/[^ \t\r\n]+)?(?:[ \t]+[^\r\n]*)?$"
)
_ESCAPED_ROLE_MARKER_RE = re.compile(
    r"(?m)^\\(## TOAS:(?:SYSTEM|USER|ASSISTANT|CONTROL|STATE|STATE-DIFF)(?:/[^ \t\r\n]+)?(?:[ \t]+[^\r\n]*)?)$"
)
_THINKING_START_MARKER = "## TOAS:THINKING"
_THINKING_END_MARKER = "## /TOAS:THINKING"


def escape_transcript_content(content: str) -> str:
    return _ROLE_MARKER_LINE_RE.sub(r"\\\g<0>", content)


def unescape_transcript_content(content: str) -> str:
    return _ESCAPED_ROLE_MARKER_RE.sub(r"\1", content)


def render_transcript_marker(role: str) -> str:
    upper_role = role.upper()
    if upper_role in {"SYSTEM", "USER", "ASSISTANT", "CONTROL"}:
        return f"## TOAS:{upper_role}"
    if upper_role in {"STATE", "STATE/1"}:
        return "## TOAS:STATE/1"
    if upper_role in {"STATE-DIFF", "STATE-DIFF/1"}:
        return "## TOAS:STATE-DIFF/1"
    if re.match(r"^(STATE|STATE-DIFF)/\d+$", upper_role):
        return f"## TOAS:{upper_role}"
    raise ValueError(f"invalid transcript role: {role}")


def render_transcript(messages: list[dict], *, spaced: bool = False) -> str:
    blocks = []
    for message in messages:
        separator = "\n\n" if spaced else "\n"
        marker = message.get("marker") or render_transcript_marker(message["role"])
        telemetry = message.get("telemetry_comment")
        body = escape_transcript_content(message["content"])
        if telemetry:
            prefix = f"{marker}\n{telemetry}"
            blocks.append(f"{prefix}{separator}{body}\n")
        else:
            blocks.append(f"{marker}{separator}{body}\n")
    return "\n".join(blocks)


def parse_transcript(text: str) -> list[dict]:
    messages: list[dict[str, str]] = []
    current_role = None
    current_marker = None
    current_lines: list[str] = []
    seen_system = False
    in_projection_thinking = False

    def flush() -> None:
        nonlocal current_role, current_marker, current_lines
        if not current_role:
            current_lines = []
            return

        lines_to_process = list(current_lines)
        telemetry_comment = None
        non_empty_indices = [i for i, l in enumerate(lines_to_process) if l.strip()]
        if non_empty_indices:
            first_idx = non_empty_indices[0]
            first_line = lines_to_process[first_idx].strip()
            if first_line.startswith("<!-- toas:") and first_line.endswith("-->"):
                telemetry_comment = first_line
                lines_to_process.pop(first_idx)

        turn_id = None
        if current_marker:
            match = _TRANSCRIPT_ROLE_MARKER_RE.fullmatch(current_marker)
            if match and match.group(3):
                from .runtime.turn_telemetry import parse_turn_stamp

                parsed = parse_turn_stamp(match.group(3))
                if "id" in parsed:
                    turn_id = parsed["id"]
        if not turn_id and telemetry_comment:
            from .runtime.turn_telemetry import parse_turn_stamp

            parsed = parse_turn_stamp(telemetry_comment)
            if "id" in parsed:
                turn_id = parsed["id"]

        msg: dict[str, str] = {
            "role": current_role,
            "content": unescape_transcript_content("\n".join(lines_to_process).strip()),
        }
        if current_marker:
            msg["marker"] = current_marker
        if telemetry_comment:
            msg["telemetry_comment"] = telemetry_comment
        if turn_id:
            msg["turn_id"] = turn_id
        messages.append(msg)
        current_lines = []
        current_marker = None

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
            canonical = render_transcript_marker(role)
            current_marker = line if line != canonical else None
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

