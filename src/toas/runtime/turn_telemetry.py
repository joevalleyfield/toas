"""Turn telemetry, ID allocation, and status decoration formatting for transcript projections."""
from __future__ import annotations

import re
from datetime import datetime, timezone

_TELEMETRY_COMMENT_RE = re.compile(r"^<!--\s*toas:\s*(.*?)\s*-->$")
_TIMESTAMP_TOKEN_RE = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?$")
_DURATION_TOKEN_RE = re.compile(r"^(?:\d+h(?:[0-9]+m)?|\d+m(?:[0-9]+s)?|\d+(?:\.\d+)?s|\d+ms)$")
_TOKEN_MULTIPLIER_RE = re.compile(r"^\d+(?:\.\d+)?[kKM]$")
_TOKEN_SCALAR_RE = re.compile(r"^\d+tok$", re.IGNORECASE)
_STATUS_TOKENS = {"OK", "ERROR", "FAIL", "CANCELLED"}
_PROSE_REFERENCE_RE = re.compile(r"(?<!\\)\[\[([a-zA-Z0-9_-]+)(?:\|[^\]]+)?\]\]")
_RESULT_HEADER_RE = re.compile(r"^## RESULT(?:[ \t]+[^\r\n]*)?$")
_RESULT_STATUS_RE = re.compile(r"^\[(OK|ERROR|FAIL|CANCELLED)\](?:\s+.*)?$")
_RESULT_SPILLED_RE = re.compile(r"^Output exceeded threshold(?:\s+.*)?$")
_RESULT_SECTION_LABEL_RE = re.compile(r"^(?:stdout|stderr|preview|partial matches):\s*$")
_RESULT_FOOTER_RE = re.compile(r"^\[(?:\d+\s+lines\s+remaining\.|Output\s+truncated|Exit\s+code:).*\]$")
_RESULT_HINT_RE = re.compile(r"^next valid shape:\s*$")
_CODE_FENCE_OPEN_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_CODE_FENCE_CLOSE_RE = re.compile(r"^(?P<fence>`{3,}|~{3,})[ \t]*$")

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


def allocate_turn_handle(
    index: int,
    *,
    namespace: str = "nato",
    role: str | None = None,
) -> str:
    """Allocate a deterministic turn handle for a 0-based turn index.

    Supported namespaces:
      - 'nato' (default): NATO phonetic alphabet ('alpha', 'bravo', ..., 'alpha-2', ...)
      - 'numeric': Compact role-prefixed numbering ('u1', 'u2', ... for user; 'a1', 'a2', ... for assistant; 't1' default)
    """
    if index < 0:
        index = 0
    ns = namespace.lower().strip() if isinstance(namespace, str) else "nato"
    if ns == "numeric":
        prefix = "u" if role == "user" else ("a" if role == "assistant" else "t")
        return f"{prefix}{index + 1}"

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


def humanize_token_count(tokens: int | None) -> str | None:
    """Format token count to a compact readable string.

    Rules:
      - Under 1000: '420 tok' (space plus 'tok' label when scalar)
      - 1000 and above: '1.8k', '12.4k', '120k', '1.2M' (no label needed with multiplier)
    """
    if tokens is None or tokens < 0:
        return None
    if tokens < 1000:
        return f"{tokens} tok"
    if tokens < 1_000_000:
        k_val = tokens / 1000
        formatted = f"{k_val:.1f}k"
        if formatted.endswith(".0k"):
            formatted = f"{int(round(k_val))}k"
        return formatted
    m_val = tokens / 1_000_000
    formatted = f"{m_val:.1f}M"
    if formatted.endswith(".0M"):
        formatted = f"{int(round(m_val))}M"
    return formatted


