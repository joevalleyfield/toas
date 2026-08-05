from __future__ import annotations

import os
import re
import shlex
from datetime import date
from pathlib import Path

from ..backend_policy import generation_policy_from_config
from ..config import apply_overrides, config_from_discovered_paths
from ..graph import (
    active_config_overrides,
    active_surface_id,
    message_lineage,
    read_log,
    surface_bindings,
    write_session_successor_record,
)
from ..prompts import load_prompt_ref
from ..transcript import parse_transcript, render_transcript
from .rendering_edges import apply_newline_style, detect_newline_style
from .session_file_edges import read_text_preserve_newlines
from .session_step_edges import extract_operator_command_tail

_NAME_RE = re.compile(r"[A-Za-z0-9._-]+")
_ACTIVE_RUN_STATUSES = {"accepted", "starting", "running", "cancelling"}
_ACTIVE_QUEUE_STATUSES = {"pending", "running", "blocked", "awaiting_approval"}


def _latest_statuses(events: list[dict], kind: str, id_key: str) -> dict[str, str]:
    latest: dict[str, str] = {}
    for event in events:
        if event.get("kind") != kind:
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        identity = payload.get(id_key)
        status = payload.get("status")
        if isinstance(identity, str) and identity and isinstance(status, str):
            latest[identity] = status
    return latest


def continuation_blocker(events: list[dict]) -> str | None:
    active_runs = sorted(
        run_id
        for run_id, status in _latest_statuses(events, "run", "run_id").items()
        if status in _ACTIVE_RUN_STATUSES
    )
    if active_runs:
        return f"active run prevents session continuation: {', '.join(active_runs)}"
    active_queues = sorted(
        queue_id
        for queue_id, status in _latest_statuses(events, "execution_queue", "id").items()
        if status in _ACTIVE_QUEUE_STATUSES
    )
    if active_queues:
        return f"unresolved execution queue prevents session continuation: {', '.join(active_queues)}"
    return None


def rotation_blocker(events: list[dict]) -> str | None:
    """Compatibility alias for the original public helper."""
    return continuation_blocker(events)


def _section(content: str, heading: str) -> list[str]:
    lines = content.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == heading) + 1
    except StopIteration as exc:
        raise ValueError(f"compaction handoff missing {heading}") from exc
    out: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("## ") or stripped.startswith("### "):
            break
        if stripped:
            out.append(stripped)
    return out


def _shell_entries(content: str, heading: str) -> list[str]:
    entries: list[str] = []
    for line in _section(content, heading):
        normalized = line[2:].strip() if line.startswith("- ") else line
        if not normalized.startswith("$ "):
            raise ValueError(f"invalid {heading} entry: {line}")
        command = normalized[2:].strip()
        entries.append(command)
    return entries


def restoration_commands(handoff: str, *, workdir: Path) -> list[str]:
    file_commands = _shell_entries(handoff, "### Files to Restore")
    files: list[str] = []
    for command in file_commands:
        try:
            argv = shlex.split(command.replace("\\", "/"))
        except ValueError as exc:
            raise ValueError(f"invalid Files to Restore command: {command}") from exc
        if len(argv) != 2 or argv[0] != "cat" or argv[1].startswith("-"):
            raise ValueError(f"Files to Restore entry must be '$ cat <path>': $ {command}")
        path = argv[1].replace("\\", "/")
        if path not in files:
            files.append(path)

    agents_path = workdir / "AGENTS.md"
    agents_entries = [item for item in files if item.rsplit("/", 1)[-1] == "AGENTS.md"]
    files = [item for item in files if item.rsplit("/", 1)[-1] != "AGENTS.md"]
    if agents_entries:
        files.insert(0, agents_entries[0])
    elif agents_path.is_file():
        files.insert(0, "AGENTS.md")

    commands = [f"cat {shlex.quote(path)}" for path in files]
    commands.extend(_shell_entries(handoff, "### Commands to Run"))
    return commands


def restoration_plan(handoff: str, *, workdir: Path) -> list[str]:
    """Compatibility alias; restoration is now literal user command text."""
    return restoration_commands(handoff, workdir=workdir)


def _objective_slug(handoff: str) -> str:
    objective = " ".join(_section(handoff, "## Current Objective"))
    objective = re.sub(r"[`*_#]", "", objective).strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", objective).strip("-")
    if not slug:
        slug = "session-handoff"
    return slug[:48].rstrip("-")


def suggested_continuation_name(handoff: str, *, today: date | None = None) -> str:
    stamp = (today or date.today()).strftime("%y%m%d")
    return f"{stamp}-{_objective_slug(handoff)}"


def suggested_rotation_name(handoff: str, *, today: date | None = None) -> str:
    """Compatibility alias for the original public helper."""
    return suggested_continuation_name(handoff, today=today)


def _resolve_target_path(name: str, *, sessions_dir: Path) -> Path:
    normalized = name.strip()
    if not _NAME_RE.fullmatch(normalized):
        raise ValueError("session continuation name must match [A-Za-z0-9._-]+")
    candidate = sessions_dir / f"session-{normalized}.md"
    ordinal = 2
    while candidate.exists():
        candidate = sessions_dir / f"session-{normalized}-{ordinal}.md"
        ordinal += 1
    return candidate


def _events_path(workdir: Path) -> Path:
    preferred = workdir / ".toas" / "events.jsonl"
    legacy = workdir / "events.jsonl"
    return legacy if legacy.exists() and not preferred.exists() else preferred


def _default_predecessor_path(*, workdir: Path, events: list[dict]) -> Path:
    file_config = config_from_discovered_paths(workdir=workdir)
    config = apply_overrides(file_config, active_config_overrides(events))
    selected_surface_id = active_surface_id(events)
    configured_path = (
        surface_bindings(events).get(selected_surface_id, config.session.transcript_path)
        if isinstance(selected_surface_id, str) and selected_surface_id
        else config.session.transcript_path
    )
    return Path(configured_path)


