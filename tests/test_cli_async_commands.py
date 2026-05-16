from pathlib import Path
from types import SimpleNamespace

import pytest

from toas.cli_async_commands import (
    AsyncCommandDeps,
    backend_payload_from_config,
    build_deps,
    run_backend,
    run_cancel,
    run_step_async,
    run_watch,
)
from toas.rpc_client import RpcClientError


def _config(*, async_runs="enabled", streaming_mode="enabled", cancellation_mode="enabled"):
    runtime = SimpleNamespace(
        async_runs=async_runs,
        streaming_mode=streaming_mode,
        cancellation_mode=cancellation_mode,
    )
    managed = SimpleNamespace(command=("python",), cwd="", env=(("A", "B"),), health_url="", health_timeout_s=1.0)
    backend = SimpleNamespace(mode="managed-local", managed_local=managed)
    return SimpleNamespace(runtime=runtime, backend=backend)


def _deps(*, config=None, enabled=True, rpc=None, out=None, sleeps=None):
    out = out if out is not None else []
    sleeps = sleeps if sleeps is not None else []
    if config is None:
        config = _config()
    if rpc is None:
        rpc = lambda _op, _payload=None: {}
    return AsyncCommandDeps(
        load_operator_config_for_cwd=lambda: config,
        rpc_enabled_for_call=lambda: enabled,
        rpc_request=rpc,
        cwd_resolver=lambda: Path("/tmp"),
        print_fn=lambda *args, end="\n": out.append("".join(str(a) for a in args) + end),
        sleep_fn=lambda secs: sleeps.append(secs),
    )


def test_run_step_async_happy_path_prints_run_id_and_status():
    out = []
    deps = _deps(rpc=lambda _op, _payload=None: {"run_id": "r1", "status": "running"}, out=out)

    run_step_async(deps)

    assert out == ["run_id=r1 status=running\n"]


def test_run_step_async_rejects_disabled_policy():
    deps = _deps(config=_config(async_runs="disabled"))
    with pytest.raises(SystemExit, match="step --async disabled by runtime.async_runs policy"):
        run_step_async(deps)


def test_run_step_async_requires_rpc_enabled():
    deps = _deps(enabled=False)
    with pytest.raises(SystemExit, match="step --async requires daemon rpc mode"):
        run_step_async(deps)


def test_run_step_async_requires_non_empty_run_id():
    deps = _deps(rpc=lambda _op, _payload=None: {"status": "running"})
    with pytest.raises(SystemExit, match="step --async failed: missing run_id"):
        run_step_async(deps)


def test_run_watch_without_follow_prints_status_once():
    out = []
    seen = []

    def _rpc(op, payload=None):
        seen.append((op, dict(payload or {})))
        return {"status": "running", "next_offset": 5, "next_seq": 2}

    run_watch("r1", offset=0, follow=False, deps=_deps(rpc=_rpc, out=out))

    assert seen[0][0] == "watch"
    assert out == ["[run running] offset=5\n"]


def test_run_watch_returns_when_terminal_event_present_even_if_status_running():
    out = []

    def _rpc(_op, _payload=None):
        return {
            "status": "running",
            "next_offset": 0,
            "next_seq": 1,
            "events": [{"type": "llm_done", "payload": {"status": "succeeded"}}],
        }

    run_watch("r1", follow=True, deps=_deps(rpc=_rpc, out=out))
    assert out == []


def test_run_watch_rejects_unknown_event_kind():
    def _rpc(_op, _payload=None):
        return {
            "status": "running",
            "next_offset": 0,
            "next_seq": 1,
            "events": [{"type": "mystery_event", "payload": {}}],
        }

    with pytest.raises(ValueError, match="unknown event kind"):
        run_watch("r1", deps=_deps(rpc=_rpc))


def test_run_watch_ignores_non_list_events_container():
    out = []

    def _rpc(_op, _payload=None):
        return {"status": "running", "next_offset": 3, "next_seq": 0, "events": "oops"}

    run_watch("r1", deps=_deps(rpc=_rpc, out=out))
    assert out == ["[run running] offset=3\n"]


def test_run_watch_ignores_non_dict_event_items():
    out = []

    def _rpc(_op, _payload=None):
        return {"status": "running", "next_offset": 4, "next_seq": 1, "events": [None]}

    run_watch("r1", deps=_deps(rpc=_rpc, out=out))
    assert out == ["[run running] offset=4\n"]


