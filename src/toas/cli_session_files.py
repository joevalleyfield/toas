from __future__ import annotations

import os
import re
import shlex
from datetime import datetime
from pathlib import Path

from .runtime.session_rotation import _NAME_RE, _resolve_target_path

_SESSION_PREFIX_RE = re.compile(r"^session-(\d{6}-\d{4})(?:-|\.md)")


def _sessions_dir(workdir: Path) -> Path:
    return workdir / ".toas"


def _new_session_name(slug: str | None, *, now: datetime | None = None) -> str:
    dt = now or datetime.now()
    stamp = dt.strftime("%y%m%d-%H%M")
    if slug is None or slug == "":
        return stamp
    return f"{stamp}-{slug}"


def _validate_slug(slug: str) -> str:
    normalized = slug.strip()
    if not _NAME_RE.fullmatch(normalized):
        raise SystemExit(
            f"invalid slug: {slug!r} (must match [A-Za-z0-9._-]+)"
        )
    return normalized


def _create_session_file(*, slug: str | None, workdir: Path, now: datetime | None = None) -> Path:
    normalized_slug = _validate_slug(slug) if slug is not None else None
    name = _new_session_name(normalized_slug, now=now)
    target = _resolve_target_path(name, sessions_dir=_sessions_dir(workdir))
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.touch()
    return target


def _dated_sessions(workdir: Path) -> list[tuple[tuple[int, int], float, Path]]:
    sessions_dir = _sessions_dir(workdir)
    if not sessions_dir.is_dir():
        return []
    ranked: list[tuple[tuple[int, int], float, Path]] = []
    for path in sessions_dir.glob("session-*.md"):
        match = _SESSION_PREFIX_RE.match(path.name)
        if match is None:
            continue
        stamp = match.group(1)
        day, minute = stamp.split("-")
        ranked.append(((int(day), int(minute)), path.stat().st_mtime, path))
    return ranked


def _most_recent_session(*, workdir: Path) -> Path:
    ranked = _dated_sessions(workdir)
    if ranked:
        return max(ranked, key=lambda item: (item[0], item[1]))[2]
    return _sessions_dir(workdir) / "session.md"


def _resolve_editor() -> str:
    for var in ("TOAS_EDITOR", "EDITOR"):
        value = os.environ.get(var)
        if value and value.strip():
            return value.strip()
    return "vim"


def _open_in_editor(path: Path, *, editor: str | None = None, exec_fn=os.execvp) -> None:
    command = editor or _resolve_editor()
    parts = shlex.split(command)
    parts.append(str(path))
    exec_fn(parts[0], parts)


def run_new(
    slug: str | None,
    *,
    edit: bool = False,
    workdir: Path | None = None,
    now: datetime | None = None,
    editor: str | None = None,
    exec_fn=os.execvp,
    print_fn=print,
) -> Path:
    base = workdir if workdir is not None else Path.cwd()
    target = _create_session_file(slug=slug, workdir=base, now=now)
    print_fn(target.as_posix())
    if edit:
        _open_in_editor(target, editor=editor, exec_fn=exec_fn)
    return target


def run_edit(
    path: str | None,
    *,
    workdir: Path | None = None,
    editor: str | None = None,
    exec_fn=os.execvp,
) -> Path:
    base = workdir if workdir is not None else Path.cwd()
    target = Path(path) if path is not None else _most_recent_session(workdir=base)
    if not target.is_absolute():
        target = (base / target).resolve()
    if not target.exists():
        raise SystemExit(f"no such session: {target}")
    _open_in_editor(target, editor=editor, exec_fn=exec_fn)
    return target
