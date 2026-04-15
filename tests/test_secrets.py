import sys
import types

import pytest

from toas.secrets import resolve_secret


def test_resolve_secret_env(monkeypatch):
    monkeypatch.setenv("TEST_KEY", "abc")
    assert resolve_secret(source="env", ref="TEST_KEY", default="x") == "abc"


def test_resolve_secret_env_default(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    assert resolve_secret(source="env", ref="MISSING_KEY", default="x") == "x"


def test_resolve_secret_keyring_missing_package(monkeypatch):
    monkeypatch.setitem(sys.modules, "keyring", None)
    with pytest.raises(RuntimeError, match="keyring provider requested"):
        resolve_secret(source="keyring", ref="svc:user")


def test_resolve_secret_keyring_success(monkeypatch):
    fake = types.SimpleNamespace(get_password=lambda service, username: "sekrit")
    monkeypatch.setitem(sys.modules, "keyring", fake)
    assert resolve_secret(source="keyring", ref="svc:user") == "sekrit"


def test_resolve_secret_keyring_not_found(monkeypatch):
    fake = types.SimpleNamespace(get_password=lambda service, username: None)
    monkeypatch.setitem(sys.modules, "keyring", fake)
    with pytest.raises(RuntimeError, match="keyring secret not found"):
        resolve_secret(source="keyring", ref="svc:user")


def test_resolve_secret_env_defaults_ref_when_blank(monkeypatch):
    monkeypatch.setenv("TOAS_LLM_API_KEY", "default-key")
    assert resolve_secret(source="env", ref="   ", default="x") == "default-key"


def test_resolve_secret_keyring_rejects_missing_or_malformed_ref():
    with pytest.raises(RuntimeError, match="service:username"):
        resolve_secret(source="keyring", ref="")
    with pytest.raises(RuntimeError, match="service:username"):
        resolve_secret(source="keyring", ref="svcuser")
    with pytest.raises(RuntimeError, match="service:username"):
        resolve_secret(source="keyring", ref="svc:")


def test_resolve_secret_unknown_source_raises():
    with pytest.raises(RuntimeError, match="unknown secret source"):
        resolve_secret(source="vault", ref="k")