def calibrate_token_estimator_ratio(
    items: list[dict],
    mode: str = "chars",
    *,
    default_rate: float | None = None,
    max_calls: int = 3,
    min_tokens: int = 50,
) -> float:
    """Derive an empirical character-to-token or word-to-token ratio from recent LLM calls.

    Scans backward through history items to find up to `max_calls` LLM interactions with
    provider usage, accumulating character/word counts and token counts until `min_tokens`
    threshold is met, and computes the ratio clamped to safe bounds.
    """
    clean_mode = mode.lower().strip()
    is_words = clean_mode == "words"
    if is_words:
        fallback = default_rate if (default_rate is not None and default_rate > 0) else 0.75
        min_clamp, max_clamp = 0.3, 1.5
    else:
        fallback = default_rate if (default_rate is not None and default_rate > 0) else 4.0
        min_clamp, max_clamp = 1.5, 6.0

    if not items:
        return fallback

    accumulated_units = 0
    accumulated_tokens = 0
    calls_found = 0

    for idx in range(len(items) - 1, -1, -1):
        item = items[idx]
        if not isinstance(item, dict):
            continue

        usage: dict | None = None
        comp_text: str = ""
        prompt_text: str = ""
        prompt_cutoff = idx

        # 1. Node with attached _llm_call (pre-commit generation node)
        llm_call = item.get("_llm_call")
        if isinstance(llm_call, dict) and isinstance(llm_call.get("usage"), dict):
            usage = llm_call["usage"]
            comp_text = str(item.get("content", "")).strip()
            prompt_cutoff = idx
            req_msgs = llm_call.get("request_messages")
            if isinstance(req_msgs, list):
                prompt_text = " ".join(
                    str(m.get("content", "")) for m in req_msgs if isinstance(m, dict) and m.get("content")
                )

        # 2. Durable llm_call record or event with payload usage
        if usage is None:
            payload = item.get("payload")
            if isinstance(payload, dict) and isinstance(payload.get("usage"), dict):
                usage = payload["usage"]
                resp_payload = payload.get("response")
                if isinstance(resp_payload, dict) and resp_payload.get("content"):
                    comp_text = str(resp_payload["content"]).strip()
                elif payload.get("message_id"):
                    mid = payload["message_id"]
                    for prev_i, prev in enumerate(items):
                        if isinstance(prev, dict) and prev.get("id") == mid:
                            comp_text = str(prev.get("content", "")).strip()
                            prompt_cutoff = prev_i
                            break
                elif idx > 0 and isinstance(items[idx - 1], dict) and items[idx - 1].get("role") == "assistant":
                    comp_text = str(items[idx - 1].get("content", "")).strip()
                    prompt_cutoff = idx - 1

                msgs = payload.get("messages")
                if isinstance(msgs, list):
                    prompt_text = " ".join(
                        str(m.get("content", "")) for m in msgs if isinstance(m, dict) and m.get("content")
                    )

        if usage is None:
            continue

        total_toks = usage.get("total_tokens")
        if not isinstance(total_toks, int) or total_toks <= 0:
            prompt_toks = usage.get("prompt_tokens") or 0
            comp_toks = usage.get("completion_tokens") or 0
            total_toks = prompt_toks + comp_toks
        if total_toks <= 0:
            continue

        # If prompt_text was not in payload/llm_call, gather preceding turn content
        if not prompt_text:
            prompt_parts: list[str] = []
            for prev_idx in range(prompt_cutoff):
                prev_item = items[prev_idx]
                if isinstance(prev_item, dict) and prev_item.get("role") in {"user", "assistant", "system", "result"}:
                    c = prev_item.get("content")
                    if c:
                        prompt_parts.append(str(c))
            prompt_text = " ".join(prompt_parts)

        units = 0
        if prompt_text:
            units += len(prompt_text.split()) if is_words else len(prompt_text)
        if comp_text:
            units += len(comp_text.split()) if is_words else len(comp_text)
        if units <= 0:
            continue

        accumulated_units += units
        accumulated_tokens += total_toks
        calls_found += 1

        if calls_found >= max_calls or accumulated_tokens >= min_tokens:
            break

    if accumulated_tokens > 0 and accumulated_units > 0:
        raw_ratio = accumulated_units / accumulated_tokens
        clamped = max(min_clamp, min(max_clamp, raw_ratio))
        return round(clamped, 2)

    return fallback


