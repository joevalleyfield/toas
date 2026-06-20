import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from toas.cli_async_commands import (
    AsyncCommandDeps,
    _async_backend_mode,
    _cancel_async_step,
    _start_async_step,
    _strict_local_backend_guard_enabled,
    _watch_async_step,
    backend_payload_from_config,
    build_deps,
    run_backend,
    run_cancel,
    run_step_async,
    run_watch,
)
from toas.rpc_client import RpcClientError
from toas.runtime.session_host_state import SessionHostRecord


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
        resolve_session_host_record=lambda _cwd: None,
        clear_session_host_record=lambda _cwd: None,
        ensure_session_host_record=lambda _cwd: None,
        owner_kind="shell",
        owner_id="",
    )


def test_run_step_async_happy_path_prints_run_id_and_status():
    out = []
    deps = _deps(rpc=lambda _op, _payload=None: {"run_id": "r1", "status": "running"}, out=out)

    run_step_async(deps)

    assert out == ["run_id=r1 status=running backend=rpc\n"]


def test_run_step_async_includes_session_path_override_in_payload():
    seen_payload = {}

    def _rpc(_op, payload=None):
        seen_payload.update(payload or {})
        return {"run_id": "r1", "status": "running"}

    deps = _deps(rpc=_rpc, out=[])
    run_step_async(deps, session_path=".toas/session-docs-keeper.md")
    assert seen_payload["session_path"] == ".toas/session-docs-keeper.md"


def test_run_step_async_includes_host_diagnostic_when_active_host_present():
    out = []
    host = SessionHostRecord(
        host_id="host-1",
        pid=1,
        owner_pid=1,
        started_at=0.0,
        transport="stdio",
        endpoint="pipe://stdio",
    )
    deps = _deps(rpc=lambda _op, _payload=None: {"run_id": "r1", "status": "running"}, out=out)
    deps = AsyncCommandDeps(
        **{**deps.__dict__, "resolve_session_host_record": lambda _cwd: host},  # type: ignore[arg-type]
    )
    # isolate diagnostic behavior from environment pid liveness checks
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("toas.cli_async_commands.record_is_stale", lambda _rec: False)
    run_step_async(deps)
    monkeypatch.undo()
    assert out == ["run_id=r1 status=running backend=rpc host=host-1\n"]


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
    assert out == ["run_id=r1 status=accepted backend=rpc\n"]


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
        "toas.cli_async_commands._start_async_step",
        lambda _payload: {"run_id": "r1", "status": "running"},
    )
    run_step_async(_deps(config=cfg, out=out))
    assert out == ["run_id=r1 status=running backend=local\n"]


