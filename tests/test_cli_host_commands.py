from __future__ import annotations

import sys

import pytest

from toas import cli_host_commands as chc


def test_run_host_serve_calls_runtime(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        chc,
        "serve_session_host",
        lambda owner_pid, request_handler: seen.update(owner_pid=owner_pid, request_handler=request_handler),
    )
    monkeypatch.setattr(chc, "_parse_serve_opts", lambda _args: (42, False, None))
    chc.run_host(["serve", "--owner-pid", "42"])
    assert seen["owner_pid"] == 42
    assert seen["request_handler"] is chc._host_request_handler


def test_host_request_handler_builds_without_importing_cli_or_daemon(monkeypatch):
    import toas

    class _Runtime:
        @staticmethod
        def handle_request(request):
            return {"ok": True, "request": request}

    seen = {}

    def _build_runtime(*, cli_module, **_kwargs):
        seen["cli_module"] = cli_module
        return _Runtime()

    monkeypatch.setattr(chc, "_HOST_REQUEST_RUNTIME", None)
    monkeypatch.setattr(chc, "build_local_request_handler_runtime", _build_runtime)
    monkeypatch.delitem(sys.modules, "toas.cli", raising=False)
    monkeypatch.delitem(sys.modules, "toas.daemon", raising=False)
    monkeypatch.delattr(toas, "cli", raising=False)
    monkeypatch.delattr(toas, "daemon", raising=False)

    out = chc._host_request_handler({"request_id": "r1"})

    assert out == {"ok": True, "request": {"request_id": "r1"}}
    assert seen["cli_module"].__name__ == "toas.cli_local_commands"
    assert "toas.cli" not in sys.modules
    assert "toas.daemon" not in sys.modules


def test_host_backend_lifecycle_wired_into_runtime(monkeypatch):
    """backend lifecycle fns passed to local runtime builder call through to _HOST_BACKEND_LIFECYCLE."""
    from toas.runtime.model_backend_lifecycle import BackendLifecycleResult

    external_result = BackendLifecycleResult(mode="external", status="external")
    monkeypatch.setattr(chc._HOST_BACKEND_LIFECYCLE, "status", lambda req: external_result)
    monkeypatch.setattr(chc, "_HOST_REQUEST_RUNTIME", None)

    seen_kwargs: dict = {}

    def _build_runtime(*, cli_module, **kwargs):
        seen_kwargs.update(kwargs)
        class _R:
            def handle_request(self, req):
                return {}
        return _R()

    monkeypatch.setattr(chc, "build_local_request_handler_runtime", _build_runtime)
    chc._host_request_handler({"request_id": "x"})

    assert "managed_backend_status_fn" in seen_kwargs
    result = seen_kwargs["managed_backend_status_fn"](mode="external", workdir="/tmp")
    assert result["mode"] == "external"
    assert result["status"] == "external"


def test_run_host_serve_stdio_json_sets_env(monkeypatch):
    seen = {}
    monkeypatch.setattr(chc, "serve_session_host", lambda owner_pid, request_handler: seen.setdefault("owner_pid", owner_pid))
    monkeypatch.setattr(chc, "_parse_serve_opts", lambda _args: (42, True, None))
    monkeypatch.delenv("TOAS_HOST_STDIO_JSON", raising=False)
    chc.run_host(["serve", "--owner-pid", "42", "--stdio-json"])
    assert seen["owner_pid"] == 42
    assert chc.os.environ["TOAS_HOST_STDIO_JSON"] == "1"


def test_run_host_usage_and_unknown():
    with pytest.raises(SystemExit, match="usage: toas host \\[serve\\|stop\\] \\[--owner-pid <pid>\\]"):
        chc.run_host([])
    with pytest.raises(SystemExit, match="unknown host command: bad"):
        chc.run_host(["bad"])


def test_parse_serve_opts_defaults_to_parent(monkeypatch):
    monkeypatch.setattr(chc.os, "getppid", lambda: 77)
    assert chc._parse_serve_opts([]) == (77, False, None)


def test_parse_serve_opts_rejects_unknown_option():
    with pytest.raises(SystemExit, match="unknown option: --bad"):
        chc._parse_serve_opts(["--bad"])


def test_parse_serve_opts_rejects_non_positive(monkeypatch):
    monkeypatch.setattr(chc.os, "getppid", lambda: 0)
    with pytest.raises(SystemExit, match="owner pid must be > 0"):
        chc._parse_serve_opts([])


def test_parse_serve_opts_requires_value():
    with pytest.raises(SystemExit, match="usage: toas host serve --owner-pid <pid>"):
        chc._parse_serve_opts(["--owner-pid"])


def test_parse_serve_opts_parses_stdio_json():
    assert chc._parse_serve_opts(["--owner-pid", "12", "--stdio-json"]) == (12, True, None)


def test_parse_serve_opts_parses_session_path():
    assert chc._parse_serve_opts(["--owner-pid", "12", "--session", ".toas/session-docs.md"]) == (
        12,
        False,
        ".toas/session-docs.md",
    )


def test_run_host_serve_sets_session_env(monkeypatch):
    seen = {}
    monkeypatch.setattr(chc, "serve_session_host", lambda owner_pid, request_handler: seen.setdefault("owner_pid", owner_pid))
    monkeypatch.setattr(chc, "_parse_serve_opts", lambda _args: (42, False, ".toas/session-docs.md"))
    monkeypatch.delenv("TOAS_HOST_SESSION_PATH", raising=False)
    chc.run_host(["serve", "--owner-pid", "42", "--session", ".toas/session-docs.md"])
    assert seen["owner_pid"] == 42
    assert chc.os.environ["TOAS_HOST_SESSION_PATH"] == ".toas/session-docs.md"