def estimate_tokens(
    text: str | None,
    heuristic: str = "adaptive",
    items: list[dict] | None = None,
) -> int:
    """Estimate token count for a text string using a configurable heuristic."""
    if not text:
        return 0
    clean_h = heuristic.strip().lower()
    if clean_h in {"adaptive:words", "auto:words"}:
        rate = calibrate_token_estimator_ratio(items or [], mode="words")
        words = len(text.split())
        return max(1, int(round(words / rate))) if words else 0
    if clean_h in {"adaptive", "adaptive:chars", "auto", "auto:chars"}:
        rate = calibrate_token_estimator_ratio(items or [], mode="chars")
        length = len(text)
        return max(1, int(round(length / rate))) if length else 0
    if clean_h.startswith("words:"):
        rate_str = clean_h[len("words:"):].strip()
        try:
            rate = float(rate_str)
        except ValueError:
            rate = 0.75
        if rate <= 0:
            rate = 0.75
        words = len(text.split())
        return max(1, int(round(words / rate))) if words else 0
    rate = 4.0
    if clean_h.startswith("chars:"):
        rate_str = clean_h[len("chars:"):].strip()
        try:
            rate = float(rate_str)
        except ValueError:
            rate = 4.0
    if rate <= 0:
        rate = 4.0
    length = len(text)
    return max(1, int(round(length / rate))) if length else 0


