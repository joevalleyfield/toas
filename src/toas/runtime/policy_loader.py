"""Discovery and loading for user/workspace executable grant policy modules."""

from __future__ import annotations

import importlib.util
import inspect
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .executable_grants import ExecutableGrantPolicy

DEFAULT_POLICY_MODULE_PATH = ".toas/policy.py"


def resolve_policy_path(
    workspace_root: Path | str | None = None,
    *,
    configured_path: str | None = None,
) -> Path | None:
    """Resolve the candidate policy module path, checking for existence."""
    base = Path(workspace_root or ".").resolve()
    target_rel = configured_path or DEFAULT_POLICY_MODULE_PATH
    candidate = Path(target_rel)
    if not candidate.is_absolute():
        candidate = (base / candidate).resolve()

    if candidate.is_file():
        return candidate

    if configured_path is not None and configured_path != DEFAULT_POLICY_MODULE_PATH:
        raise FileNotFoundError(f"configured executable policy module not found: {candidate}")

    return None


def load_executable_policy(
    path: Path | str,
    *,
    config: Any = None,
) -> ExecutableGrantPolicy:
    """Load and instantiate an ExecutableGrantPolicy from a Python module."""
    file_path = Path(path).resolve()
    if not file_path.is_file():
        raise FileNotFoundError(f"executable policy module not found: {file_path}")

    module_name = f"_toas_policy_{abs(hash(str(file_path)))}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load policy module spec from {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as err:
        raise RuntimeError(f"error evaluating executable policy module {file_path}: {err}") from err

    # 1. Factory function: get_policy / GET_POLICY
    for attr in ("get_policy", "GET_POLICY"):
        if hasattr(module, attr):
            factory = getattr(module, attr)
            if not callable(factory):
                raise TypeError(f"'{attr}' in {file_path} must be callable")
            try:
                sig = inspect.signature(factory)
                policy = factory(config=config) if "config" in sig.parameters else factory()
            except Exception as err:
                raise RuntimeError(f"error calling {attr}() in {file_path}: {err}") from err

            if not isinstance(policy, ExecutableGrantPolicy):
                raise TypeError(
                    f"{attr}() in {file_path} must return ExecutableGrantPolicy, got {type(policy).__name__}"
                )
            return policy

    # 2. Explicit policy instance: policy / POLICY
    for attr in ("policy", "POLICY"):
        if hasattr(module, attr):
            policy = getattr(module, attr)
            if not isinstance(policy, ExecutableGrantPolicy):
                raise TypeError(
                    f"'{attr}' in {file_path} must be an ExecutableGrantPolicy instance, got {type(policy).__name__}"
                )
            return policy

    # 3. Prefix matchers mapping: prefix_matchers / PREFIX_MATCHERS
    for attr in ("prefix_matchers", "PREFIX_MATCHERS"):
        if hasattr(module, attr):
            matchers = getattr(module, attr)
            if not isinstance(matchers, Mapping):
                raise TypeError(
                    f"'{attr}' in {file_path} must be a Mapping[str, Sequence[Matcher]], got {type(matchers).__name__}"
                )
            default = getattr(module, "default", getattr(module, "DEFAULT", False))
            return ExecutableGrantPolicy(default=default, prefix_matchers=matchers)

    raise RuntimeError(
        f"executable policy module {file_path} must export 'policy', 'get_policy', or 'prefix_matchers'"
    )


def resolve_executable_grant_policy(
    workspace_root: Path | str | None = None,
    *,
    config: Any = None,
) -> ExecutableGrantPolicy | None:
    """Resolve and load the workspace policy if one exists, else None."""
    configured_path = None
    if config is not None and hasattr(config, "runtime"):
        configured_path = getattr(config.runtime, "policy_module", None)

    policy_file = resolve_policy_path(workspace_root, configured_path=configured_path)
    if policy_file is None:
        return None

    return load_executable_policy(policy_file, config=config)
