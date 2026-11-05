"""Turn telemetry, ID allocation, and status decoration formatting for transcript projections."""
from __future__ import annotations

import re
from datetime import datetime, timezone

_TELEMETRY_COMMENT_RE = re.compile(r"^<!--\s*toas:\s*(.*?)\s*-->$")
_TIMESTAMP_TOKEN_RE = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?$")
_DURATION_TOKEN_RE = re.compile(r"^(?:\d+h(?:[0-9]+m)?|\d+m(?:[0-9]+s)?|\d+(?:\.\d+)?s|\d+ms)$")
_STATUS_TOKENS = {"OK", "ERROR", "FAIL", "CANCELLED"}
_PROSE_REFERENCE_RE = re.compile(r"(?<!\\)\[\[([a-zA-Z0-9_-]+)(?:\|[^\]]+)?\]\]")

PHONETIC_ALPHABET = (
    "alpha",
    "bravo",
    "charlie",
    "delta",
    "echo",
    "foxtrot",
    "golf",
    "hotel",
    "india",
    "juliet",
    "kilo",
    "lima",
    "mike",
    "november",
    "oscar",
    "papa",
    "quebec",
    "romeo",
    "sierra",
    "tango",
    "uniform",
    "victor",
    "whiskey",
    "xray",
    "yankee",
    "zulu",
)