def compute_cumulative_tokens(
    items: list[dict],
    current_node: dict | None = None,
    *,
    heuristic: str = "adaptive",
    current_usage: dict | None = None,
) -> int:
    """Calculate the cumulative token count up to the current turn.

    Uses a hybrid approach:
    - If current_usage is given and has 'total_tokens', returns that exact anchor.
    - Otherwise, scans backward to find the most recent node/event with provider usage
      to anchor the baseline, and adds estimated tokens for subsequent turns.
    - If no provider usage exists, sums estimated tokens across all turns.
    """
    if isinstance(current_usage, dict):
        total = current_usage.get("total_tokens")
        if isinstance(total, int) and total >= 0:
            return total

    if isinstance(current_node, dict):
        llm_call = current_node.get("_llm_call")
        if isinstance(llm_call, dict):
            usage = llm_call.get("usage")
            if isinstance(usage, dict) and isinstance(usage.get("total_tokens"), int):
                return usage["total_tokens"]
        payload = current_node.get("payload")
        if isinstance(payload, dict):
            usage = payload.get("usage")
            if isinstance(usage, dict) and isinstance(usage.get("total_tokens"), int):
                return usage["total_tokens"]

    all_items = list(items)
    if current_node is not None and (not all_items or all_items[-1] is not current_node):
        all_items.append(current_node)

    anchor_idx = -1
    anchor_tokens = 0
    for idx in range(len(all_items) - 1, -1, -1):
        item = all_items[idx]
        if not isinstance(item, dict):
            continue
        llm_call = item.get("_llm_call")
        if isinstance(llm_call, dict):
            usage = llm_call.get("usage")
            if isinstance(usage, dict) and isinstance(usage.get("total_tokens"), int):
                anchor_idx = idx
                anchor_tokens = usage["total_tokens"]
                break
        payload = item.get("payload")
        if isinstance(payload, dict):
            usage = payload.get("usage")
            if isinstance(usage, dict) and isinstance(usage.get("total_tokens"), int):
                anchor_idx = idx
                anchor_tokens = usage["total_tokens"]
                break
        meta = item.get("metadata")
        if isinstance(meta, dict) and isinstance(meta.get("tokens"), int):
            anchor_idx = idx
            anchor_tokens = meta["tokens"]
            break
        if isinstance(item.get("tokens"), int):
            anchor_idx = idx
            anchor_tokens = item["tokens"]
            break

    if anchor_idx >= 0:
        total = anchor_tokens
        for item in all_items[anchor_idx + 1:]:
            if isinstance(item, dict):
                role = item.get("role")
                kind = item.get("kind")
                if kind or role in {"llm_call", "tool_request", "jump", "head", "anchor", "run"}:
                    continue
                content = str(item.get("content", ""))
                total += estimate_tokens(content, heuristic, items=all_items)
        return total

    total = 0
    for item in all_items:
        if isinstance(item, dict):
            role = item.get("role")
            kind = item.get("kind")
            if kind or role in {"llm_call", "tool_request", "jump", "head", "anchor", "run"}:
                continue
            content = str(item.get("content", ""))
            total += estimate_tokens(content, heuristic, items=all_items)
    return total


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
            elif k in {"tokens", "tok", "token_count"}:
                result["tokens"] = v
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
        if _TOKEN_MULTIPLIER_RE.match(token) or _TOKEN_SCALAR_RE.match(token):
            result["tokens"] = token
            continue
        if token.lower() == "tok":
            if "tokens" in result and result["tokens"].isdigit():
                result["tokens"] = f"{result['tokens']} tok"
                continue
            if remaining_tokens and remaining_tokens[-1].isdigit():
                val = remaining_tokens.pop()
                result["tokens"] = f"{val} tok"
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
    tokens: int | str | None = None,
    style: str = "compact",
) -> str | None:
    """Format turn telemetry into an inline decorator or comment block.

    Supported styles:
      - 'compact': returns keyless bracketed stamp, e.g. '[bravo claude-3-7-sonnet 11:42:00 1.2s 1.8k]'
      - 'inline': returns key-value bracketed stamp, e.g. '[id=bravo target=... t=... duration=... tokens=1.8k]'
      - 'comment': returns HTML comment line, e.g. '<!-- toas: id=bravo target=... timestamp=... duration=... tokens=1.8k -->'
      - 'off': returns None
    """
    if style not in {"compact", "inline", "comment"}:
        return None

    clean_id = str(turn_id).strip() if turn_id else None
    clean_target = str(target).strip() if target else None
    formatted_ts = format_timestamp(timestamp, compact=(style in {"compact", "inline"}))
    formatted_dur = humanize_duration(duration_ms)
    clean_status = str(status).strip() if status else None
    formatted_tokens = (
        humanize_token_count(tokens)
        if isinstance(tokens, int)
        else (str(tokens).strip() if tokens else None)
    )

    if style == "compact":
        tokens_list: list[str] = []
        if clean_id:
            tokens_list.append(clean_id)
        if clean_status:
            tokens_list.append(clean_status)
        if clean_target:
            tokens_list.append(clean_target)
        if formatted_ts:
            tokens_list.append(formatted_ts)
        if formatted_dur:
            tokens_list.append(formatted_dur)
        if formatted_tokens:
            tokens_list.append(formatted_tokens)
        if not tokens_list:
            return None
        return f"[{' '.join(tokens_list)}]"

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
    if formatted_tokens:
        pairs.append(("tokens", formatted_tokens))

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


