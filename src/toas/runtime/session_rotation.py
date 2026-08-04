from __future__ import annotations

import os
import re
import shlex
from datetime import date
from pathlib import Path

import yaml

from ..backend_policy import generation_policy_from_config
from ..config import apply_overrides, config_from_discovered_paths
from ..graph import (
    active_compaction_projection,
    active_config_overrides,
    active_surface_id,
    message_lineage,
    read_log,
    surface_bindings,
    write_session_rotation_transition,
)
from ..prompts import load_prompt_ref

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


def rotation_blocker(events: list[dict]) -> str | None:
    active_runs = sorted(
        run_id
        for run_id, status in _latest_statuses(events, "run", "run_id").items()
        if status in _ACTIVE_RUN_STATUSES
    )
    if active_runs:
        return f"active run prevents session rotation: {', '.join(active_runs)}"
    active_queues = sorted(
        queue_id
        for queue_id, status in _latest_statuses(events, "execution_queue", "id").items()
        if status in _ACTIVE_QUEUE_STATUSES
    )
    if active_queues:
        return f"unresolved execution queue prevents session rotation: {', '.join(active_queues)}"
    return None


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


def restoration_plan(handoff: str, *, workdir: Path) -> list[dict]:
    file_commands = _shell_entries(handoff, "### Files to Restore")
    files: list[str] = []
    for command in file_commands:
        try:
            argv = shlex.split(command)
        except ValueError as exc:
            raise ValueError(f"invalid Files to Restore command: {command}") from exc
        if len(argv) != 2 or argv[0] != "cat" or argv[1].startswith("-"):
            raise ValueError(f"Files to Restore entry must be '$ cat <path>': $ {command}")
        if argv[1] not in files:
            files.append(argv[1])

    agents_path = workdir / "AGENTS.md"
    agents_entries = [item for item in files if Path(item).name == "AGENTS.md"]
    files = [item for item in files if Path(item).name != "AGENTS.md"]
    if agents_entries:
        files.insert(0, agents_entries[0])
    elif agents_path.is_file():
        files.insert(0, "AGENTS.md")

    plan = [
        {"operation": "read_file", "arguments": {"path": path, "number_lines": True}}
        for path in files
    ]
    for command in _shell_entries(handoff, "### Commands to Run"):
        plan.append({"operation": "shell_script", "arguments": {"script": command}})
    return plan


def _objective_slug(handoff: str) -> str:
    objective = " ".join(_section(handoff, "## Current Objective"))
    objective = re.sub(r"[`*_#]", "", objective).strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", objective).strip("-")
    if not slug:
        slug = "session-handoff"
    return slug[:48].rstrip("-")


def suggested_rotation_name(handoff: str, *, today: date | None = None) -> str:
    stamp = (today or date.today()).strftime("%y%m%d")
    return f"{stamp}-{_objective_slug(handoff)}"


def _resolve_target_path(name: str, *, sessions_dir: Path) -> Path:
    normalized = name.strip()
    if not _NAME_RE.fullmatch(normalized):
        raise ValueError("session rotation name must match [A-Za-z0-9._-]+")
    candidate = sessions_dir / f"session-{normalized}.md"
    ordinal = 2
    while candidate.exists():
        candidate = sessions_dir / f"session-{normalized}-{ordinal}.md"
        ordinal += 1
    return candidate


