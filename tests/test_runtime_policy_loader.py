"""Tests for user executable policy discovery and module loader."""

from __future__ import annotations

import pytest

from toas.config import OperatorConfig, RuntimePolicy
from toas.runtime.executable_grants import ExecutableGrantPolicy
from toas.runtime.policy_loader import (
    load_executable_policy,
    resolve_executable_grant_policy,
    resolve_policy_path,
)


def test_resolve_policy_path_default_and_configured(tmp_path):
    # Default absent
    assert resolve_policy_path(tmp_path) is None

    # Default present
    toas_dir = tmp_path / ".toas"
    toas_dir.mkdir()
    policy_file = toas_dir / "policy.py"
    policy_file.write_text("# empty\n", encoding="utf-8")
    assert resolve_policy_path(tmp_path) == policy_file.resolve()

    # Configured custom relative path present
    custom = tmp_path / "custom_policy.py"
    custom.write_text("# custom\n", encoding="utf-8")
    assert resolve_policy_path(tmp_path, configured_path="custom_policy.py") == custom.resolve()

    # Configured custom missing raises FileNotFoundError
    with pytest.raises(FileNotFoundError, match="configured executable policy module not found"):
        resolve_policy_path(tmp_path, configured_path="missing.py")


def test_load_executable_policy_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="executable policy module not found"):
        load_executable_policy(tmp_path / "nonexistent.py")