def test_run_step_async_local_backend_ensures_host_when_missing():
    out = []
    host = SessionHostRecord(
        host_id="ensured-1",
        pid=1,
        owner_pid=1,
        started_at=0.0,
        transport="stdio",
        endpoint="pipe://stdio",
    )
    seen = {}
    cfg = _config()
    cfg.runtime.async_backend_mode = "local"
    deps = _deps(
        config=cfg,
        rpc=lambda _op, _payload=None: (_ for _ in ()).throw(AssertionError("rpc should not be called")),
        out=out,
    )
    deps = AsyncCommandDeps(
        **{
            **deps.__dict__,
            "ensure_session_host_record": lambda _cwd: host,
        },  # type: ignore[arg-type]
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("toas.cli_async_commands.record_is_stale", lambda _rec: False)
    def _start_local(payload):
        seen["payload"] = dict(payload)
        return {"run_id": "r1", "status": "running"}

    monkeypatch.setattr("toas.cli_async_commands._start_async_step", _start_local)
    run_step_async(deps)
    monkeypatch.undo()
    assert seen["payload"]["session_host_id"] == "ensured-1"
    assert out == ["run_id=r1 status=running backend=local host=ensured-1\n"]


def test_run_step_async_shell_refuses_editor_owned_host():
    host = SessionHostRecord(
        host_id="h-editor",
        pid=1,
        owner_pid=1,
        owner_kind="editor",
        owner_id="vim-1",
        started_at=0.0,
        transport="stdio",
        endpoint="pipe://stdio",
    )
    cfg = _config()
    cfg.runtime.async_backend_mode = "local"
    deps = _deps(config=cfg)
    deps = AsyncCommandDeps(
        **{
            **deps.__dict__,
            "resolve_session_host_record": lambda _cwd: host,
            "owner_kind": "shell",
        },  # type: ignore[arg-type]
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("toas.cli_async_commands.record_is_stale", lambda _rec: False)
    with pytest.raises(SystemExit, match="editor-owned"):
        run_step_async(deps)
    monkeypatch.undo()


def test_run_watch_without_follow_prints_status_once():
    out = []
    seen = []

    def _rpc(op, payload=None):
        seen.append((op, dict(payload or {})))
        return {"status": "running", "next_offset": 5, "next_seq": 2}

    run_watch("r1", offset=0, follow=False, deps=_deps(rpc=_rpc, out=out))

    assert seen[0][0] == "watch"
    assert out == ["[run running] offset=5 backend=rpc\n"]


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


def test_run_watch_envelope_payload_lane_phase_survive_event_normalization() -> None:
    out = []
    seen = {}

    def _rpc(_op, _payload=None):
        return {
            "status": "running",
            "next_offset": 2,
            "next_seq": 1,
            "envelopes": [
                {
                    "session_id": "r1",
                    "activity_id": "r1",
                    "event_id": 1,
                    "kind": "llm_reasoning",
                    "ts": "2026-05-16T00:00:00Z",
                    "payload": {"lane": "llm_reasoning", "phase": "delta", "text": "think"},
                    "final": False,
                    "cancel_of": None,
                }
            ],
        }

    def _event_policy(kind):
        seen["kind"] = kind
        return None

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("toas.cli_async_commands.event_policy", _event_policy)
    run_watch("r1", deps=_deps(rpc=_rpc, out=out))
    monkeypatch.undo()
    assert seen["kind"] == "llm_reasoning"
    assert out == ["think", "[run running] offset=2 backend=rpc\n"]


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
    assert out == ["[run running] offset=2 backend=rpc\n"]


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
    assert out == ["[run running] offset=3 backend=rpc\n"]


def test_run_watch_ignores_non_dict_event_items():
    out = []

    def _rpc(_op, _payload=None):
        return {"status": "running", "next_offset": 4, "next_seq": 1, "events": [None]}

    run_watch("r1", deps=_deps(rpc=_rpc, out=out))
    assert out == ["[run running] offset=4 backend=rpc\n"]


def test_run_watch_follow_retries_and_sleeps_until_success():
    out = []
    sleeps = []
    calls = [{"status": "running", "next_offset": 0, "next_seq": 0}, {"status": "succeeded", "next_offset": 0, "next_seq": 0}]

    def _rpc(_op, _payload=None):
        return calls.pop(0)

    run_watch("r1", follow=True, deps=_deps(rpc=_rpc, out=out, sleeps=sleeps))

    assert out == []
    assert sleeps == [0.1]


def test_run_watch_prints_event_text_and_failed_status_with_error():
    out = []

    def _rpc(_op, _payload=None):
        return {
            "status": "failed",
            "error": "boom",
            "next_offset": 5,
            "next_seq": 1,
            "events": [{"type": "tool_progress", "phase": "delta", "payload": {"text": "hello"}}],
        }

    run_watch("r1", deps=_deps(rpc=_rpc, out=out))

    assert out == ["hello", "\n[run failed] boom\n"]


def test_run_watch_ignores_legacy_chunk_without_semantic_events():
    out = []

    def _rpc(_op, _payload=None):
        return {"chunk": "legacy", "status": "failed", "error": "boom", "next_offset": 5, "next_seq": 1}

    run_watch("r1", deps=_deps(rpc=_rpc, out=out))

    assert out == ["\n[run failed] boom\n"]


def test_run_watch_prefers_semantic_event_text_over_legacy_chunk_when_both_present():
    out = []

    def _rpc(_op, _payload=None):
        return {
            "chunk": "legacy-chunk-ignored",
            "status": "running",
            "next_offset": 5,
            "next_seq": 1,
            "events": [{"type": "llm_delta", "phase": "delta", "payload": {"text": "semantic"}}],
        }

    run_watch("r1", deps=_deps(rpc=_rpc, out=out))

    assert out == ["semantic", "[run running] offset=5 backend=rpc\n"]


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
        "toas.cli_async_commands._watch_async_step",
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
    assert out == ["[run running] offset=5 backend=local\n"]


def test_run_cancel_happy_path_prints_status():
    out = []
    run_cancel("r1", _deps(rpc=lambda _op, _payload=None: {"status": "cancelling"}, out=out))
    assert out == ["run_id=r1 status=cancelling backend=rpc\n"]


def test_run_cancel_includes_host_diagnostic_when_active_host_present():
    out = []
    host = SessionHostRecord(
        host_id="host-2",
        pid=1,
        owner_pid=1,
        started_at=0.0,
        transport="stdio",
        endpoint="pipe://stdio",
    )
    deps = _deps(rpc=lambda _op, _payload=None: {"status": "cancelling"}, out=out)
    deps = AsyncCommandDeps(
        **{**deps.__dict__, "resolve_session_host_record": lambda _cwd: host},  # type: ignore[arg-type]
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("toas.cli_async_commands.record_is_stale", lambda _rec: False)
    run_cancel("r1", deps)
    monkeypatch.undo()
    assert out == ["run_id=r1 status=cancelling backend=rpc host=host-2\n"]


def test_run_cancel_prints_terminal_cancelled_status():
    out = []
    run_cancel("r1", _deps(rpc=lambda _op, _payload=None: {"status": "cancelled"}, out=out))
    assert out == ["run_id=r1 status=cancelled backend=rpc\n"]


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
    assert out == ["run_id=r1 status=queued backend=rpc\n"]


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
        "toas.cli_async_commands._cancel_async_step",
        lambda _payload: {"status": "cancelling"},
    )
    run_cancel(
        "r1",
        _deps(config=cfg, rpc=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("rpc should not be called")), out=out),
    )
    assert out == ["run_id=r1 status=cancelling backend=local\n"]


def test_run_step_async_clears_stale_session_host_record():
    out = []
    host = SessionHostRecord(
        host_id="stale-host",
        pid=1,
        owner_pid=1,
        started_at=0.0,
        transport="stdio",
        endpoint="pipe://stdio",
    )
    cleared = []
    deps = _deps(rpc=lambda _op, _payload=None: {"run_id": "r1", "status": "running"}, out=out)
    deps = AsyncCommandDeps(
        **{
            **deps.__dict__,
            "resolve_session_host_record": lambda _cwd: host,
            "clear_session_host_record": lambda cwd: cleared.append(str(cwd)),
        },  # type: ignore[arg-type]
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("toas.cli_async_commands.record_is_stale", lambda _rec: True)
    run_step_async(deps)
    monkeypatch.undo()
    assert cleared == ["/tmp"]
    assert out == ["run_id=r1 status=running backend=rpc\n"]


def test_run_step_async_clears_stale_ensured_session_host_record():
    out = []
    host = SessionHostRecord(
        host_id="stale-ensured",
        pid=1,
        owner_pid=1,
        started_at=0.0,
        transport="stdio",
        endpoint="pipe://stdio",
    )
    cleared = []
    cfg = _config()
    cfg.runtime.async_backend_mode = "local"
    deps = _deps(config=cfg, out=out)
    deps = AsyncCommandDeps(
        **{
            **deps.__dict__,
            "ensure_session_host_record": lambda _cwd: host,
            "clear_session_host_record": lambda cwd: cleared.append(str(cwd)),
        },  # type: ignore[arg-type]
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("toas.cli_async_commands.record_is_stale", lambda _rec: True)
    monkeypatch.setattr(
        "toas.cli_async_commands._start_async_step",
        lambda _payload: {"run_id": "r1", "status": "running"},
    )
    run_step_async(deps)
    monkeypatch.undo()
    assert cleared == ["/tmp"]
    assert out == ["run_id=r1 status=running backend=local\n"]


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


def test_run_backend_local_path_when_rpc_disabled():
    out = []
    cfg = _config()
    cfg.backend.mode = "external"
    run_backend("status", _deps(enabled=False, config=cfg, out=out))
    assert out == ["backend mode=external status=external\n"]


def test_rpc_request_or_exit_error_path_bubbles_as_system_exit_via_backend():
    def _rpc(_op, _payload=None):
        raise RpcClientError("down")

    with pytest.raises(SystemExit, match="backend status failed: down"):
        run_backend("status", _deps(rpc=_rpc))


def test_build_deps_wires_default_cwd_and_sleep(monkeypatch, tmp_path):
    marker = []

    monkeypatch.setattr(
        "toas.cli_async_commands.Path",
        SimpleNamespace(cwd=lambda: SimpleNamespace(resolve=lambda: tmp_path)),
    )
    monkeypatch.setattr("toas.cli_async_commands.time.sleep", lambda secs: marker.append(secs))

    deps = build_deps(
        load_operator_config_for_cwd=lambda: _config(),
        rpc_enabled_for_call=lambda: True,
        rpc_request=lambda _op, _payload=None: {"status": "running"},
        print_fn=lambda *args, **kwargs: None,
    )

    assert str(deps.cwd_resolver()) == str(tmp_path)
    deps.sleep_fn(0.1)
    assert marker == [0.1]
    workdir = tmp_path
    assert deps.resolve_session_host_record(workdir) is None
    deps.clear_session_host_record(workdir)
    host = deps.ensure_session_host_record(workdir)
    assert host is not None
    assert host.host_id.startswith("h-")


def test_async_backend_mode_defaults_to_local(monkeypatch):
    monkeypatch.delenv("TOAS_ASYNC_BACKEND_MODE", raising=False)
    cfg = SimpleNamespace(runtime=SimpleNamespace())
    assert _async_backend_mode(cfg) == "local"


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


def test_start_async_step_uses_runtime_adapter(monkeypatch):
    calls = {}

    runtime_adapter = types.ModuleType("toas.runtime.async_start_adapter")

    def _adapter_start_async_step(payload):
        calls["payload"] = payload
        return {"run_id": "loc1", "status": "running"}

    runtime_adapter.start_async_step = _adapter_start_async_step
    monkeypatch.setitem(sys.modules, "toas.runtime.async_start_adapter", runtime_adapter)
    monkeypatch.setitem(sys.modules, "toas.daemon.facade_async_ops", None)

    out = _start_async_step({"workdir": "/tmp"})
    assert out == {"run_id": "loc1", "status": "running"}
    assert calls["payload"] == {"workdir": "/tmp"}


def test_watch_async_step_wires_activity_store_call(monkeypatch):
    activity_store = types.ModuleType("toas.runtime.async_activity_store_api")
    activity_store.watch_async_step = lambda payload: {"status": "running", "next_offset": payload["offset"], "next_seq": 0}
    monkeypatch.setitem(sys.modules, "toas.runtime.async_activity_store_api", activity_store)

    out = _watch_async_step({"run_id": "r1", "offset": 2, "since_seq": 0, "workdir": "/tmp"})
    assert out["status"] == "running"
    assert out["next_offset"] == 2


def test_cancel_async_step_wires_activity_store_call(monkeypatch):
    activity_store = types.ModuleType("toas.runtime.async_activity_store_api")
    activity_store.cancel_async_step = lambda payload: {"status": "cancelling", "run_id": payload["run_id"]}
    monkeypatch.setitem(sys.modules, "toas.runtime.async_activity_store_api", activity_store)

    out = _cancel_async_step({"run_id": "r1", "workdir": "/tmp"})
    assert out["status"] == "cancelling"
    assert out["run_id"] == "r1"


def test_watch_event_text_early_return_non_dict_payload():
    from toas.cli_async_commands import _watch_event_text

    assert _watch_event_text({"payload": "not-a-dict"}) == ""


def test_watch_event_text_early_return_missing_text():
    from toas.cli_async_commands import _watch_event_text

    assert _watch_event_text({"payload": {}}) == ""
    assert _watch_event_text({"payload": {"text": None}}) == ""
    assert _watch_event_text({"payload": {"text": 123}}) == ""
    assert _watch_event_text({"payload": {"text": ""}}) == ""


def test_watch_event_text_early_return_non_delta_phase():
    from toas.cli_async_commands import _watch_event_text

    assert _watch_event_text({"payload": {"text": "hello", "phase": "start"}}) == ""
    assert _watch_event_text({"payload": {"text": "hello", "phase": "end"}}) == ""


def test_write_run_event_swallows_exceptions(monkeypatch):
    from toas.runtime.async_start_adapter import write_run_event
    monkeypatch.setattr(
        "toas.runtime.async_start_adapter.write_run_record",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )
    write_run_event("/tmp/workdir", "run-1", "started")


def test_start_async_step_passes_all_fns_to_impl(monkeypatch):
    from toas.runtime.async_start_adapter import start_async_step
    received = {}

    def _fake_impl(payload, **kwargs):
        received.update(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr("toas.runtime.async_start_adapter.start_async_step_impl", _fake_impl)
    result = start_async_step({"workdir": "/tmp"})
    assert result == {"status": "ok"}
    assert callable(received["normalize_workdir_fn"])
    assert callable(received["thinking_stream_enabled_fn"])
    assert callable(received["prompt_progress_stream_enabled_fn"])
    assert callable(received["stream_process_output_fn"])
    assert callable(received["wait_for_process_fn"])
    assert callable(received["write_run_event_fn"])


def test_normalize_workdir_windows_path_shape(monkeypatch):
    from toas.runtime.async_start_adapter import normalize_workdir

    monkeypatch.setattr("toas.runtime.async_start_adapter.sys.platform", "win32")
    assert normalize_workdir("/c/Users/tim/project") == "c:/Users/tim/project"
    assert normalize_workdir("/not-a-windows-path") == "/not-a-windows-path"


def test_stream_flag_helpers_delegate_to_policy_edges(monkeypatch):
    from toas.runtime.async_start_adapter import (
        prompt_progress_stream_enabled,
        thinking_stream_enabled,
    )

    monkeypatch.setattr(
        "toas.runtime.async_start_adapter.stream_flags_for_workdir",
        lambda workdir: (workdir.endswith("think"), workdir.endswith("prompt")),
    )
    assert thinking_stream_enabled("/tmp/think") is True
    assert prompt_progress_stream_enabled("/tmp/prompt") is True
