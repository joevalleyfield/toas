from pathlib import Path
from types import SimpleNamespace
import types
import sys

import pytest

from toas.cli_async_commands import (
    AsyncCommandDeps,
    backend_payload_from_config,
    build_deps,
    run_backend,
    run_cancel,
    run_step_async,
    run_watch,
    _async_backend_mode,
    _strict_local_backend_guard_enabled,
    _start_async_step_local,
    _watch_async_step_local,
    _cancel_async_step_local,
)
from toas.rpc_client import RpcClientError


def _config(*, async_runs="enabled", streaming_mode="enabled", cancellation_mode="enabled"):
    runtime = SimpleNamespace(
        async_runs=async_runs,
        streaming_mode=streaming_mode,
        cancellation_mode=cancellation_mode,
        async_backend_mode="rpc",
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


def test_run_step_async_uses_envelope_status_when_present():
    out = []
    deps = _deps(
        rpc=lambda _op, _payload=None: {
            "run_id": "r1",
            "status": "running",
            "envelope": {
                "session_id": "r1",
                "activity_id": "r1",
                "event_id": 0,
                "kind": "accepted",
                "ts": "2026-05-16T00:00:00Z",
                "payload": {"status": "accepted"},
                "final": False,
                "cancel_of": None,
            },
        },
        out=out,
    )
    run_step_async(deps)
    assert out == ["run_id=r1 status=accepted\n"]


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


def test_run_step_async_local_backend_placeholder_rejects_when_strict_guard_enabled(monkeypatch):
    monkeypatch.setenv("TOAS_ASYNC_LOCAL_STRICT_GUARD", "1")
    cfg = _config()
    cfg.runtime.async_backend_mode = "local"
    deps = _deps(
        config=cfg,
        rpc=lambda _op, _payload=None: (_ for _ in ()).throw(AssertionError("rpc should not be called")),
    )
    with pytest.raises(SystemExit, match="step --async local backend not implemented yet"):
        run_step_async(deps)


def test_run_step_async_local_backend_falls_back_to_rpc_when_strict_guard_disabled(monkeypatch):
    monkeypatch.delenv("TOAS_ASYNC_LOCAL_STRICT_GUARD", raising=False)
    cfg = _config()
    cfg.runtime.async_backend_mode = "local"
    out = []
    monkeypatch.setattr(
        "toas.cli_async_commands._start_async_step_local",
        lambda _payload: {"run_id": "r1", "status": "running"},
    )
    run_step_async(_deps(config=cfg, out=out))
    assert out == ["run_id=r1 status=running\n"]


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


def test_run_watch_uses_envelopes_when_present() -> None:
    def _rpc(_op, _payload=None):
        return {
            "status": "running",
            "next_offset": 0,
            "next_seq": 1,
            "envelopes": [
                {
                    "session_id": "r1",
                    "activity_id": "r1",
                    "event_id": 1,
                    "kind": "llm_done",
                    "ts": "2026-05-16T00:00:00Z",
                    "payload": {"final": True},
                    "final": True,
                    "cancel_of": None,
                }
            ],
        }

    run_watch("r1", follow=True, deps=_deps(rpc=_rpc, out=[]))


def test_run_watch_envelopes_skip_non_dict_and_fallback_to_events() -> None:
    out = []

    def _rpc(_op, _payload=None):
        return {
            "status": "running",
            "next_offset": 2,
            "next_seq": 1,
            "envelopes": [None],
            "events": [{"type": "status", "payload": {}}],
        }

    run_watch("r1", deps=_deps(rpc=_rpc, out=out))
    assert out == ["[run running] offset=2\n"]


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


def test_run_watch_local_backend_placeholder_rejects_when_strict_guard_enabled(monkeypatch):
    monkeypatch.setenv("TOAS_ASYNC_LOCAL_STRICT_GUARD", "1")
    cfg = _config()
    cfg.runtime.async_backend_mode = "local"
    with pytest.raises(SystemExit, match="watch local backend not implemented yet"):
        run_watch("r1", deps=_deps(config=cfg, rpc=lambda *_args, **_kwargs: {}))


def test_run_watch_local_backend_falls_back_to_rpc_when_strict_guard_disabled(monkeypatch):
    monkeypatch.delenv("TOAS_ASYNC_LOCAL_STRICT_GUARD", raising=False)
    cfg = _config()
    cfg.runtime.async_backend_mode = "local"
    out = []
    monkeypatch.setattr(
        "toas.cli_async_commands._watch_async_step_local",
        lambda _payload: {"status": "running", "next_offset": 5, "next_seq": 0},
    )
    run_watch(
        "r1",
        deps=_deps(
            config=cfg,
            rpc=lambda _op, _payload=None: (_ for _ in ()).throw(AssertionError("rpc should not be called")),
            out=out,
        ),
    )
    assert out == ["[run running] offset=5\n"]


def test_run_cancel_happy_path_prints_status():
    out = []
    run_cancel("r1", _deps(rpc=lambda _op, _payload=None: {"status": "cancelling"}, out=out))
    assert out == ["run_id=r1 status=cancelling\n"]


def test_run_cancel_prints_terminal_cancelled_status():
    out = []
    run_cancel("r1", _deps(rpc=lambda _op, _payload=None: {"status": "cancelled"}, out=out))
    assert out == ["run_id=r1 status=cancelled\n"]


def test_run_cancel_uses_envelope_status_when_present():
    out = []
    run_cancel(
        "r1",
        _deps(
            rpc=lambda _op, _payload=None: {
                "status": "cancelling",
                "envelope": {
                    "session_id": "r1",
                    "activity_id": "r1",
                    "event_id": 0,
                    "kind": "cancel",
                    "ts": "2026-05-16T00:00:00Z",
                    "payload": {"status": "queued"},
                    "final": False,
                    "cancel_of": "r1",
                },
            },
            out=out,
        ),
    )
    assert out == ["run_id=r1 status=queued\n"]


def test_run_cancel_rejects_disabled_policy():
    with pytest.raises(SystemExit, match="cancel disabled by runtime.cancellation_mode policy"):
        run_cancel("r1", _deps(config=_config(cancellation_mode="disabled")))


def test_run_cancel_requires_rpc_enabled():
    with pytest.raises(SystemExit, match="cancel requires daemon rpc mode"):
        run_cancel("r1", _deps(enabled=False))


def test_run_cancel_local_backend_placeholder_rejects_when_strict_guard_enabled(monkeypatch):
    monkeypatch.setenv("TOAS_ASYNC_LOCAL_STRICT_GUARD", "1")
    cfg = _config()
    cfg.runtime.async_backend_mode = "local"
    with pytest.raises(SystemExit, match="cancel local backend not implemented yet"):
        run_cancel("r1", _deps(config=cfg, rpc=lambda *_args, **_kwargs: {}))


def test_run_cancel_local_backend_falls_back_to_rpc_when_strict_guard_disabled(monkeypatch):
    monkeypatch.delenv("TOAS_ASYNC_LOCAL_STRICT_GUARD", raising=False)
    cfg = _config()
    cfg.runtime.async_backend_mode = "local"
    out = []
    monkeypatch.setattr(
        "toas.cli_async_commands._cancel_async_step_local",
        lambda _payload: {"status": "cancelling"},
    )
    run_cancel(
        "r1",
        _deps(config=cfg, rpc=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("rpc should not be called")), out=out),
    )
    assert out == ["run_id=r1 status=cancelling\n"]


