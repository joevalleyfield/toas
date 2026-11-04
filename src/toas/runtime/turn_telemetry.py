"""Turn telemetry and status decoration formatting for transcript projections."""
from __future__ import annotations

import re
from datetime import datetime, timezone

_TELEMETRY_COMMENT_RE = re.compile(r"^<!--\s*toas:\s*(.*?)\s*-->$")


def humanize_duration(ms: int | float | None) -> str | None:
    """Format duration in milliseconds to a compact readable string."""
    if ms is None or ms < 0:
        return None
    if ms < 1000:
        return f"{int(ms)}ms"
    return f"{ms / 1000:.1f}s"


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


def format_turn_telemetry(
    *,
    target: str | None = None,
    duration_ms: int | float | None = None,
    status: str | None = None,
    timestamp: datetime | str | None = None,
    style: str = "inline",
) -> str | None:
    """Format turn telemetry into an inline decorator or comment block.

    Supported styles:
      - 'inline': returns bracketed key-values, e.g. '[target=... t=... duration=...]'
      - 'comment': returns HTML comment line, e.g. '<!-- toas: target=... timestamp=... duration=... -->'
      - 'off': returns None
    """
    if style not in {"inline", "comment"}:
        return None

    pairs: list[tuple[str, str]] = []
    if target:
        clean_target = str(target).strip()
        if clean_target:
            pairs.append(("target", clean_target))

    formatted_ts = format_timestamp(timestamp, compact=(style == "inline"))
    if formatted_ts:
        ts_key = "t" if style == "inline" else "timestamp"
        pairs.append((ts_key, formatted_ts))

    formatted_dur = humanize_duration(duration_ms)
    if formatted_dur:
        pairs.append(("duration", formatted_dur))

    if status:
        clean_status = str(status).strip()
        if clean_status:
            pairs.append(("status", clean_status))

    if not pairs:
        return None

    body = " ".join(f"{k}={v}" for k, v in pairs)
    if style == "inline":
        return f"[{body}]"
    return f"<!-- toas: {body} -->"


def parse_telemetry_comment(line: str) -> dict[str, str] | None:
    """Parse a sub-heading comment line into key-value pairs if it matches."""
    match = _TELEMETRY_COMMENT_RE.match(line.strip())
    if not match:
        return None
    raw_pairs = match.group(1).split()
    result: dict[str, str] = {}
    for token in raw_pairs:
        if "=" in token:
            k, v = token.split("=", 1)
            result[k] = v
    return result


def extract_subheading_telemetry(lines: list[str]) -> tuple[str | None, list[str]]:
    """Extract a leading telemetry comment from turn content lines if present."""
    if not lines:
        return None, lines
    first = lines[0].strip()
    if _TELEMETRY_COMMENT_RE.match(first):
        return lines[0], lines[1:]
    return None, lines


def decorate_result_node(
    node: dict,
    *,
    style: str = "inline",
    duration_ms: int | float | None = None,
    timestamp: datetime | str | None = None,
) -> dict:
    """Decorate a result node with telemetry markers or comment lines."""
    if style not in {"inline", "comment"}:
        return node
    raw_payload = node.get("payload")
    payload: dict = raw_payload if isinstance(raw_payload, dict) else {}
    status = "OK" if payload.get("ok", True) is not False else "ERROR"
    tool_name = payload.get("tool_name")
    dur = duration_ms if duration_ms is not None else payload.get("duration_ms")
    telemetry = format_turn_telemetry(
        target=tool_name,
        duration_ms=dur,
        status=status,
        timestamp=timestamp,
        style=style,
    )
    if telemetry:
        if style == "inline":
            node["result_marker"] = f"## RESULT {telemetry}"
        elif style == "comment":
            node["telemetry_comment"] = telemetry
    return node

