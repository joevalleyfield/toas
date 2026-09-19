from __future__ import annotations

import os
import shutil
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentProfile:
    name: str
    variables: tuple[tuple[str, str], ...] = ()
    path_prepend: tuple[str, ...] = ()
    path_append: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeEnvironmentBinding:
    selector: str
    profile: str
    mode: str = "merge"


@dataclass(frozen=True)
class EnvironmentPolicy:
    mode: str = "inherit"
    profiles: tuple[EnvironmentProfile, ...] = ()
    bindings: tuple[RuntimeEnvironmentBinding, ...] = ()


_ACTIVE_POLICY: ContextVar[EnvironmentPolicy | None] = ContextVar("toas_environment_policy", default=None)
_ACTIVE_OVERRIDES: ContextVar[dict[str, str | None] | None] = ContextVar(
    "toas_environment_overrides", default=None
)


@contextmanager
def active_environment_policy(policy: EnvironmentPolicy | None):
    token = _ACTIVE_POLICY.set(policy)
    try:
        yield
    finally:
        _ACTIVE_POLICY.reset(token)


def current_environment_policy() -> EnvironmentPolicy | None:
    return _ACTIVE_POLICY.get()


@contextmanager
def active_environment_overrides(overrides: dict[str, str | None] | None):
    """Apply transcript/process environment modifiers to nested subprocesses."""
    token = _ACTIVE_OVERRIDES.set(dict(overrides) if overrides else None)
    try:
        yield
    finally:
        _ACTIVE_OVERRIDES.reset(token)


def current_environment_overrides() -> dict[str, str | None] | None:
    return _ACTIVE_OVERRIDES.get()


def resolve_executable(argv0: str, *, env: dict[str, str]) -> str:
    """Resolve a bare outer executable using the effective PATH."""
    if not argv0 or os.path.dirname(argv0):
        return argv0
    return shutil.which(argv0, path=env.get("PATH")) or argv0


def _selector_matches(selector: str, executable: str) -> tuple[int, str]:
    normalized = os.path.normcase(os.path.normpath(executable))
    selector = selector.strip()
    if selector.startswith("exact:"):
        wanted = os.path.normcase(os.path.normpath(selector[6:]))
        return (2, selector) if wanted == normalized else (0, "")
    family = PathStem(executable)
    wanted = selector.removeprefix("family:").lower()
    return (1, selector) if wanted == family else (0, "")


def PathStem(path: str) -> str:
    name = os.path.basename(path).lower()
    if name.endswith(".exe"):
        name = name[:-4]
    return name


def _deduplicate_path(entries: list[str], *, windows: bool) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for entry in entries:
        key = entry.casefold() if windows else entry
        if key not in seen:
            seen.add(key)
            result.append(entry)
    return result


def apply_environment_policy(
    env: dict[str, str],
    argv: list[str],
    *,
    policy: EnvironmentPolicy | None = None,
) -> tuple[list[str], dict[str, str]]:
    policy = policy or current_environment_policy()
    effective = dict(env)
    resolved = resolve_executable(argv[0], env=effective)
    if policy is None:
        return [resolved, *argv[1:]], effective

    selected: RuntimeEnvironmentBinding | None = None
    selected_rank = 0
    for binding in policy.bindings:
        rank, _ = _selector_matches(binding.selector, resolved)
        if rank > selected_rank:
            selected = binding
            selected_rank = rank

    profile = None
    mode = policy.mode
    if selected is not None:
        mode = selected.mode
        profile = next((item for item in policy.profiles if item.name == selected.profile), None)
    if mode not in {"inherit", "replace", "merge"}:
        raise RuntimeError(f"invalid environment mode: {mode}")
    if mode == "replace":
        effective = {}
    if profile is not None:
        effective.update(dict(profile.variables))
        path = effective.get("PATH", "").split(os.pathsep) if effective.get("PATH") else []
        windows = os.name == "nt" or sys.platform.startswith("win")
        effective["PATH"] = os.pathsep.join(
            _deduplicate_path(
                [*profile.path_prepend, *path, *profile.path_append],
                windows=windows,
            )
        )
    return [resolved, *argv[1:]], effective
