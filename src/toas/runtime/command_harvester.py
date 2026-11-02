"""Harvester and profiler for executable commands recorded in event logs."""

from __future__ import annotations

import json
import shlex
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from ..shell_grants import shell_script_segment_commands
from .matchers import extract_subcommand


@dataclass(frozen=True)
class HarvestedInvocation:
    prefix: str
    subcommand: str | None
    flags: tuple[str, ...]
    raw_argv: tuple[str, ...]
    origin: str  # "assistant" or "user"
    tool_name: str  # "shell", "shell_script", etc.


@dataclass
class CommandProfile:
    prefix: str
    total_calls: int = 0
    assistant_calls: int = 0
    user_calls: int = 0
    subcommands: dict[str, int] = field(default_factory=dict)
    flags: dict[str, int] = field(default_factory=dict)
    sample_invocations: list[tuple[str, ...]] = field(default_factory=list)

    def record(self, inv: HarvestedInvocation) -> None:
        self.total_calls += 1
        if inv.origin == "user":
            self.user_calls += 1
        else:
            self.assistant_calls += 1

        if inv.subcommand:
            self.subcommands[inv.subcommand] = self.subcommands.get(inv.subcommand, 0) + 1

        for flag in inv.flags:
            self.flags[flag] = self.flags.get(flag, 0) + 1

        if len(self.sample_invocations) < 5 and inv.raw_argv not in self.sample_invocations:
            self.sample_invocations.append(inv.raw_argv)


@dataclass
class HarvestReport:
    total_events_scanned: int = 0
    total_invocations: int = 0
    profiles: dict[str, CommandProfile] = field(default_factory=dict)

    def record(self, inv: HarvestedInvocation) -> None:
        self.total_invocations += 1
        if inv.prefix not in self.profiles:
            self.profiles[inv.prefix] = CommandProfile(prefix=inv.prefix)
        self.profiles[inv.prefix].record(inv)


def make_invocation(
    argv: Sequence[str],
    *,
    origin: str,
    tool_name: str,
) -> HarvestedInvocation | None:
    """Create a HarvestedInvocation from a tokenized argv sequence."""
    if not argv:
        return None
    clean_argv = [str(token) for token in argv if token]
    if not clean_argv:
        return None
    prefix = clean_argv[0]
    subcommand = extract_subcommand(clean_argv)
    flags = tuple(token for token in clean_argv[1:] if token.startswith("-"))
    return HarvestedInvocation(
        prefix=prefix,
        subcommand=subcommand,
        flags=flags,
        raw_argv=tuple(clean_argv),
        origin=origin,
        tool_name=tool_name,
    )


def parse_command_string(command: str) -> list[str]:
    """Split a command line safely with fallback on unbalanced quotes."""
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def extract_invocations_from_tool_call(
    call: dict,
    *,
    origin: str = "assistant",
) -> list[HarvestedInvocation]:
    """Extract invocations from a single tool call dictionary."""
    tool_name = str(call.get("tool_name") or "")
    args = call.get("args")
    if not isinstance(args, dict):
        return []

    results: list[HarvestedInvocation] = []

    if tool_name == "shell":
        argv = args.get("argv")
        if isinstance(argv, list) and argv:
            inv = make_invocation(argv, origin=origin, tool_name=tool_name)
            if inv:
                results.append(inv)
        elif isinstance(args.get("command"), str) and args["command"].strip():
            parsed = parse_command_string(args["command"])
            inv = make_invocation(parsed, origin=origin, tool_name=tool_name)
            if inv:
                results.append(inv)

    elif tool_name == "shell_script":
        script = args.get("script")
        if isinstance(script, str) and script.strip():
            for segment in shell_script_segment_commands(script):
                parsed = parse_command_string(segment)
                inv = make_invocation(parsed, origin=origin, tool_name=tool_name)
                if inv:
                    results.append(inv)

    elif tool_name in {"python_script", "powershell_script", "interpreter_script"}:
        runtime = args.get("runtime")
        if isinstance(runtime, list) and runtime:
            inv = make_invocation(runtime, origin=origin, tool_name=tool_name)
            if inv:
                results.append(inv)
        else:
            default_prefix = (
                "python3"
                if "python" in tool_name
                else ("pwsh" if "powershell" in tool_name else tool_name)
            )
            inv = make_invocation([default_prefix], origin=origin, tool_name=tool_name)
            if inv:
                results.append(inv)

    return results


def extract_invocations_from_message(record: dict) -> list[HarvestedInvocation]:
    """Extract invocations from user message content lines starting with $."""
    role = record.get("role")
    content = record.get("content")
    if role != "user" or not isinstance(content, str):
        return []

    results: list[HarvestedInvocation] = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("$ "):
            cmd_str = line[2:].strip()
            if cmd_str:
                parsed = parse_command_string(cmd_str)
                inv = make_invocation(parsed, origin="user", tool_name="user_shell")
                if inv:
                    results.append(inv)
    return results


def harvest_from_events(lines: Iterable[str]) -> HarvestReport:
    """Scan raw JSONL lines and produce an aggregated HarvestReport."""
    report = HarvestReport()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not isinstance(record, dict):
            continue

        report.total_events_scanned += 1
        kind = record.get("kind")

        # 1. tool_request
        if kind == "tool_request":
            payload = record.get("payload")
            if isinstance(payload, list):
                for call in payload:
                    if isinstance(call, dict):
                        for inv in extract_invocations_from_tool_call(call, origin="assistant"):
                            report.record(inv)

        # 2. state_transition or state_diff
        elif kind in {"state_transition", "state_diff"}:
            tool_calls = record.get("tool_calls")
            if isinstance(tool_calls, list):
                for call in tool_calls:
                    if isinstance(call, dict):
                        for inv in extract_invocations_from_tool_call(call, origin="assistant"):
                            report.record(inv)

        # 3. Message events (e.g. user prompt shell commands)
        if "role" in record:
            for inv in extract_invocations_from_message(record):
                report.record(inv)

    return report


def harvest_from_event_log(path: Path | str) -> HarvestReport:
    """Read an events.jsonl file and return a HarvestReport."""
    file_path = Path(path).resolve()
    if not file_path.is_file():
        raise FileNotFoundError(f"event log not found: {file_path}")
    with open(file_path, encoding="utf-8", errors="replace") as f:
        return harvest_from_events(f)


def format_harvest_report(report: HarvestReport) -> str:
    """Format a HarvestReport into a human-readable CLI summary."""
    lines: list[str] = [
        f"Harvested {report.total_invocations} executable invocations across {report.total_events_scanned} events:",
        "",
    ]
    if not report.profiles:
        lines.append("  No executable invocations observed.")
        return "\n".join(lines)

    sorted_profiles = sorted(
        report.profiles.values(),
        key=lambda p: p.total_calls,
        reverse=True,
    )

    for p in sorted_profiles:
        lines.append(
            f"• {p.prefix}: {p.total_calls} calls (assistant: {p.assistant_calls}, user: {p.user_calls})"
        )
        if p.subcommands:
            sorted_subs = sorted(p.subcommands.items(), key=lambda x: x[1], reverse=True)
            sub_strs = [f"{cmd} ({cnt})" for cmd, cnt in sorted_subs]
            lines.append(f"    subcommands: {', '.join(sub_strs)}")
        if p.flags:
            sorted_flags = sorted(p.flags.items(), key=lambda x: x[1], reverse=True)
            flag_strs = [f"{flg} ({cnt})" for flg, cnt in sorted_flags[:8]]
            lines.append(f"    flags: {', '.join(flag_strs)}")
        lines.append("")

    return "\n".join(lines).rstrip()
