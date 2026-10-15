"""Effective shell selection for an operator step or standalone tool call."""

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from ..config import config_from_discovered_paths

_SHELL_RUNTIME: ContextVar[tuple[str, ...] | None] = ContextVar("shell_runtime", default=None)


@contextmanager
def active_shell_runtime(runtime: tuple[str, ...]):
    token = _SHELL_RUNTIME.set(runtime)
    try:
        yield
    finally:
        _SHELL_RUNTIME.reset(token)


def configured_shell_runtime(workdir: Path) -> tuple[str, ...]:
    selected = _SHELL_RUNTIME.get()
    if selected is not None:
        return selected
    configured = config_from_discovered_paths(workdir=workdir).runtime.shell_runtime
    if not isinstance(configured, (tuple, list)) or not all(isinstance(part, str) and part for part in configured):
        raise RuntimeError("runtime.shell_runtime must be an argv list (empty selects automatic discovery)")
    return tuple(configured)
