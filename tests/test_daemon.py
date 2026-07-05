from __future__ import annotations

import runpy
from pathlib import Path

import pytest

import toas.runtime.step_generation_runtime as sgr
from toas import daemon
from toas.daemon import handle_request
from toas.runtime import request_dispatch_adapter as rda


def _write_configured_session(tmp_path: Path, text: str, *, config_name: str = "session.md") -> None:
    target = tmp_path / ".toas" / "session.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    session_path = tmp_path / config_name
    if session_path != target:
        session_path.write_text(text, encoding="utf-8")


def test_handle_request_status():
    response = handle_request({"request_id": "r1", "op": "status", "payload": {}})
    assert response["protocol_version"] == 1
    assert response["request_id"] == "r1"
    assert response["ok"] is True
    assert response["payload"]["status"] == "ok"
    assert response["payload"]["envelope"]["kind"] == "status"


def test_handle_request_step_returns_stdout_and_applies_step(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_configured_session(tmp_path, "## TOAS:USER\nhello\n")
    monkeypatch.setattr(
        sgr,
        "generate_assistant_message",
        lambda messages, settings=None, extra_body=None, on_delta=None: {"role": "assistant", "content": "hi"},
    )

    response = handle_request({"request_id": "r1", "op": "step", "payload": {}})

    assert response["ok"] is True
    assert response["request_id"] == "r1"
    assert response["payload"]["stdout"] == "## TOAS:ASSISTANT\n\nhi\n\n"

    events = Path(".toas/events.jsonl").read_text(encoding="utf-8")
    assert '"role": "user", "content": "hello"' in events
    assert '"role": "assistant", "content": "hi"' in events


def test_handle_request_step_uses_configured_session_transcript_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("toas.toml").write_text('[session]\ntranscript_path = ".toas/session-a.md"\n', encoding="utf-8")
    Path(".toas/session-a.md").parent.mkdir(parents=True, exist_ok=True)
    Path(".toas/session-a.md").write_text("## TOAS:USER\nhello\n", encoding="utf-8")
    monkeypatch.setattr(
        sgr,
        "generate_assistant_message",
        lambda messages, settings=None, extra_body=None, on_delta=None: {"role": "assistant", "content": "hi"},
    )

    response = handle_request({"request_id": "r1", "op": "step", "payload": {}})

    assert response["ok"] is True
    assert response["payload"]["stdout"] == "## TOAS:ASSISTANT\n\nhi\n\n"
    events = Path(".toas/events.jsonl").read_text(encoding="utf-8")
    assert '"role": "user", "content": "hello"' in events
    assert not Path("session.md").exists()


def test_handle_request_step_projects_operator_result_and_writes_command_records(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_configured_session(tmp_path, "## TOAS:USER\n\n/pwd\n")

    response = handle_request({"request_id": "r1", "op": "step", "payload": {}})

    assert response["ok"] is True
    assert response["payload"]["stdout"].startswith("## TOAS:USER\n\n## RESULT\n\n")
    events = Path(".toas/events.jsonl").read_text(encoding="utf-8")
    assert '"role": "user", "content": "/pwd"' in events
    assert '"kind": "command_request"' in events
    assert '"kind": "command_result"' in events


def test_handle_request_unknown_op_returns_error():
    response = handle_request({"request_id": "r1", "op": "bogus", "payload": {}})
    assert response == {
        "protocol_version": 1,
        "request_id": "r1",
        "ok": False,
        "error": {"code": "unknown_op", "message": "unknown op: bogus"},
    }


def test_handle_request_prompt_returns_prompt_stdout(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    response = handle_request(
        {"request_id": "r1", "op": "prompt", "payload": {"ref": "protocol/terse_v1"}}
    )
    assert response["ok"] is True
    assert "Stay inside the local TOAS action protocol" in response["payload"]["stdout"]


def test_handle_request_stream_read_uses_stream_read_helper(monkeypatch):
    seen = {}
    daemon._REQUEST_HANDLER_RUNTIME = None

    class _Runtime:
        def handle_request(self, request):
            seen["request"] = request
            return {"payload": request["payload"]}

    monkeypatch.setattr("toas.daemon.build_request_handler_runtime", lambda **kwargs: _Runtime())

    response = handle_request(
        {
            "request_id": "r1",
            "op": "stream_read",
            "payload": {
                "run_id": "abc123",
                "mode": "follow",
                "since_seq": "7",
                "initial_output_len": "11",
                "initial_event_seq": "13",
            },
        }
    )

    assert response["payload"]["run_id"] == "abc123"
    assert seen["request"]["op"] == "stream_read"


def test_handle_request_stream_subscribe_forces_follow_mode(monkeypatch):
    seen = {}
    daemon._REQUEST_HANDLER_RUNTIME = None

    class _Runtime:
        def handle_request(self, request):
            seen["request"] = request
            return {"payload": request["payload"]}

    monkeypatch.setattr("toas.daemon.build_request_handler_runtime", lambda **kwargs: _Runtime())

    response = handle_request(
        {
            "request_id": "r1",
            "op": "stream_subscribe",
            "payload": {"run_id": "abc123", "mode": "tail"},
        }
    )

    assert response["payload"]["mode"] == "tail"
    assert seen["request"]["op"] == "stream_subscribe"


def test_safe_op_call_wrapper_delegates(monkeypatch):
    seen = {}
    validators = {"status": lambda payload: payload}

    def _safe_op_call(**kwargs):
        seen.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(rda, "safe_op_call", _safe_op_call)
    out = rda.safe_op_call_wrapper(
        request_id="r1",
        op="status",
        payload={"workdir": "/tmp"},
        handler=lambda payload: payload,
        payload_validators_obj=validators,
        make_ok_response=lambda request_id, payload: {"request_id": request_id, "payload": payload},
        make_error_response=lambda request_id, **kwargs: {"request_id": request_id, **kwargs},
    )

    assert out == {"ok": True}
    assert seen["request_id"] == "r1"
    assert seen["op"] == "status"
    assert seen["payload"] == {"workdir": "/tmp"}
    assert seen["payload_validators"] is validators


def test_daemon_main_exits_cleanly_on_keyboard_interrupt(monkeypatch):
    monkeypatch.setattr(daemon.sys, "argv", ["toasd", "serve"])
    monkeypatch.setattr(daemon, "serve_forever", lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(SystemExit) as exc:
        daemon.main()
    assert exc.value.code == 130


def test_daemon_module_entrypoint_delegates_to_package_main(monkeypatch):
    seen = {"called": False}
    monkeypatch.setattr(daemon, "main", lambda: seen.__setitem__("called", True))

    runpy.run_module("toas.daemon", run_name="__main__")

    assert seen["called"] is True


def test_daemon_main_start_stop_status_and_unknown(monkeypatch):
    monkeypatch.setattr(daemon, "start", lambda: {"pid": 1, "endpoint": "ep", "running": True})
    monkeypatch.setattr(daemon, "stop", lambda: {"running": False, "endpoint": "ep", "pid": None})
    monkeypatch.setattr(daemon, "status", lambda: {"running": True, "endpoint": "ep", "pid": 1})

    monkeypatch.setattr(daemon.sys, "argv", ["toasd", "start"])
    daemon.main()
    monkeypatch.setattr(daemon.sys, "argv", ["toasd", "stop"])
    daemon.main()
    monkeypatch.setattr(daemon.sys, "argv", ["toasd", "status"])
    daemon.main()

    monkeypatch.setattr(daemon.sys, "argv", ["toasd", "wat"])
    with pytest.raises(SystemExit, match="unknown command: wat"):
        daemon.main()


def test_daemon_top_level_wrappers_delegate(monkeypatch):
    calls = {}
    daemon._REQUEST_HANDLER_RUNTIME = None

    def _capture(name, result):
        def _inner(**kwargs):
            calls[name] = kwargs
            return result

        return _inner

    monkeypatch.setattr(
        "toas.config.config_from_discovered_paths",
        lambda *, workdir: type("Config", (), {"diagnostics": {"level": "debug"}, "workdir": workdir})(),
    )
    monkeypatch.setattr("toas.runtime.logging_bootstrap.configure_logging", lambda diagnostics: calls.setdefault("logging", diagnostics))
    monkeypatch.setattr(daemon, "serve_forever_impl", _capture("serve", "served"))
    monkeypatch.setattr(daemon, "start_impl", _capture("start", {"running": True}))
    monkeypatch.setattr(daemon, "stop_impl", _capture("stop", {"running": False}))
    monkeypatch.setattr(daemon, "status_impl", _capture("status", {"running": False}))
    monkeypatch.setattr(daemon, "main_impl", _capture("main", "mained"))

    assert daemon.serve_forever() == "served"
    assert daemon.start() == {"running": True}
    assert daemon.stop() == {"running": False}
    assert daemon.status() == {"running": False}
    assert daemon.main() == "mained"
    assert calls["serve"]["handle_request"] is daemon.handle_request
    assert calls["start"]["stale_socket_cleanup_fn"] is daemon._stale_socket_cleanup
    assert calls["stop"]["read_pid_fn"] is daemon._read_pid
    assert calls["status"]["run_step_healthcheck_fn"] is daemon._run_step_healthcheck
    assert calls["main"]["start_fn"] is daemon.start


def test_daemon_process_and_backend_delegate_wrappers(monkeypatch, tmp_path):
    seen = {}

    monkeypatch.setattr(daemon, "pid_path_impl", lambda: tmp_path / "daemon.pid")
    monkeypatch.setattr(daemon, "vim_port_path_impl", lambda: tmp_path / "daemon.port")
    monkeypatch.setattr(daemon, "read_pid_impl", lambda pid_path_fn: seen.setdefault("read_pid_fn", pid_path_fn)() and 17)
    monkeypatch.setattr(daemon, "is_pid_running_impl", lambda pid: seen.setdefault("pid", pid) == 17)
    monkeypatch.setattr(
        daemon,
        "run_step_healthcheck_impl",
        lambda *, rpc_request_fn: seen.setdefault("rpc_request_fn", rpc_request_fn) is daemon.rpc_request,
    )
    monkeypatch.setattr(
        daemon,
        "request_from_payload",
        lambda payload: seen.setdefault("payloads", []).append(payload) or {"request": payload},
    )
    monkeypatch.setattr(
        daemon,
        "result_to_dict",
        lambda result: seen.setdefault("results", []).append(result) or {"wrapped": result},
    )
    monkeypatch.setattr(
        daemon._BACKEND_LIFECYCLE,
        "status",
        lambda request: {"kind": "status", "request": request},
    )
    monkeypatch.setattr(
        daemon._BACKEND_LIFECYCLE,
        "start",
        lambda request: {"kind": "start", "request": request},
    )
    monkeypatch.setattr(
        daemon._BACKEND_LIFECYCLE,
        "stop",
        lambda request: {"kind": "stop", "request": request},
    )
    monkeypatch.setattr(
        daemon._BACKEND_LIFECYCLE,
        "restart",
        lambda request: {"kind": "restart", "request": request},
    )
    monkeypatch.setattr(
        "toas.daemon.server_lifecycle.stale_socket_cleanup",
        lambda **kwargs: (seen.setdefault("stale_socket_cleanup", kwargs), {"cleaned": True})[1],
    )

    assert daemon._pid_path() == tmp_path / "daemon.pid"
    assert daemon._vim_port_path() == tmp_path / "daemon.port"
    assert daemon._read_pid() == 17
    assert daemon._is_pid_running(17) is True
    assert daemon._run_step_healthcheck() is True
    assert daemon._managed_backend_status(mode="managed", workdir="/tmp") == {
        "wrapped": {"kind": "status", "request": {"request": {"mode": "managed", "workdir": "/tmp"}}}
    }
    assert daemon._managed_backend_start({"mode": "managed", "workdir": "/tmp"}) == {
        "wrapped": {"kind": "start", "request": {"request": {"mode": "managed", "workdir": "/tmp"}}}
    }
    assert daemon._managed_backend_stop({"mode": "managed", "workdir": "/tmp"}) == {
        "wrapped": {"kind": "stop", "request": {"request": {"mode": "managed", "workdir": "/tmp"}}}
    }
    assert daemon._managed_backend_restart({"mode": "managed", "workdir": "/tmp"}) == {
        "wrapped": {"kind": "restart", "request": {"request": {"mode": "managed", "workdir": "/tmp"}}}
    }
    assert daemon._stale_socket_cleanup() == {"cleaned": True}
    assert seen["read_pid_fn"] is daemon._pid_path
    assert seen["pid"] == 17
    assert seen["rpc_request_fn"] is daemon.rpc_request
    assert seen["payloads"] == [
        {"mode": "managed", "workdir": "/tmp"},
        {"mode": "managed", "workdir": "/tmp"},
        {"mode": "managed", "workdir": "/tmp"},
        {"mode": "managed", "workdir": "/tmp"},
    ]
    assert seen["stale_socket_cleanup"]["run_step_healthcheck_fn"] is daemon._run_step_healthcheck