def test_run_watch_follow_exits_on_terminal_cancelled_status():
    out: list[str] = []
    sleeps: list[float] = []
    calls = [
        {"status": "cancelling", "next_offset": 0, "next_seq": 0},
        {"status": "cancelled", "next_offset": 0, "next_seq": 0},
    ]

    def _rpc(_op, _payload=None):
        return calls.pop(0)

    run_watch("r1", follow=True, deps=_deps(rpc=_rpc, out=out, sleeps=sleeps))

    assert out == ["\n[run cancelled]\n"]
    assert sleeps == [0.1]


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


def test_run_backend_prefers_envelope_status_and_detail():
    out = []

    def _rpc(_op, _payload=None):
        return {
            "mode": "managed-local",
            "status": "running",
            "pid": 42,
            "detail": "legacy",
            "envelope": {
                "session_id": "daemon-status",
                "activity_id": "daemon-status",
                "event_id": 0,
                "kind": "status",
                "ts": "2026-05-16T00:00:00Z",
                "payload": {"status": "accepted", "detail": "from-envelope"},
                "final": False,
                "cancel_of": None,
            },
        }

    run_backend("status", _deps(rpc=_rpc, out=out))

    assert out == ["backend mode=managed-local status=accepted pid=42\n", "detail: from-envelope\n"]


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