def test_run_host_stop_uses_recorded_pid_and_clears(monkeypatch, tmp_path):
    from toas.runtime.session_host_state import SessionHostRecord, write_session_host_record

    write_session_host_record(
        workdir=tmp_path,
        record=SessionHostRecord(
            host_id="h1",
            pid=1234,
            owner_pid=999,
            started_at=1.0,
            transport="stdio",
            endpoint="pipe://stdio",
        ),
    )
    seen = {}
    monkeypatch.setattr(chc, "stop_session_host", lambda pid: seen.setdefault("pid", pid))
    monkeypatch.setattr(chc, "_parse_stop_opts", lambda _args: chc.HostStopOpts(workdir=tmp_path, owner_kind="", owner_id=""))
    chc.run_host(["stop"])
    assert seen["pid"] == 1234
    assert chc.read_session_host_record(workdir=tmp_path) is None


def test_run_host_stop_ignores_stop_errors_and_clears(monkeypatch, tmp_path):
    from toas.runtime.session_host_state import SessionHostRecord, write_session_host_record

    write_session_host_record(
        workdir=tmp_path,
        record=SessionHostRecord(
            host_id="h1",
            pid=1234,
            owner_pid=999,
            started_at=1.0,
            transport="stdio",
            endpoint="pipe://stdio",
        ),
    )
    monkeypatch.setattr(chc, "_parse_stop_opts", lambda _args: chc.HostStopOpts(workdir=tmp_path, owner_kind="", owner_id=""))

    def _boom(pid):
        raise OSError("nope")

    monkeypatch.setattr(chc, "stop_session_host", _boom)
    chc.run_host(["stop"])
    assert chc.read_session_host_record(workdir=tmp_path) is None


def test_parse_stop_opts_defaults_to_cwd(monkeypatch, tmp_path):
    monkeypatch.delenv("TOAS_OWNER_KIND", raising=False)
    monkeypatch.delenv("TOAS_OWNER_ID", raising=False)
    monkeypatch.setattr(chc.Path, "cwd", lambda: tmp_path)
    out = chc._parse_stop_opts([])

    assert out.workdir == tmp_path.resolve()
    assert out.owner_kind == ""
    assert out.owner_id == ""


def test_parse_stop_opts_usage_and_unknown():
    with pytest.raises(SystemExit, match="usage: toas host stop \\[--workdir <path>\\]"):
        chc._parse_stop_opts(["--workdir"])
    with pytest.raises(SystemExit, match="unknown option: --bad"):
        chc._parse_stop_opts(["--bad"])


def test_parse_stop_opts_parses_explicit_path(tmp_path):
    raw = str(tmp_path / ".")
    out = chc._parse_stop_opts(["--workdir", raw])
    assert out.workdir == tmp_path.resolve()


def test_parse_stop_opts_parses_owner_fields():
    out = chc._parse_stop_opts(["--owner-kind", "editor", "--owner-id", "vim-1"])
    assert out.owner_kind == "editor"
    assert out.owner_id == "vim-1"


def test_parse_stop_opts_owner_usage():
    with pytest.raises(SystemExit, match="usage: toas host stop \\[--owner-kind <editor\\|shell>\\]"):
        chc._parse_stop_opts(["--owner-kind"])
    with pytest.raises(SystemExit, match="usage: toas host stop \\[--owner-id <id>\\]"):
        chc._parse_stop_opts(["--owner-id"])


def test_stop_host_recorded_for_workdir_no_record_is_noop(tmp_path):
    chc._stop_host_recorded_for_workdir(tmp_path)


def test_stop_host_recorded_for_workdir_owner_mismatch_noop(monkeypatch, tmp_path):
    from toas.runtime.session_host_state import SessionHostRecord, write_session_host_record

    write_session_host_record(
        workdir=tmp_path,
        record=SessionHostRecord(
            host_id="h1",
            pid=1234,
            owner_pid=999,
            owner_kind="editor",
            owner_id="vim-1",
            started_at=1.0,
            transport="stdio",
            endpoint="pipe://stdio",
        ),
    )
    seen = {"called": False}
    monkeypatch.setattr(chc, "stop_session_host", lambda pid: seen.__setitem__("called", True))
    chc._stop_host_recorded_for_workdir(tmp_path, owner_kind="editor", owner_id="vim-2")
    assert seen["called"] is False
    assert chc.read_session_host_record(workdir=tmp_path) is not None


def test_stop_host_recorded_for_workdir_owner_kind_mismatch_noop(monkeypatch, tmp_path):
    from toas.runtime.session_host_state import SessionHostRecord, write_session_host_record

    write_session_host_record(
        workdir=tmp_path,
        record=SessionHostRecord(
            host_id="h1",
            pid=1234,
            owner_pid=999,
            owner_kind="editor",
            owner_id="vim-1",
            started_at=1.0,
            transport="stdio",
            endpoint="pipe://stdio",
        ),
    )
    seen = {"called": False}
    monkeypatch.setattr(chc, "stop_session_host", lambda pid: seen.__setitem__("called", True))
    chc._stop_host_recorded_for_workdir(tmp_path, owner_kind="shell")
    assert seen["called"] is False
    assert chc.read_session_host_record(workdir=tmp_path) is not None


def test_parse_serve_opts_session_missing_arg():
    from toas.cli_host_commands import _parse_serve_opts

    with pytest.raises(SystemExit, match="usage"):
        _parse_serve_opts(["--session"])