def test_run_watch_follow_retries_and_sleeps_until_success():
    out = []
    sleeps = []
    calls = [{"status": "running", "next_offset": 0, "next_seq": 0}, {"status": "succeeded", "next_offset": 0, "next_seq": 0}]

    def _rpc(_op, _payload=None):
        return calls.pop(0)

    run_watch("r1", follow=True, deps=_deps(rpc=_rpc, out=out, sleeps=sleeps))

    assert out == []
    assert sleeps == [0.1]


def test_run_watch_prints_chunk_and_failed_status_with_error():
    out = []

    def _rpc(_op, _payload=None):
        return {"chunk": "hello", "status": "failed", "error": "boom", "next_offset": 5, "next_seq": 1}

    run_watch("r1", deps=_deps(rpc=_rpc, out=out))

    assert out == ["hello", "\n[run failed] boom\n"]


def test_run_watch_prints_failed_status_without_error():
    out = []

    def _rpc(_op, _payload=None):
        return {"status": "cancelled", "next_offset": 0, "next_seq": 0}

    run_watch("r1", deps=_deps(rpc=_rpc, out=out))

    assert out == ["\n[run cancelled]\n"]


def test_run_watch_rejects_disabled_policy():
    with pytest.raises(SystemExit, match="watch disabled by runtime.streaming_mode policy"):
        run_watch("r1", deps=_deps(config=_config(streaming_mode="disabled")))


def test_run_watch_requires_rpc_enabled():
    with pytest.raises(SystemExit, match="watch requires daemon rpc mode"):
        run_watch("r1", deps=_deps(enabled=False))


def test_run_cancel_happy_path_prints_status():
    out = []
    run_cancel("r1", _deps(rpc=lambda _op, _payload=None: {"status": "cancelling"}, out=out))
    assert out == ["run_id=r1 status=cancelling\n"]


def test_run_cancel_rejects_disabled_policy():
    with pytest.raises(SystemExit, match="cancel disabled by runtime.cancellation_mode policy"):
        run_cancel("r1", _deps(config=_config(cancellation_mode="disabled")))


def test_run_cancel_requires_rpc_enabled():
    with pytest.raises(SystemExit, match="cancel requires daemon rpc mode"):
        run_cancel("r1", _deps(enabled=False))


def test_backend_payload_from_config_uses_managed_settings_and_cwd_fallback():
    cfg = _config()
    payload = backend_payload_from_config(cfg, Path("/w"))
    assert payload["workdir"] == str(Path("/w"))
    assert payload["mode"] == "managed-local"
    assert payload["command"] == ["python"]
    assert payload["cwd"] == str(Path("/w"))
    assert payload["env"] == {"A": "B"}


def test_run_backend_happy_path_with_pid_and_detail():
    out = []

    def _rpc(_op, _payload=None):
        return {"mode": "managed-local", "status": "running", "pid": 42, "detail": "warm"}

    run_backend("status", _deps(rpc=_rpc, out=out))

    assert out == ["backend mode=managed-local status=running pid=42\n", "detail: warm\n"]


def test_run_backend_happy_path_without_pid():
    out = []

    def _rpc(_op, _payload=None):
        return {"mode": "managed-local", "status": "running"}

    run_backend("status", _deps(rpc=_rpc, out=out))

    assert out == ["backend mode=managed-local status=running\n"]


def test_run_backend_rejects_invalid_action():
    with pytest.raises(SystemExit, match=r"usage: toas backend \[start\|stop\|restart\|status\]"):
        run_backend("bad", _deps())


def test_run_backend_requires_rpc_enabled():
    with pytest.raises(SystemExit, match="backend lifecycle requires daemon rpc mode"):
        run_backend("status", _deps(enabled=False))


def test_rpc_request_or_exit_error_path_bubbles_as_system_exit_via_backend():
    def _rpc(_op, _payload=None):
        raise RpcClientError("down")

    with pytest.raises(SystemExit, match="backend status failed: down"):
        run_backend("status", _deps(rpc=_rpc))


def test_build_deps_wires_default_cwd_and_sleep(monkeypatch):
    marker = []

    monkeypatch.setattr(
        "toas.cli_async_commands.Path",
        SimpleNamespace(cwd=lambda: SimpleNamespace(resolve=lambda: Path("/r"))),
    )
    monkeypatch.setattr("toas.cli_async_commands.time.sleep", lambda secs: marker.append(secs))

    deps = build_deps(
        load_operator_config_for_cwd=lambda: _config(),
        rpc_enabled_for_call=lambda: True,
        rpc_request=lambda _op, _payload=None: {"status": "running"},
        print_fn=lambda *args, **kwargs: None,
    )

    assert str(deps.cwd_resolver()) == str(Path("/r"))
    deps.sleep_fn(0.1)
    assert marker == [0.1]