def test_async_backend_mode_defaults_to_rpc():
    cfg = _config()
    assert _async_backend_mode(cfg) == "rpc"


def test_async_backend_mode_uses_config_when_present():
    cfg = _config()
    cfg.runtime.async_backend_mode = "local"
    assert _async_backend_mode(cfg) == "local"


def test_async_backend_mode_env_overrides_config(monkeypatch):
    cfg = _config()
    cfg.runtime.async_backend_mode = "rpc"
    monkeypatch.setenv("TOAS_ASYNC_BACKEND_MODE", "local")
    assert _async_backend_mode(cfg) == "local"


def test_strict_local_backend_guard_enabled_flag(monkeypatch):
    monkeypatch.delenv("TOAS_ASYNC_LOCAL_STRICT_GUARD", raising=False)
    assert _strict_local_backend_guard_enabled() is False
    monkeypatch.setenv("TOAS_ASYNC_LOCAL_STRICT_GUARD", "1")
    assert _strict_local_backend_guard_enabled() is True


def test_start_async_step_local_wires_facade_calls(monkeypatch):
    calls = {}

    facade_async = types.ModuleType("toas.daemon.facade_async_ops")
    facade_helpers = types.ModuleType("toas.daemon.facade_helpers")

    def _start_async_step(**kwargs):
        calls["kwargs"] = kwargs
        return {"run_id": "loc1", "status": "running"}

    facade_async.start_async_step = _start_async_step
    facade_async.stream_process_output = lambda **_kw: None
    facade_async.wait_for_process = lambda **_kw: None
    facade_helpers.normalize_workdir = lambda path: str(path)
    facade_helpers.thinking_stream_enabled = lambda _workdir: True
    facade_helpers.prompt_progress_stream_enabled = lambda _workdir: False
    facade_helpers.write_run_event = lambda _w, _r, _s, _d=None: None

    monkeypatch.setitem(sys.modules, "toas.daemon.facade_async_ops", facade_async)
    monkeypatch.setitem(sys.modules, "toas.daemon.facade_helpers", facade_helpers)

    out = _start_async_step_local({"workdir": "/tmp"})
    assert out == {"run_id": "loc1", "status": "running"}
    assert calls["kwargs"]["payload"] == {"workdir": "/tmp"}


def test_watch_async_step_local_wires_facade_call(monkeypatch):
    facade_async = types.ModuleType("toas.daemon.facade_async_ops")
    facade_async.watch_async_step_op = lambda payload: {"status": "running", "next_offset": payload["offset"], "next_seq": 0}
    monkeypatch.setitem(sys.modules, "toas.daemon.facade_async_ops", facade_async)

    out = _watch_async_step_local({"run_id": "r1", "offset": 2, "since_seq": 0, "workdir": "/tmp"})
    assert out["status"] == "running"
    assert out["next_offset"] == 2


def test_cancel_async_step_local_wires_facade_call(monkeypatch):
    facade_async = types.ModuleType("toas.daemon.facade_async_ops")
    facade_async.cancel_async_step_op = lambda payload: {"status": "cancelling", "run_id": payload["run_id"]}
    monkeypatch.setitem(sys.modules, "toas.daemon.facade_async_ops", facade_async)

    out = _cancel_async_step_local({"run_id": "r1", "workdir": "/tmp"})
    assert out["status"] == "cancelling"
    assert out["run_id"] == "r1"