def allocate_turn_handle(index: int) -> str:
    """Allocate a deterministic NATO phonetic turn handle for a 0-based turn index."""
    if index < 0:
        index = 0
    count = len(PHONETIC_ALPHABET)
    base = PHONETIC_ALPHABET[index % count]
    iteration = (index // count) + 1
    if iteration > 1:
        return f"{base}-{iteration}"
    return base


def humanize_duration(ms: int | float | None) -> str | None:
    """Format duration in milliseconds to a compact readable string."""
    if ms is None or ms < 0:
        return None
    if ms < 1000:
        return f"{int(ms)}ms"
    if ms < 60000:
        return f"{ms / 1000:.1f}s"
    total_seconds = int(ms // 1000)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    if minutes < 60:
        return f"{minutes}m{seconds}s" if seconds else f"{minutes}m"
    hours = minutes // 60
    rem_minutes = minutes % 60
    return f"{hours}h{rem_minutes}m" if rem_minutes else f"{hours}h"


def format_timestamp(ts: datetime | str | None, *, compact: bool = True) -> str | None:
    """Format a timestamp into a display string."""
    if ts is None:
        return None
    if isinstance(ts, str):
        if not ts.strip():
            return None
        try:
            parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return parsed.strftime("%H:%M:%S") if compact else parsed.isoformat()
        except ValueError:
            return ts.strip()
    if isinstance(ts, datetime):
        utc_ts = ts.astimezone(timezone.utc) if ts.tzinfo else ts
        return utc_ts.strftime("%H:%M:%S") if compact else utc_ts.isoformat()
    return None


def parse_turn_stamp(raw: str) -> dict[str, str]:
    """Parse turn telemetry and ID from an inline bracket '[...]' or comment '<!-- toas: ... -->'.

    Supports both compact keyless tokens and explicit key=value pairs, whether passed
    as bare bracket contents, a full bracketed string, or a full marker line.
    """
    text = raw.strip()
    comment_match = _TELEMETRY_COMMENT_RE.search(text)
    if comment_match:
        text = comment_match.group(1).strip()
    else:
        first_bracket = text.find("[")
        last_bracket = text.rfind("]")
        if first_bracket != -1 and last_bracket > first_bracket:
            text = text[first_bracket + 1 : last_bracket].strip()

    tokens = text.split()
    result: dict[str, str] = {}
    remaining_tokens: list[str] = []

    for i, token in enumerate(tokens):
        # 1. Bold or sigil turn-id (e.g. **bravo**, @bravo, [[bravo]])
        if token.startswith("**") and token.endswith("**") and len(token) > 4:
            result["id"] = token[2:-2]
            continue
        if token.startswith("@") and len(token) > 1:
            result["id"] = token[1:]
            continue
        if token.startswith("[[") and token.endswith("]]") and len(token) > 4:
            result["id"] = token[2:-2]
            continue

        # 2. Key=Value pairs
        if "=" in token:
            k, v = token.split("=", 1)
            k = k.lower()
            if k in {"id", "turn", "handle"}:
                result["id"] = v
            elif k in {"t", "timestamp"}:
                result["timestamp"] = v
            elif k in {"duration", "dur"}:
                result["duration"] = v
            elif k == "status":
                result["status"] = v
            elif k in {"target", "model", "tool"}:
                result["target"] = v
            else:
                result[k] = v
            continue

        # 3. Known closed-set tokens
        upper = token.upper()
        if upper in _STATUS_TOKENS:
            result["status"] = upper
            continue
        if _TIMESTAMP_TOKEN_RE.match(token):
            result["timestamp"] = token
            continue
        if _DURATION_TOKEN_RE.match(token):
            result["duration"] = token
            continue

        # 4. Leading position ID (if not yet set)
        if i == 0 and "id" not in result:
            result["id"] = token
            continue

        remaining_tokens.append(token)

    # 5. Remaining tokens: target if not set
    if remaining_tokens and "target" not in result:
        result["target"] = remaining_tokens[0]
        if len(remaining_tokens) > 1:
            result["extra"] = " ".join(remaining_tokens[1:])

    return result


def parse_telemetry_comment(line: str) -> dict[str, str] | None:
    """Parse a sub-heading comment line into key-value pairs if it matches."""
    if not _TELEMETRY_COMMENT_RE.match(line.strip()):
        return None
    return parse_turn_stamp(line)


def format_turn_telemetry(
    *,
    turn_id: str | None = None,
    target: str | None = None,
    duration_ms: int | float | None = None,
    status: str | None = None,
    timestamp: datetime | str | None = None,
    style: str = "compact",
) -> str | None:
    """Format turn telemetry into an inline decorator or comment block.

    Supported styles:
      - 'compact': returns keyless bracketed stamp, e.g. '[bravo claude-3-7-sonnet 11:42:00 1.2s]'
      - 'inline': returns key-value bracketed stamp, e.g. '[id=bravo target=... t=... duration=...]'
      - 'comment': returns HTML comment line, e.g. '<!-- toas: id=bravo target=... timestamp=... duration=... -->'
      - 'off': returns None
    """
    if style not in {"compact", "inline", "comment"}:
        return None

    clean_id = str(turn_id).strip() if turn_id else None
    clean_target = str(target).strip() if target else None
    formatted_ts = format_timestamp(timestamp, compact=(style in {"compact", "inline"}))
    formatted_dur = humanize_duration(duration_ms)
    clean_status = str(status).strip() if status else None

    if style == "compact":
        tokens: list[str] = []
        if clean_id:
            tokens.append(clean_id)
        if clean_status:
            tokens.append(clean_status)
        if clean_target:
            tokens.append(clean_target)
        if formatted_ts:
            tokens.append(formatted_ts)
        if formatted_dur:
            tokens.append(formatted_dur)
        if not tokens:
            return None
        return f"[{' '.join(tokens)}]"

    # inline or comment
    pairs: list[tuple[str, str]] = []
    if clean_id:
        pairs.append(("id", clean_id))
    if clean_target:
        pairs.append(("target", clean_target))
    if formatted_ts:
        ts_key = "t" if style == "inline" else "timestamp"
        pairs.append((ts_key, formatted_ts))
    if formatted_dur:
        pairs.append(("duration", formatted_dur))
    if clean_status:
        pairs.append(("status", clean_status))

    if not pairs:
        return None

    body = " ".join(f"{k}={v}" for k, v in pairs)
    if style == "inline":
        return f"[{body}]"
    return f"<!-- toas: {body} -->"


def extract_subheading_telemetry(lines: list[str]) -> tuple[str | None, list[str]]:
    """Extract a leading telemetry comment from turn content lines if present."""
    if not lines:
        return None, lines
    first = lines[0].strip()
    if _TELEMETRY_COMMENT_RE.match(first):
        return lines[0], lines[1:]
    return None, lines


def extract_in_prose_references(text: str) -> list[str]:
    """Extract all unescaped [[handle]] turn references from text."""
    if not text:
        return []
    return _PROSE_REFERENCE_RE.findall(text)


def resolve_turn_selector(
    items: list[dict],
    selector: str,
) -> dict | None:
    """Resolve a turn or event from a list of messages or events by ID or handle.

    Checks visible 'turn_id', 'handle', or event 'id' (including prefix match).
    """
    clean = selector.strip()
    if not clean:
        return None
    # 1. Exact match on turn_id or handle
    for item in items:
        if item.get("turn_id") == clean or item.get("handle") == clean:
            return item
    # 2. Exact match on event id
    for item in items:
        if item.get("id") == clean:
            return item
    # 3. Prefix match on event id
    for item in items:
        item_id = item.get("id")
        if item_id and item_id.startswith(clean):
            return item
    return None


def resolve_node_handle(node: dict | None, default_index: int = 0) -> str:
    """Resolve turn handle from node turn_id, handle, marker, comment, or default index."""
    if not isinstance(node, dict):
        return allocate_turn_handle(default_index)
    if node.get("turn_id"):
        return str(node["turn_id"]).strip()
    if node.get("handle"):
        return str(node["handle"]).strip()
    marker = node.get("marker")
    if isinstance(marker, str):
        parsed = parse_turn_stamp(marker)
        if "id" in parsed:
            return parsed["id"]
    comment = node.get("telemetry_comment")
    if isinstance(comment, str):
        parsed = parse_turn_stamp(comment)
        if "id" in parsed:
            return parsed["id"]
    return allocate_turn_handle(default_index)


def format_result_hierarchical_id(
    parent_handle: str,
    *,
    plan_index: int = 1,
    op_index: int = 1,
) -> str:
    """Format hierarchical provenance ID: parent_handle.p#.o#."""
    clean_parent = parent_handle.strip() if parent_handle else "alpha"
    p = max(1, plan_index)
    o = max(1, op_index)
    return f"{clean_parent}.p{p}.o{o}"


def compute_human_dwell_ms(
    prior_events: list[dict],
    current_time: datetime | float | None = None,
) -> int | None:
    """Calculate heuristic human dwell time in ms since previous turn completion.

    Returns None if there are no prior events or no prior timestamp.
    """
    if not prior_events:
        return None
    last_ts: float | None = None
    for event in reversed(prior_events):
        if not isinstance(event, dict):
            continue
        raw_ts = event.get("timestamp")
        if raw_ts is None:
            continue
        if isinstance(raw_ts, (int, float)):
            last_ts = float(raw_ts)
            break
        if isinstance(raw_ts, str):
            try:
                last_ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00")).timestamp()
                break
            except ValueError:
                continue
    if last_ts is None:
        return None

    now_ts: float
    if current_time is None:
        now_ts = datetime.now(timezone.utc).timestamp()
    elif isinstance(current_time, (int, float)):
        now_ts = float(current_time)
    elif isinstance(current_time, datetime):
        now_ts = current_time.timestamp()
    else:
        now_ts = datetime.now(timezone.utc).timestamp()

    delta_s = max(0.0, now_ts - last_ts)
    return int(delta_s * 1000)


def is_human_user_turn(node: dict) -> bool:
    """Check if a node represents a human-authored user turn with substantive content.

    Returns False if the turn is purely a structural container enclosing tool results.
    """
    if not isinstance(node, dict) or node.get("role") != "user":
        return False
    content = str(node.get("content", ""))
    blocks = re.split(r"(?m)^## RESULT(?:[ \t]+[^\r\n]*)?$", content)
    prose = blocks[0].strip()
    return bool(prose)


def decorate_user_turn_node(
    node: dict,
    *,
    style: str = "compact",
    turn_id: str | None = None,
    duration_ms: int | float | None = None,
    timestamp: datetime | str | None = None,
) -> dict:
    """Decorate a human user turn with turn handle, timestamp, and dwell duration."""
    if style not in {"compact", "inline", "comment"} or not is_human_user_turn(node):
        return node
    if not turn_id and node.get("marker"):
        parsed = parse_turn_stamp(node["marker"])
        if "id" in parsed:
            turn_id = parsed["id"]
    tid = turn_id or node.get("turn_id")
    telemetry = format_turn_telemetry(
        turn_id=tid,
        duration_ms=duration_ms,
        timestamp=timestamp or datetime.now(timezone.utc),
        style=style,
    )
    if telemetry:
        if tid:
            node["turn_id"] = tid
        if style in {"compact", "inline"}:
            node["marker"] = f"## TOAS:USER {telemetry}"
        elif style == "comment":
            node["telemetry_comment"] = telemetry
        meta = node.setdefault("metadata", {})
        if node.get("marker"):
            meta["marker"] = node["marker"]
        if node.get("telemetry_comment"):
            meta["telemetry_comment"] = node["telemetry_comment"]
        if duration_ms is not None:
            meta["duration_ms"] = duration_ms
            node["duration_ms"] = duration_ms
    return node


def decorate_result_node(
    node: dict,
    *,
    style: str = "compact",
    turn_id: str | None = None,
    duration_ms: int | float | None = None,
    timestamp: datetime | str | None = None,
) -> dict:
    """Decorate a result node with telemetry markers or comment lines."""
    if style not in {"compact", "inline", "comment"}:
        return node
    raw_payload = node.get("payload")
    payload: dict = raw_payload if isinstance(raw_payload, dict) else {}
    is_error = (
        payload.get("ok") is False
        or bool(payload.get("error"))
        or str(node.get("content", "")).startswith("[ERROR]")
    )
    status = "ERROR" if is_error else "OK"
    tool_name = payload.get("tool_name") or node.get("origin_kind")
    if tool_name == "user_shell":
        tool_name = "shell"
    dur = duration_ms if duration_ms is not None else payload.get("duration_ms")
    tid = turn_id or node.get("turn_id")
    telemetry = format_turn_telemetry(
        turn_id=tid,
        target=tool_name,
        duration_ms=dur,
        status=status,
        timestamp=timestamp,
        style=style,
    )
    if telemetry:
        if tid:
            node["turn_id"] = tid
        if style in {"compact", "inline"}:
            node["result_marker"] = f"## RESULT {telemetry}"
        elif style == "comment":
            node["telemetry_comment"] = telemetry
    return node