def _workspace_path(path: str | Path, *, workdir: Path, label: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = workdir / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(workdir)
    except ValueError as exc:
        raise RuntimeError(f"{label} transcript must be inside the workspace") from exc
    return candidate


def _handoff_from_transcript(transcript: str) -> str:
    nodes = parse_transcript(transcript)
    if len(nodes) < 2 or nodes[-2].get("role") != "user" or nodes[-1].get("role") != "assistant":
        raise RuntimeError("session continuation requires /compact followed by an assistant handoff")
    command = extract_operator_command_tail(str(nodes[-2].get("content", "")))
    if command != ("compact", []):
        raise RuntimeError("session continuation requires /compact at the end of the last user turn")
    handoff = str(nodes[-1].get("content", "")).strip()
    if not handoff.startswith("# Handoff Summary"):
        raise RuntimeError("session continuation requires a handoff-shaped assistant turn")
    return handoff


def _seed_message(seed: str) -> dict:
    parsed = parse_transcript(seed)
    if parsed:
        if len(parsed) != 1 or parsed[0].get("role") != "user":
            raise RuntimeError("bootstrap seed must compose to one user message")
        return {"role": "user", "content": str(parsed[0]["content"]).strip()}
    return {"role": "user", "content": seed.strip()}


def _continuation_inputs(*, workdir: Path, predecessor_path: str | None) -> dict:
    events_path = _events_path(workdir)
    events = read_log(str(events_path))
    blocker = continuation_blocker(events)
    if blocker is not None:
        raise RuntimeError(blocker)

    requested = predecessor_path or _default_predecessor_path(workdir=workdir, events=events)
    predecessor = _workspace_path(requested, workdir=workdir, label="predecessor")
    if not predecessor.is_file():
        raise RuntimeError(f"predecessor transcript does not exist: {predecessor}")
    predecessor_text = read_text_preserve_newlines(predecessor)
    handoff = _handoff_from_transcript(predecessor_text)

    file_config = config_from_discovered_paths(workdir=workdir)
    config = apply_overrides(file_config, active_config_overrides(events))
    prompt_ref = config.session.bootstrap_prompt_ref
    seed = load_prompt_ref(
        prompt_ref,
        mode=config.prompt.mode,
        constraints=list(config.prompt.constraints),
        policy=generation_policy_from_config(config),
        capability_profile=config.capability_advertisement.profile,
        capability_hidden_tools=config.capability_advertisement.hidden_tools,
        prompt_ingress=config.prompt.ingress,
        prompt_output_profile=config.prompt.output_profile,
    )
    commands = restoration_commands(handoff, workdir=workdir)
    if not commands:
        raise RuntimeError("compaction handoff contains no restoration commands")
    lineage = message_lineage(events)
    continuation_parent_id = lineage[-1].get("id") if lineage else None
    return {
        "events_path": events_path,
        "predecessor": predecessor,
        "predecessor_text": predecessor_text,
        "handoff": handoff,
        "prompt_ref": prompt_ref,
        "seed": seed,
        "commands": commands,
        "continuation_parent_id": continuation_parent_id,
    }


def _render_successor(*, seed: str, handoff: str, commands: list[str], newline: str) -> str:
    restoration = "\n".join(f"$ {command}" for command in commands)
    transcript = render_transcript(
        [
            _seed_message(seed),
            {"role": "assistant", "content": handoff.strip()},
            {"role": "user", "content": restoration},
        ],
        spaced=True,
    )
    return apply_newline_style(transcript, newline)


def continue_session(
    *,
    workdir: str | Path,
    predecessor_path: str | None = None,
    accepted_name: str | None = None,
    today: date | None = None,
) -> dict:
    root = Path(workdir).resolve()
    inputs = _continuation_inputs(workdir=root, predecessor_path=predecessor_path)
    suggestion = suggested_continuation_name(inputs["handoff"], today=today)
    if accepted_name is None:
        target = _resolve_target_path(suggestion, sessions_dir=inputs["predecessor"].parent)
        return {
            "status": "suggested",
            "suggested_name": suggestion,
            "suggested_path": target.relative_to(root).as_posix(),
            "predecessor_path": inputs["predecessor"].relative_to(root).as_posix(),
        }

    target = _resolve_target_path(accepted_name, sessions_dir=inputs["predecessor"].parent)
    newline = detect_newline_style(inputs["predecessor_text"])
    transcript = _render_successor(
        seed=inputs["seed"],
        handoff=inputs["handoff"],
        commands=inputs["commands"],
        newline=newline,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as stream:
            stream.write(transcript)
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    relative_predecessor = inputs["predecessor"].relative_to(root).as_posix()
    relative_target = target.relative_to(root).as_posix()
    before_events = inputs["events_path"].read_bytes() if inputs["events_path"].exists() else b""
    try:
        write_session_successor_record(
            str(inputs["events_path"]),
            predecessor_path=relative_predecessor,
            successor_path=relative_target,
            continuation_parent_id=inputs["continuation_parent_id"],
            seed_prompt_ref=inputs["prompt_ref"],
        )
    except Exception:
        after_events = inputs["events_path"].read_bytes() if inputs["events_path"].exists() else b""
        if after_events == before_events:
            target.unlink(missing_ok=True)
        raise
    return {
        "status": "continued",
        "accepted_name": accepted_name,
        "successor_path": relative_target,
        "predecessor_path": relative_predecessor,
        "restoration_commands": len(inputs["commands"]),
    }


def rotate_session(**kwargs) -> dict:
    """Compatibility alias for callers using the original rotation name."""
    return continue_session(**kwargs)