def _rotation_inputs(*, workdir: Path, predecessor_path: str | None) -> dict:
    preferred_events_path = workdir / ".toas" / "events.jsonl"
    legacy_events_path = workdir / "events.jsonl"
    events_path = legacy_events_path if legacy_events_path.exists() and not preferred_events_path.exists() else preferred_events_path
    events = read_log(str(events_path))
    blocker = rotation_blocker(events)
    if blocker is not None:
        raise RuntimeError(blocker)
    projection = active_compaction_projection(events)
    if projection is None:
        raise RuntimeError("session rotation requires a selected LLM compaction projection")
    projection_id = projection["payload"]["projection_message_id"]
    lineage = message_lineage(events)
    projection_message = next((event for event in lineage if event.get("id") == projection_id), None)
    if projection_message is None or projection_message is not lineage[-1]:
        raise RuntimeError("selected compaction projection is not the current safe lineage boundary")
    handoff = str(projection_message["content"])

    file_config = config_from_discovered_paths(workdir=workdir)
    config = apply_overrides(file_config, active_config_overrides(events))
    selected_surface_id = active_surface_id(events)
    configured_path = (
        surface_bindings(events).get(selected_surface_id, config.session.transcript_path)
        if isinstance(selected_surface_id, str) and selected_surface_id
        else config.session.transcript_path
    )
    predecessor = Path(predecessor_path) if predecessor_path else Path(configured_path)
    if not predecessor.is_absolute():
        predecessor = workdir / predecessor
    predecessor = predecessor.resolve()
    try:
        predecessor.relative_to(workdir)
    except ValueError as exc:
        raise RuntimeError("predecessor transcript must be inside the workspace") from exc
    if not predecessor.is_file():
        raise RuntimeError(f"predecessor transcript does not exist: {predecessor}")
    if handoff not in predecessor.read_text(encoding="utf-8"):
        raise RuntimeError("predecessor transcript does not contain the selected compaction handoff")

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
    plan = restoration_plan(handoff, workdir=workdir)
    if not plan:
        raise RuntimeError("compaction handoff contains no restoration operations")
    return {
        "events_path": events_path,
        "events": events,
        "projection_id": projection_id,
        "predecessor": predecessor,
        "handoff": handoff,
        "prompt_ref": prompt_ref,
        "seed": seed,
        "plan": plan,
        "surface_id": selected_surface_id,
    }


def _render_successor(*, seed: str, handoff: str, plan: list[dict]) -> tuple[str, str]:
    plan_text = yaml.safe_dump(plan, sort_keys=False, allow_unicode=True).rstrip()
    plan_message = f"```yaml\n{plan_text}\n```"
    transcript = (
        f"## TOAS:USER\n\n{seed.strip()}\n\n"
        f"## TOAS:USER\n\n{handoff.strip()}\n\n"
        f"## TOAS:USER\n\n{plan_message}\n"
    )
    return transcript, plan_message


def rotate_session(
    *,
    workdir: str | Path,
    predecessor_path: str | None = None,
    accepted_name: str | None = None,
    today: date | None = None,
) -> dict:
    root = Path(workdir).resolve()
    inputs = _rotation_inputs(workdir=root, predecessor_path=predecessor_path)
    suggestion = suggested_rotation_name(inputs["handoff"], today=today)
    if accepted_name is None:
        target = _resolve_target_path(suggestion, sessions_dir=inputs["predecessor"].parent)
        return {
            "status": "suggested",
            "suggested_name": suggestion,
            "suggested_path": str(target.relative_to(root)),
            "predecessor_path": str(inputs["predecessor"]),
        }

    target = _resolve_target_path(accepted_name, sessions_dir=inputs["predecessor"].parent)
    transcript, plan_message = _render_successor(
        seed=inputs["seed"],
        handoff=inputs["handoff"],
        plan=inputs["plan"],
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp-{os.getpid()}")
    temporary.write_text(transcript, encoding="utf-8")
    os.replace(temporary, target)
    relative_target = str(target.relative_to(root))
    try:
        write_session_rotation_transition(
            str(inputs["events_path"]),
            messages=[
                {"role": "user", "content": inputs["seed"].strip(), "provenance": {"source": "session_rotation_seed"}},
                {"role": "user", "content": inputs["handoff"].strip(), "provenance": {"source": "session_rotation_handoff"}},
                {"role": "user", "content": plan_message, "provenance": {"source": "session_rotation_restoration"}},
            ],
            predecessor_path=str(inputs["predecessor"]),
            successor_path=relative_target,
            projection_message_id=inputs["projection_id"],
            seed_prompt_ref=inputs["prompt_ref"],
            surface_id=inputs["surface_id"],
        )
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {
        "status": "rotated",
        "accepted_name": accepted_name,
        "successor_path": relative_target,
        "predecessor_path": str(inputs["predecessor"]),
        "restoration_operations": len(inputs["plan"]),
    }
