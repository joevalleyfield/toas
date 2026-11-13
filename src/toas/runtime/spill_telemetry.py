"""Aggregate-only projections of local spill observations in durable tool results."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Iterator

SCHEMA = "spill_telemetry.v0"
_OBSERVATION_SCHEMA = "spill_observation.v0"
_TOOL_BUCKETS = (
    "activate_skill", "apply_patch", "capability_help", "capture_task_thread", "code_survey",
    "echo", "echo_block", "get_structure", "interpreter_script", "powershell_script",
    "procedure", "python_script", "read_file", "replace_block", "replace_range", "search",
    "shell", "shell_script", "skill", "write_file", "other",
)
_REFERENCE_TOOLS = frozenset({"read_file", "shell", "shell_script"})
_BLOCK_REFERENCE_RE = re.compile(r"\bib_[a-zA-Z0-9_-]+\b")
_LINE_BUCKETS = ((0, 0, "0"), (1, 1, "1"), (2, 10, "2_10"), (11, 40, "11_40"), (41, 100, "41_100"), (101, 500, "101_500"), (501, None, "501_plus"))
_BYTE_BUCKETS = ((0, 1023, "0_1k"), (1024, 4095, "1k_4k"), (4096, 16383, "4k_16k"), (16384, 65535, "16k_64k"), (65536, None, "64k_plus"))


def _bucket(value: int, buckets: tuple[tuple[int, int | None, str], ...]) -> str:
    return next(name for low, high, name in buckets if value >= low and (high is None or value <= high))


def _tool_bucket(name: object) -> str:
    value = str(name) if name is not None else "other"
    return value if value in _TOOL_BUCKETS else "other"


def _result_observations(value: object) -> Iterator[dict]:
    if isinstance(value, list):
        for telemetry in value:
            if isinstance(telemetry, dict) and telemetry.get("schema") == _OBSERVATION_SCHEMA:
                yield telemetry


def _references(value: object) -> set[str]:
    if isinstance(value, str):
        return set(_BLOCK_REFERENCE_RE.findall(value))
    if isinstance(value, dict):
        return set().union(*(_references(child) for child in value.values())) if value else set()
    if isinstance(value, list):
        return set().union(*(_references(child) for child in value)) if value else set()
    return set()


def _request_key(kind: str, record: dict) -> str:
    # Hash locally so duplicate/replayed request records can be collapsed without
    # retaining or returning arguments, commands, or their contents.
    encoded = json.dumps([kind, record.get("related_to"), record.get("payload")], sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def empty_spill_telemetry() -> dict:
    def tool_stats() -> dict:
        return {
            "eligible_outputs": 0,
            "spill_count": 0,
            "unobserved_result_records": 0,
            "line_distribution": {name: 0 for _, _, name in _LINE_BUCKETS},
            "byte_distribution": {name: 0 for _, _, name in _BYTE_BUCKETS},
            "spill_line_distribution": {name: 0 for _, _, name in _LINE_BUCKETS},
            "spill_byte_distribution": {name: 0 for _, _, name in _BYTE_BUCKETS},
        }

    return {
        "schema": SCHEMA,
        "coverage": {"result_records": 0, "observed_result_records": 0, "unobserved_result_records": 0},
        "tools": {name: tool_stats() for name in _TOOL_BUCKETS},
        "rereads": {
            "reference_pairs": 0,
            "read_file_confirmed_pairs": 0,
            "distinct_spilled_blocks": 0,
            "distinct_referenced_blocks": 0,
            "distinct_read_file_confirmed_blocks": 0,
            "by_tool": dict.fromkeys((*sorted(_REFERENCE_TOOLS), "other"), 0),
            "interpretation": "inferred_reference_proxy; exact known block references do not prove the file was opened",
            "scope": "read_file, shell, shell_script, and direct shell request text; other readers are unobserved",
        },
    }


def aggregate_spill_telemetry(lines: Iterable[str]) -> dict:
    report = empty_spill_telemetry()
    seen_observations: set[str] = set()
    seen_result_records: set[str] = set()
    seen_requests: set[str] = set()
    spill_origins: dict[str, set[str | None]] = {}
    matched_pairs: set[tuple[str, str]] = set()
    pending_read_file_pairs: set[tuple[str | None, str, str]] = set()
    confirmed_pairs: set[tuple[str, str]] = set()
    pair_tools: dict[tuple[str, str], str] = {}
    command_origins: dict[str, str | None] = {}

    for raw_line in lines:
        try:
            record = json.loads(raw_line)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(record, dict):
            continue
        kind = record.get("kind")
        related_to = record.get("related_to")
        origin = str(related_to) if related_to is not None else None

        if kind in {"tool_request", "command_request"}:
            key = _request_key(str(kind), record)
            if key in seen_requests:
                continue
            seen_requests.add(key)
            payload = record.get("payload")
            candidates: list[tuple[str, object]] = []
            if kind == "tool_request" and isinstance(payload, list):
                candidates.extend(
                    (str(call.get("tool_name") or "other"), call.get("args"))
                    for call in payload if isinstance(call, dict)
                )
            elif kind == "command_request" and isinstance(payload, dict):
                candidates.append(("shell", [payload.get("command"), payload.get("args")]))
                command_id = payload.get("id")
                if isinstance(command_id, str):
                    command_origins[command_id] = origin
            for name, args in candidates:
                if name not in _REFERENCE_TOOLS:
                    continue
                for block_id in _references(args):
                    origins = spill_origins.get(block_id, set())
                    if not any(spill_origin != origin for spill_origin in origins):
                        continue
                    pair = (key, block_id)
                    if pair in matched_pairs:
                        continue
                    matched_pairs.add(pair)
                    pair_tools[pair] = name
                    if name == "read_file":
                        pending_read_file_pairs.add((origin, block_id, key))
            continue

        if kind not in {"tool_result", "command_result"}:
            continue

        payload = record.get("payload")
        if kind == "command_result":
            origin = command_origins.get(str(related_to), origin)
        telemetries = list(_result_observations(record.get("spill_telemetry")))
        record_id = "|".join(sorted(
            str(telemetry.get("result_id")) for telemetry in telemetries if telemetry.get("result_id")
        ))
        if not record_id:
            record_id = hashlib.sha256(json.dumps(record, sort_keys=True, default=str).encode("utf-8")).hexdigest()
        record_key = f"{origin}|{record_id}"
        if record_key in seen_result_records:
            continue
        seen_result_records.add(record_key)
        report["coverage"]["result_records"] += 1
        if telemetries:
            report["coverage"]["observed_result_records"] += 1
        else:
            report["coverage"]["unobserved_result_records"] += 1
            legacy_tool = "shell" if kind == "command_result" else (payload.get("tool_name") if isinstance(payload, dict) else "other")
            report["tools"][_tool_bucket(legacy_tool)]["unobserved_result_records"] += 1
            continue

        for telemetry in telemetries:
            read_block_id = telemetry.get("read_block_id")
            if isinstance(read_block_id, str):
                confirmed_pairs.update(
                    (request_key, read_block_id)
                    for read_origin, block_id, request_key in pending_read_file_pairs
                    if (read_origin, block_id) == (origin, read_block_id)
                )
            outputs = telemetry.get("outputs")
            if not isinstance(outputs, list):
                continue
            for obs in outputs:
                if not isinstance(obs, dict):
                    continue
                observation_id = obs.get("observation_id")
                if not isinstance(observation_id, str) or observation_id in seen_observations:
                    continue
                seen_observations.add(observation_id)
                tool = report["tools"][_tool_bucket(obs.get("tool_name"))]
                line_count = obs.get("original_lines")
                byte_count = obs.get("original_bytes")
                if not isinstance(line_count, int) or isinstance(line_count, bool) or line_count < 0:
                    continue
                if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count < 0:
                    continue
                tool["eligible_outputs"] += 1
                tool["line_distribution"][_bucket(line_count, _LINE_BUCKETS)] += 1
                tool["byte_distribution"][_bucket(byte_count, _BYTE_BUCKETS)] += 1
                if obs.get("spilled") is True:
                    tool["spill_count"] += 1
                    tool["spill_line_distribution"][_bucket(line_count, _LINE_BUCKETS)] += 1
                    tool["spill_byte_distribution"][_bucket(byte_count, _BYTE_BUCKETS)] += 1
                    spilled_block_id = obs.get("block_id")
                    if isinstance(spilled_block_id, str):
                        spill_origins.setdefault(spilled_block_id, set()).add(origin)

    report["rereads"]["reference_pairs"] = len(matched_pairs)
    report["rereads"]["read_file_confirmed_pairs"] = len(confirmed_pairs)
    report["rereads"]["distinct_spilled_blocks"] = len(spill_origins)
    report["rereads"]["distinct_referenced_blocks"] = len({block_id for _, block_id in matched_pairs})
    report["rereads"]["distinct_read_file_confirmed_blocks"] = len({block_id for _, block_id in confirmed_pairs})
    for bucket in report["rereads"]["by_tool"]:
        report["rereads"]["by_tool"][bucket] = sum(tool == bucket for tool in pair_tools.values())
    for stats in report["tools"].values():
        count = stats["eligible_outputs"]
        stats["spill_rate_percent"] = round(stats["spill_count"] * 100 / count, 2) if count else 0.0
    return report


def aggregate_spill_telemetry_file(path) -> dict:
    from pathlib import Path

    with Path(path).open(encoding="utf-8", errors="replace") as source:
        return aggregate_spill_telemetry(source)