def test_load_executable_policy_syntax_error(tmp_path):
    p = tmp_path / "broken.py"
    p.write_text("def syntax_error(\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="error evaluating executable policy module"):
        load_executable_policy(p)


def test_load_executable_policy_with_explicit_policy_instance(tmp_path):
    p = tmp_path / "explicit.py"
    p.write_text(
        "from toas.runtime.executable_grants import ExecutableGrantPolicy\n"
        "policy = ExecutableGrantPolicy(default=True)\n",
        encoding="utf-8",
    )
    loaded = load_executable_policy(p)
    assert isinstance(loaded, ExecutableGrantPolicy)
    assert loaded.default is True


def test_load_executable_policy_with_policy_uppercase(tmp_path):
    p = tmp_path / "uppercase.py"
    p.write_text(
        "from toas.runtime.executable_grants import ExecutableGrantPolicy\n"
        "POLICY = ExecutableGrantPolicy(default=True)\n",
        encoding="utf-8",
    )
    loaded = load_executable_policy(p)
    assert isinstance(loaded, ExecutableGrantPolicy)
    assert loaded.default is True


def test_load_executable_policy_with_invalid_policy_type(tmp_path):
    p = tmp_path / "wrong_type.py"
    p.write_text("policy = 'not_a_policy'\n", encoding="utf-8")
    with pytest.raises(TypeError, match="'policy'.*must be an ExecutableGrantPolicy instance"):
        load_executable_policy(p)


def test_load_executable_policy_with_get_policy_factory(tmp_path):
    p = tmp_path / "factory.py"
    p.write_text(
        "from toas.runtime.executable_grants import ExecutableGrantPolicy\n"
        "def get_policy(config=None):\n"
        "    return ExecutableGrantPolicy(default=True)\n",
        encoding="utf-8",
    )
    loaded = load_executable_policy(p, config=None)
    assert isinstance(loaded, ExecutableGrantPolicy)
    assert loaded.default is True

    # Factory without config param
    p2 = tmp_path / "factory_no_args.py"
    p2.write_text(
        "from toas.runtime.executable_grants import ExecutableGrantPolicy\n"
        "def GET_POLICY():\n"
        "    return ExecutableGrantPolicy(default=False)\n",
        encoding="utf-8",
    )
    loaded2 = load_executable_policy(p2)
    assert loaded2.default is False


def test_load_executable_policy_factory_errors(tmp_path):
    # Not callable
    p = tmp_path / "factory_not_callable.py"
    p.write_text("get_policy = 123\n", encoding="utf-8")
    with pytest.raises(TypeError, match="'get_policy'.*must be callable"):
        load_executable_policy(p)

    # Factory raises
    p2 = tmp_path / "factory_raises.py"
    p2.write_text("def get_policy(): raise ValueError('boom')\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="error calling get_policy"):
        load_executable_policy(p2)

    # Factory returns wrong type
    p3 = tmp_path / "factory_wrong_return.py"
    p3.write_text("def get_policy(): return 'not_policy'\n", encoding="utf-8")
    with pytest.raises(TypeError, match="get_policy.*must return ExecutableGrantPolicy"):
        load_executable_policy(p3)


def test_load_executable_policy_with_prefix_matchers_mapping(tmp_path):
    p = tmp_path / "mapping.py"
    p.write_text(
        "from toas.runtime.matchers import allow_all\n"
        "DEFAULT = True\n"
        "PREFIX_MATCHERS = {'git': (allow_all(),)}\n",
        encoding="utf-8",
    )
    loaded = load_executable_policy(p)
    assert isinstance(loaded, ExecutableGrantPolicy)
    assert loaded.default is True
    assert "git" in loaded.prefix_matchers

    # Lowercase variant
    p2 = tmp_path / "mapping_lower.py"
    p2.write_text(
        "prefix_matchers = {'uv': ()}\n",
        encoding="utf-8",
    )
    loaded2 = load_executable_policy(p2)
    assert loaded2.default is False
    assert "uv" in loaded2.prefix_matchers


def test_load_executable_policy_with_invalid_prefix_matchers_type(tmp_path):
    p = tmp_path / "bad_mapping.py"
    p.write_text("prefix_matchers = [1, 2, 3]\n", encoding="utf-8")
    with pytest.raises(TypeError, match="'prefix_matchers'.*must be a Mapping"):
        load_executable_policy(p)


def test_load_executable_policy_missing_exports(tmp_path):
    p = tmp_path / "empty.py"
    p.write_text("x = 42\n", encoding="utf-8")
    with pytest.raises(
        RuntimeError, match="must export 'policy', 'get_policy', or 'prefix_matchers'"
    ):
        load_executable_policy(p)


def test_load_executable_policy_spec_failure(tmp_path, monkeypatch):
    import importlib.util

    p = tmp_path / "spec_fail.py"
    p.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *args, **kwargs: None)
    with pytest.raises(RuntimeError, match="failed to load policy module spec"):
        load_executable_policy(p)


def test_resolve_executable_grant_policy_integration(tmp_path):
    # No policy file -> None
    assert resolve_executable_grant_policy(tmp_path) is None

    # Default policy file exists
    toas_dir = tmp_path / ".toas"
    toas_dir.mkdir()
    policy_file = toas_dir / "policy.py"
    policy_file.write_text(
        "from toas.runtime.executable_grants import ExecutableGrantPolicy\n"
        "policy = ExecutableGrantPolicy(default=True)\n",
        encoding="utf-8",
    )
    resolved = resolve_executable_grant_policy(tmp_path)
    assert resolved is not None
    assert resolved.default is True

    # Custom configured path in config
    cfg = OperatorConfig(runtime=RuntimePolicy(policy_module="my_policy.py"))
    custom = tmp_path / "my_policy.py"
    custom.write_text(
        "from toas.runtime.executable_grants import ExecutableGrantPolicy\n"
        "policy = ExecutableGrantPolicy(default=False)\n",
        encoding="utf-8",
    )
    resolved_custom = resolve_executable_grant_policy(tmp_path, config=cfg)
    assert resolved_custom is not None
    assert resolved_custom.default is False


def test_policy_default_rejects_truthy_non_boolean_values(tmp_path):
    policy_file = tmp_path / "policy.py"
    policy_file.write_text('default = "false"\nprefix_matchers = {}\n', encoding="utf-8")
    with pytest.raises(TypeError, match="executable grant default must be bool"):
        load_executable_policy(policy_file)

    policy_file.write_text(
        "from toas.runtime.executable_grants import ExecutableGrantPolicy\n"
        'policy = ExecutableGrantPolicy(default="false")\n', encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="executable grant default must be bool"):
        load_executable_policy(policy_file)