def extract_human_user_content(content: str) -> str:
    """Extract human-authored text from user turn content, filtering machine result blocks."""
    if not isinstance(content, str) or not content.strip():
        return ""

    lines = content.splitlines()
    human_lines: list[str] = []
    in_result_section = False
    in_fence = False
    fence_char: str | None = None
    fence_len: int = 0
    result_has_fence = False
    seen_result_first_line = False

    for line in lines:
        stripped = line.strip()

        # Check for fence inside a result section
        if in_result_section:
            if in_fence:
                close_match = _CODE_FENCE_CLOSE_RE.fullmatch(line)
                if close_match:
                    f_str = close_match.group("fence")
                    if f_str[0] == fence_char and len(f_str) >= fence_len:
                        in_fence = False
                continue

            # Not inside fence
            if _RESULT_HEADER_RE.match(stripped):
                in_result_section = True
                in_fence = False
                fence_char = None
                fence_len = 0
                result_has_fence = False
                seen_result_first_line = False
                continue

            open_match = _CODE_FENCE_OPEN_RE.match(line)
            if open_match:
                f_str = open_match.group("fence")
                in_fence = True
                fence_char = f_str[0]
                fence_len = len(f_str)
                result_has_fence = True
                continue

            if not stripped or _TELEMETRY_COMMENT_RE.match(stripped):
                continue

            # Standard machine harness lines
            if (
                _RESULT_STATUS_RE.match(stripped)
                or _RESULT_SPILLED_RE.match(stripped)
                or _RESULT_SECTION_LABEL_RE.match(stripped)
                or _RESULT_FOOTER_RE.match(stripped)
                or _RESULT_HINT_RE.match(stripped)
            ):
                continue

            # If this result section has not seen a fence yet and this is the first non-empty line
            # immediately under ## RESULT, treat it as the raw single-line result output.
            if not result_has_fence and not seen_result_first_line:
                seen_result_first_line = True
                continue

            # Any other non-harness line outside of fences is human user content!
            human_lines.append(line)
        else:
            # Outside result section (before the first ## RESULT)
            if _RESULT_HEADER_RE.match(stripped):
                in_result_section = True
                in_fence = False
                fence_char = None
                fence_len = 0
                result_has_fence = False
                seen_result_first_line = False
                continue

            if not stripped or _TELEMETRY_COMMENT_RE.match(stripped):
                continue

            human_lines.append(line)

    return "\n".join(human_lines).strip()


def is_human_user_turn(node: dict) -> bool:
    """Check if a node represents a human-authored user turn with substantive content.

    Returns False if the turn is purely a structural container enclosing tool results.
    Preserves human user prose positioned before, between, or outside result fences.
    """
    if not isinstance(node, dict) or node.get("role") != "user":
        return False
    if "content" not in node:
        return True
    content = str(node.get("content", ""))
    return bool(extract_human_user_content(content))


def is_actual_turn(node: dict) -> bool:
    """Check if a node represents an actual conversation turn (not a result or structural container)."""
    if not isinstance(node, dict):
        return False
    role = node.get("role")
    if role == "assistant":
        return True
    if role in {"state", "state-diff"}:
        return True
    if role == "user":
        return is_human_user_turn(node)
    return False


def count_actual_turns(
    history: list[dict],
    *,
    role: str | None = None,
    mode: str = "shared_dense",
) -> int:
    """Count the number of substantive actual turns in history.

    If mode in ('role_partitioned', 'role'):
      Counts only actual turns matching the given role.
    If mode in ('shared_dense', 'shared'):
      Counts all actual turns regardless of role.
    """
    norm_mode = mode.lower().strip() if isinstance(mode, str) else "shared_dense"
    if norm_mode in {"role_partitioned", "role"} and role is not None:
        target_role = role.lower().strip()
        count = 0
        for node in history:
            if not is_actual_turn(node):
                continue
            node_role = str(node.get("role", "")).lower().strip()
            if node_role == target_role:
                count += 1
        return count

    return sum(1 for node in history if is_actual_turn(node))


def decorate_user_turn_node(
    node: dict,
    *,
    style: str = "compact",
    turn_id: str | None = None,
    duration_ms: int | float | None = None,
    timestamp: datetime | str | None = None,
    tokens: int | str | None = None,
) -> dict:
    """Decorate a human user turn with turn handle, timestamp, dwell duration, and token count."""
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
        tokens=tokens,
        style=style,
    )
    if telemetry:
        if tid:
            node["turn_id"] = tid
        if tokens is not None:
            node["tokens"] = tokens
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
        if tokens is not None:
            meta["tokens"] = tokens
    return node


def decorate_result_node(
    node: dict,
    *,
    style: str = "compact",
    turn_id: str | None = None,
    duration_ms: int | float | None = None,
    timestamp: datetime | str | None = None,
    tokens: int | str | None = None,
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
        tokens=tokens,
        style=style,
    )
    if telemetry:
        if tid:
            node["turn_id"] = tid
        if tokens is not None:
            node["tokens"] = tokens
        if style in {"compact", "inline"}:
            node["result_marker"] = f"## RESULT {telemetry}"
        elif style == "comment":
            node["telemetry_comment"] = telemetry
    return node
