from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from toas.cli_demo_async_client import (
    AsyncHostClient,
    DaemonRpcClient,
    HostClient,
    _print_envelopes,
    _read_diag_tail,
    _read_wire_tail,
    _start_host,
    build_parser,
    main,
)

# ---------------------------------------------------------------------------
# _print_envelopes
# ---------------------------------------------------------------------------

class TestPrintEnvelopes:
    def test_empty_payload_returns_false(self, capsys):
        assert _print_envelopes({}) is False
        assert capsys.readouterr().out == ""

    def test_no_envelopes_key_returns_false(self, capsys):
        assert _print_envelopes({"other": True}) is False
        assert capsys.readouterr().out == ""

    def test_empty_envelopes_list_returns_false(self, capsys):
        assert _print_envelopes({"envelopes": []}) is False
        assert capsys.readouterr().out == ""

    def test_prints_kind_without_status(self, capsys):
        payload = {"envelopes": [{"kind": "llm_delta"}]}
        result = _print_envelopes(payload)
        assert result is False
        assert "envelope kind=llm_delta" in capsys.readouterr().out

    def test_prints_kind_with_status(self, capsys):
        payload = {
            "envelopes": [{"kind": "tool_call", "payload": {"status": "started"}}],
        }
        result = _print_envelopes(payload)
        assert result is False
        assert "envelope kind=tool_call status=started" in capsys.readouterr().out

    def test_llm_done_sets_terminal_true(self, capsys):
        payload = {"envelopes": [{"kind": "llm_done"}]}
        result = _print_envelopes(payload)
        assert result is True

    def test_run_done_sets_terminal_true(self, capsys):
        payload = {"envelopes": [{"kind": "run_done"}]}
        result = _print_envelopes(payload)
        assert result is True

    def test_cancelled_sets_terminal_true(self, capsys):
        payload = {"envelopes": [{"kind": "cancelled"}]}
        result = _print_envelopes(payload)
        assert result is True

    def test_error_sets_terminal_true(self, capsys):
        payload = {"envelopes": [{"kind": "error"}]}
        result = _print_envelopes(payload)
        assert result is True

    def test_non_terminal_kind_returns_false(self, capsys):
        payload = {
            "envelopes": [
                {"kind": "tool_call"},
                {"kind": "llm_delta"},
            ],
        }
        result = _print_envelopes(payload)
        assert result is False

    def test_mixed_envelopes_terminal_if_any_terminal(self, capsys):
        payload = {
            "envelopes": [
                {"kind": "tool_call"},
                {"kind": "llm_done"},
            ],
        }
        result = _print_envelopes(payload)
        assert result is True

    def test_non_dict_envelope_ignored(self, capsys):
        payload = {"envelopes": ["string_entry", {"kind": "tool_call"}]}
        result = _print_envelopes(payload)
        assert result is False
        assert capsys.readouterr().out.count("envelope") == 1

# ---------------------------------------------------------------------------
# _read_diag_tail
# ---------------------------------------------------------------------------

class TestReadDiagTail:
    def test_none_path_returns_empty(self):
        assert _read_diag_tail(None) == ""

    def test_missing_path_returns_empty(self, tmp_path: Path):
        assert _read_diag_tail(tmp_path / "nonexistent.log") == ""

    def test_returns_last_8_lines(self, tmp_path: Path):
        path = tmp_path / "diag.log"
        lines = [f"line-{i}" for i in range(20)]
        path.write_text("\n".join(lines))
        result = _read_diag_tail(path)
        expected = " | ".join(lines[-8:])
        assert result == expected

    def test_fewer_than_8_lines(self, tmp_path: Path):
        path = tmp_path / "diag.log"
        path.write_text("a\nb\nc")
        result = _read_diag_tail(path)
        assert result == "a | b | c"

    def test_empty_file(self, tmp_path: Path):
        path = tmp_path / "diag.log"
        path.write_text("")
        assert _read_diag_tail(path) == ""

    def test_exception_returns_empty(self, tmp_path: Path):
        path = tmp_path / "diag.log"
        path.write_text("ok")
        with mock.patch("pathlib.Path.read_text", side_effect=PermissionError):
            assert _read_diag_tail(path) == ""

# ---------------------------------------------------------------------------
# _read_wire_tail
# ---------------------------------------------------------------------------

class TestReadWireTail:
    def test_returns_empty_when_no_wire_log(self, tmp_path: Path):
        with mock.patch("pathlib.Path.cwd", return_value=tmp_path):
            assert _read_wire_tail() == ""

    def test_returns_last_8_lines(self, tmp_path: Path):
        toas = tmp_path / ".toas"
        toas.mkdir()
        wire = toas / "host-stdio-wire.log"
        lines = [f"wire-{i}" for i in range(15)]
        wire.write_text("\n".join(lines))
        with mock.patch("pathlib.Path.cwd", return_value=tmp_path):
            result = _read_wire_tail()
        expected = " | ".join(lines[-8:])
        assert result == expected

    def test_fewer_than_8_lines(self, tmp_path: Path):
        toas = tmp_path / ".toas"
        toas.mkdir()
        wire = toas / "host-stdio-wire.log"
        wire.write_text("x\ny")
        with mock.patch("pathlib.Path.cwd", return_value=tmp_path):
            result = _read_wire_tail()
        assert result == "x | y"

    def test_exception_returns_empty(self, tmp_path: Path):
        toas = tmp_path / ".toas"
        toas.mkdir()
        wire = toas / "host-stdio-wire.log"
        wire.write_text("ok")
        with (
            mock.patch("pathlib.Path.cwd", return_value=tmp_path),
            mock.patch("pathlib.Path.read_text", side_effect=PermissionError),
        ):
            assert _read_wire_tail() == ""

# ---------------------------------------------------------------------------
# build_parser
# ---------------------------------------------------------------------------

class TestBuildParser:
    def test_parser_has_description(self):
        p = build_parser()
        assert "Demo async stdio-json client" in p.description

    def test_default_workdir(self):
        p = build_parser()
        args = p.parse_args([])
        assert args.workdir == "."

    def test_default_transport_stdio_host(self):
        p = build_parser()
        args = p.parse_args([])
        assert args.transport == "stdio-host"

    def test_default_transport_daemon_rpc(self):
        p = build_parser()
        args = p.parse_args(["--transport", "daemon-rpc"])
        assert args.transport == "daemon-rpc"

    def test_default_backend_mode_local(self):
        p = build_parser()
        args = p.parse_args([])
        assert args.backend_mode == "local"

    def test_default_mode_follow(self):
        p = build_parser()
        args = p.parse_args([])
        assert args.mode == "follow"

    def test_default_read_timeout_s(self):
        p = build_parser()
        args = p.parse_args([])
        assert args.read_timeout_s == 5.0

    def test_default_request_timeout_s(self):
        p = build_parser()
        args = p.parse_args([])
        assert args.request_timeout_s == 15.0

    def test_default_poll_interval_s(self):
        p = build_parser()
        args = p.parse_args([])
        assert args.poll_interval_s == 0.5

    def test_default_max_seconds(self):
        p = build_parser()
        args = p.parse_args([])
        assert args.max_seconds == 120.0

    def test_default_host_cmd(self):
        p = build_parser()
        args = p.parse_args([])
        assert args.host_cmd == ["toas", "host", "serve", "--stdio-json"]

    def test_custom_host_cmd(self):
        p = build_parser()
        args = p.parse_args(["--host-cmd", "python3", "toas_host_serve.py"])
        assert args.host_cmd == ["python3", "toas_host_serve.py"]

    def test_owner_pid_flag(self):
        p = build_parser()
        args = p.parse_args(["--owner-pid", "42"])
        assert args.owner_pid == 42

    def test_ignore_owner_check_flag(self):
        p = build_parser()
        args = p.parse_args(["--ignore-owner-check"])
        assert args.ignore_owner_check is True

    def test_subscribe_flag(self):
        p = build_parser()
        args = p.parse_args(["--subscribe"])
        assert args.subscribe is True

    def test_poll_mode(self):
        p = build_parser()
        args = p.parse_args(["--mode", "poll"])
        assert args.mode == "poll"

    def test_external_backend(self):
        p = build_parser()
        args = p.parse_args(["--backend-mode", "external"])
        assert args.backend_mode == "external"

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_adds_stdio_json_if_missing(self):
        with mock.patch("toas.cli_demo_async_client._run_demo") as mock_run_demo:
            main(["--transport", "daemon-rpc", "--host-cmd", "python3", "toas_host.py"])
            call_args = mock_run_demo.call_args[0][0]
            assert "--stdio-json" in call_args.host_cmd

    def test_main_appends_owner_pid(self):
        with mock.patch("toas.cli_demo_async_client._run_demo") as mock_run_demo:
            main(["--transport", "daemon-rpc", "--owner-pid", "999"])
            call_args = mock_run_demo.call_args[0][0]
            assert "--owner-pid" in call_args.host_cmd
            assert "999" in call_args.host_cmd

    def test_main_stdio_host_transport_calls_async_run(self):
        def fake_run(coro):
            coro.close()
            return 0

        with mock.patch(
            "toas.cli_demo_async_client.asyncio.run", side_effect=fake_run
        ) as mock_asyncio_run:
            main(["--transport", "stdio-host"])
            mock_asyncio_run.assert_called_once()

    def test_main_daemon_rpc_transport_calls_run_demo(self):
        with mock.patch("toas.cli_demo_async_client._run_demo", return_value=0) as mock_run_demo:
            main(["--transport", "daemon-rpc"])
            mock_run_demo.assert_called_once()

    def test_main_returns_run_demo_result(self):
        with mock.patch("toas.cli_demo_async_client._run_demo", return_value=42):
            result = main(["--transport", "daemon-rpc"])
            assert result == 42

# ---------------------------------------------------------------------------
# DaemonRpcClient
# ---------------------------------------------------------------------------

class TestDaemonRpcClient:
    def test_request_returns_ok_with_rpc_result(self):
        client = DaemonRpcClient()
        with mock.patch("toas.cli_demo_async_client.rpc_request", return_value={"status": "ok"}) as mock_rpc:
            result = client.request("status", {})
        assert result == {"ok": True, "payload": {"status": "ok"}}
        mock_rpc.assert_called_once_with("status", {})

    def test_request_passes_op_and_payload(self):
        client = DaemonRpcClient()
        with mock.patch("toas.cli_demo_async_client.rpc_request") as mock_rpc:
            client.request("step_async", {"key": "val"})
        mock_rpc.assert_called_once_with("step_async", {"key": "val"})

    def test_request_ignores_request_id(self):
        """request_id is accepted but ignored (assigned to _)"""
        client = DaemonRpcClient()
        with mock.patch("toas.cli_demo_async_client.rpc_request", return_value={}):
            result = client.request("status", {}, request_id="ignored")
        assert result == {"ok": True, "payload": {}}

# ---------------------------------------------------------------------------
# HostClient (sync)
# ---------------------------------------------------------------------------

class TestHostClient:
    def test_request_sends_json_frame_and_reads_response(self, tmp_path: Path):
        """HostClient.request writes a JSON frame and reads a response."""
        proc = subprocess.Popen(
            [
                sys.executable,
                "-u",
                "-c",
                r"""
import json, sys
for line in sys.stdin:
    req = json.loads(line.strip())
    print(json.dumps({"ok": True, "request_id": req["request_id"]}))
    sys.stdout.flush()
""",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            client = HostClient(proc, request_timeout_s=5.0)
            resp = client.request("status", {}, request_id="test-1")
            assert resp["ok"] is True
            assert resp["request_id"] == "test-1"
        finally:
            proc.terminate()
            proc.wait()

    def test_request_empty_response_raises_runtime_error(self, tmp_path: Path):
        """When host exits before responding, HostClient raises RuntimeError."""
        # Spawn a process that reads one line then exits without writing stdout
        proc = subprocess.Popen(
            [sys.executable, "-u", "-c", "import sys; sys.stdin.readline()"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        client = HostClient(proc, request_timeout_s=2.0)
        with pytest.raises(RuntimeError, match="empty response from host"):
            client.request("status", {})
        proc.terminate()
        proc.wait()

    def test_request_id_mismatch_raises(self, tmp_path: Path):
        """When response has wrong request_id, HostClient raises RuntimeError."""
        proc = subprocess.Popen(
            [
                sys.executable,
                "-u",
                "-c",
                r"""
import json, sys
for line in sys.stdin:
    print(json.dumps({"ok": True, "request_id": "wrong-id"}))
    sys.stdout.flush()
""",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            client = HostClient(proc, request_timeout_s=5.0)
            with pytest.raises(RuntimeError, match="request_id mismatch"):
                client.request("status", {}, request_id="expected-id")
        finally:
            proc.terminate()
            proc.wait()

    def test_request_generates_request_id_when_none(self, tmp_path: Path):
        """HostClient generates a request_id if none provided."""
        proc = subprocess.Popen(
            [
                sys.executable,
                "-u",
                "-c",
                r"""
import json, sys
for line in sys.stdin:
    req = json.loads(line.strip())
    print(json.dumps({"ok": True, "request_id": req["request_id"]}))
    sys.stdout.flush()
""",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            client = HostClient(proc, request_timeout_s=5.0)
            resp = client.request("status", {})
            assert resp["request_id"]  # generated id is present
        finally:
            proc.terminate()
            proc.wait()

# ---------------------------------------------------------------------------
# _start_host
# ---------------------------------------------------------------------------

class TestStartHost:
    def test_starts_host_process_and_returns_host_client(self, tmp_path: Path):
        client = _start_host(
            workdir=tmp_path,
            host_cmd=[sys.executable, "-c", "pass"],
        )
        try:
            assert isinstance(client, HostClient)
            assert client.proc is not None
        finally:
            client.proc.terminate()
            client.proc.wait()

    def test_sets_custom_env_vars(self, tmp_path: Path):
        client = _start_host(
            workdir=tmp_path,
            host_cmd=[sys.executable, "-c", "import os, json; print(json.dumps(os.environ.get('MY_VAR', '')), file=__import__('sys').stderr); sys.exit(0)"],
            host_env={"MY_VAR": "hello"},
        )
        try:
            assert isinstance(client, HostClient)
        finally:
            client.proc.terminate()
            client.proc.wait()

    def test_passes_diag_path_and_timeout(self, tmp_path: Path):
        diag = tmp_path / "diag.log"
        client = _start_host(
            workdir=tmp_path,
            host_cmd=[sys.executable, "-c", "pass"],
            diag_path=diag,
            request_timeout_s=7.0,
        )
        try:
            assert client.diag_path == diag
            assert client.request_timeout_s == 7.0
        finally:
            client.proc.terminate()
            client.proc.wait()

# ---------------------------------------------------------------------------
# _run_demo (sync)
# ---------------------------------------------------------------------------

class TestRunDemo:
    def test_probe_failure_returns_2(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="daemon-rpc",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
        )
        with mock.patch("toas.cli_demo_async_client.DaemonRpcClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.request.return_value = {"ok": False, "error": "no host"}
            result = _run_demo(args)
        assert result == 2
        assert "probe failed" in capsys.readouterr().out

    def test_step_async_failure_returns_2(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="daemon-rpc",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
        )
        with mock.patch("toas.cli_demo_async_client.DaemonRpcClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.request.side_effect = [
                {"ok": True, "payload": {"status": "running"}},  # probe
                {"ok": False, "error": "step failed"},             # step_async
            ]
            result = _run_demo(args)
        assert result == 2
        assert "step_async failed" in capsys.readouterr().out

    def test_missing_run_id_returns_2(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="daemon-rpc",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
        )
        with mock.patch("toas.cli_demo_async_client.DaemonRpcClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.request.side_effect = [
                {"ok": True, "payload": {"status": "running"}},  # probe
                {"ok": True, "payload": {}},                       # step_async no run_id
            ]
            result = _run_demo(args)
        assert result == 2
        assert "missing run_id" in capsys.readouterr().out

    def test_terminal_status_done_returns_0(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="daemon-rpc",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
        )
        with mock.patch("toas.cli_demo_async_client.DaemonRpcClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.request.side_effect = [
                {"ok": True, "payload": {"status": "running"}},  # probe
                {"ok": True, "payload": {"run_id": "r1", "status": "running"}},  # step_async
                {"ok": True, "payload": {"status": "done", "next_offset": 1, "next_seq": 1}},  # stream_read
            ]
            result = _run_demo(args)
        assert result == 0
        assert "terminal_status=done" in capsys.readouterr().out

    def test_terminal_status_succeeded_returns_0(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="daemon-rpc",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
        )
        with mock.patch("toas.cli_demo_async_client.DaemonRpcClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.request.side_effect = [
                {"ok": True, "payload": {"status": "running"}},
                {"ok": True, "payload": {"run_id": "r1", "status": "running"}},
                {"ok": True, "payload": {"status": "succeeded", "next_offset": 1, "next_seq": 1}},
            ]
            result = _run_demo(args)
        assert result == 0
        assert "terminal_status=succeeded" in capsys.readouterr().out

    def test_terminal_status_failed_returns_4(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="daemon-rpc",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
        )
        with mock.patch("toas.cli_demo_async_client.DaemonRpcClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.request.side_effect = [
                {"ok": True, "payload": {"status": "running"}},
                {"ok": True, "payload": {"run_id": "r1", "status": "running"}},
                {"ok": True, "payload": {"status": "failed", "error": "boom", "next_offset": 1, "next_seq": 1}},
            ]
            result = _run_demo(args)
        assert result == 4
        out = capsys.readouterr().out
        assert "terminal_status=failed" in out
        assert "error=boom" in out

    def test_terminal_status_cancelled_returns_4(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="daemon-rpc",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
        )
        with mock.patch("toas.cli_demo_async_client.DaemonRpcClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.request.side_effect = [
                {"ok": True, "payload": {"status": "running"}},
                {"ok": True, "payload": {"run_id": "r1", "status": "running"}},
                {"ok": True, "payload": {"status": "cancelled", "next_offset": 1, "next_seq": 1}},
            ]
            result = _run_demo(args)
        assert result == 4

    def test_saw_terminal_envelope_returns_0(self, tmp_path: Path, capsys):
        """If _print_envelopes returns True, demo returns 0 immediately."""
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="daemon-rpc",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
        )
        with mock.patch("toas.cli_demo_async_client.DaemonRpcClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.request.side_effect = [
                {"ok": True, "payload": {"status": "running"}},
                {"ok": True, "payload": {"run_id": "r1", "status": "running"}},
                {
                    "ok": True,
                    "payload": {
                        "status": "running",
                        "next_offset": 1,
                        "next_seq": 1,
                        "envelopes": [{"kind": "llm_done"}],
                    },
                },
            ]
            result = _run_demo(args)
        assert result == 0
        assert "terminal_status=done" in capsys.readouterr().out

    def test_timeout_returns_3(self, tmp_path: Path, capsys):
        """Demo returns 3 on max_seconds timeout."""
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="daemon-rpc",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=0.001,  # very short
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
        )
        with mock.patch("toas.cli_demo_async_client.DaemonRpcClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.request.side_effect = [
                {"ok": True, "payload": {"status": "running"}},
                {"ok": True, "payload": {"run_id": "r1", "status": "running"}},
                {
                    "ok": True,
                    "payload": {
                        "status": "running",
                        "next_offset": 1,
                        "next_seq": 1,
                    },
                },
            ]
            result = _run_demo(args)
        assert result == 3
        assert "timed out" in capsys.readouterr().out

    def test_stream_read_failure_returns_2(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="daemon-rpc",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
        )
        with mock.patch("toas.cli_demo_async_client.DaemonRpcClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.request.side_effect = [
                {"ok": True, "payload": {"status": "running"}},
                {"ok": True, "payload": {"run_id": "r1", "status": "running"}},
                {"ok": False, "error": "stream_read error"},
            ]
            result = _run_demo(args)
        assert result == 2
        assert "stream_read failed" in capsys.readouterr().out

    def test_stdio_host_transport_spawns_process(self, tmp_path: Path, capsys):
        """stdio-host transport calls _start_host and terminates in finally."""
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="stdio-host",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=[sys.executable, "-c", "pass"],
            ignore_owner_check=False,
        )
        with (
            mock.patch(
                "toas.cli_demo_async_client._start_host",
            ) as mock_start,
            mock.patch("toas.cli_demo_async_client.time.sleep", return_value=None),
        ):
            mock_proc = mock.Mock()
            mock_proc.poll.return_value = None
            mock_host = mock.Mock(spec=HostClient)
            mock_host.proc = mock_proc
            mock_host.request.return_value = {
                "ok": True,
                "payload": {"status": "running"},
            }
            mock_start.return_value = mock_host

            # First call is probe, second is step_async (missing run_id -> returns 2)
            mock_host.request.side_effect = [
                {"ok": True, "payload": {"status": "running"}},
                {"ok": True, "payload": {}},  # missing run_id
            ]

            result = _run_demo(args)
        assert result == 2
        mock_start.assert_called_once()
        # finally block should attempt terminate
        mock_proc.terminate.assert_called_once()

    def test_stdio_host_transport_finaly_does_not_terminate_if_already_dead(self, tmp_path: Path):
        """If spawned proc already dead, finally skips terminate."""
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="stdio-host",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=[sys.executable, "-c", "pass"],
            ignore_owner_check=False,
        )
        with (
            mock.patch("toas.cli_demo_async_client._start_host") as mock_start,
            mock.patch("toas.cli_demo_async_client.time.sleep", return_value=None),
        ):
            mock_proc = mock.Mock()
            mock_proc.poll.return_value = 0  # already dead
            mock_host = mock.Mock(spec=HostClient)
            mock_host.proc = mock_proc
            mock_host.request.side_effect = [
                {"ok": True, "payload": {"status": "running"}},
                {"ok": True, "payload": {}},  # missing run_id -> returns 2
            ]
            mock_start.return_value = mock_host

            _run_demo(args)
        mock_proc.terminate.assert_not_called()

    def test_ignore_owner_check_sets_env(self, tmp_path: Path):
        """ignore_owner_check=True sets TOAS_HOST_IGNORE_OWNER_CHECK in host_env."""
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="stdio-host",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=[sys.executable, "-c", "pass"],
            ignore_owner_check=True,
        )
        with mock.patch("toas.cli_demo_async_client._start_host") as mock_start:
            mock_proc = mock.Mock()
            mock_proc.poll.return_value = 0
            mock_host = mock.Mock(spec=HostClient)
            mock_host.proc = mock_proc
            mock_host.request.side_effect = [
                {"ok": True, "payload": {"status": "running"}},
                {"ok": True, "payload": {}},
            ]
            mock_start.return_value = mock_host

            _run_demo(args)

        call_kwargs = mock_start.call_args[1]
        assert call_kwargs["host_env"].get("TOAS_HOST_IGNORE_OWNER_CHECK") == "1"

    def test_output_in_stream_read_is_printed(self, tmp_path: Path, capsys):
        """stream_read with 'out' in payload prints it."""
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="daemon-rpc",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
        )
        with mock.patch("toas.cli_demo_async_client.DaemonRpcClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.request.side_effect = [
                {"ok": True, "payload": {"status": "running"}},
                {"ok": True, "payload": {"run_id": "r1", "status": "running"}},
                {"ok": True, "payload": {"status": "done", "out": "hello world\n", "next_offset": 1, "next_seq": 1}},
            ]
            result = _run_demo(args)
        assert result == 0
        out = capsys.readouterr().out
        assert "hello world" in out

    def test_stdio_host_transport_kill_on_terminate_failure(self, tmp_path: Path):
        """If terminate+wait raises, finally calls kill on spawned proc."""
        from toas.cli_demo_async_client import _run_demo

        args = argparse.Namespace(
            workdir=str(tmp_path),
            transport="stdio-host",
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=[sys.executable, "-c", "pass"],
            ignore_owner_check=False,
        )
        with mock.patch("toas.cli_demo_async_client._start_host") as mock_start:
            mock_proc = mock.Mock()
            mock_proc.poll.return_value = None  # still alive
            mock_proc.terminate = mock.Mock()
            mock_proc.wait = mock.Mock(side_effect=TimeoutError)
            mock_proc.kill = mock.Mock()
            mock_host = mock.Mock(spec=HostClient)
            mock_host.proc = mock_proc
            mock_host.request.side_effect = [
                {"ok": True, "payload": {"status": "running"}},
                {"ok": True, "payload": {}},  # missing run_id -> returns 2
            ]
            mock_start.return_value = mock_host

            _run_demo(args)
        mock_proc.kill.assert_called_once()

# ---------------------------------------------------------------------------
# _run_demo_async_stdio
# ---------------------------------------------------------------------------

class TestRunDemoAsyncStdio:
    def test_probe_failure_returns_2(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo_async_stdio

        args = argparse.Namespace(
            workdir=str(tmp_path),
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
            subscribe=False,
        )
        with mock.patch(
            "asyncio.create_subprocess_exec",
            new_callable=mock.AsyncMock,
        ) as mock_create:
            mock_proc = mock.AsyncMock()
            mock_proc.stdin = mock.AsyncMock()
            mock_proc.stdout = mock.AsyncMock()
            mock_create.return_value = mock_proc

            async def fake_request(self, op, payload, **kw):
                return {"ok": False, "error": "no host"}

            with mock.patch.object(
                AsyncHostClient, "request", new=fake_request
            ):
                result = asyncio.run(_run_demo_async_stdio(args))
        assert result == 2
        assert "probe failed" in capsys.readouterr().out

    def test_cleanup_kills_process_when_wait_fails(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo_async_stdio

        args = argparse.Namespace(
            workdir=str(tmp_path),
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
            subscribe=False,
        )
        with mock.patch(
            "asyncio.create_subprocess_exec",
            new_callable=mock.AsyncMock,
        ) as mock_create:
            mock_proc = mock.AsyncMock()
            mock_proc.stdin = mock.AsyncMock()
            mock_proc.stdout = mock.AsyncMock()
            mock_proc.returncode = None
            mock_proc.terminate = mock.Mock()
            mock_proc.wait = mock.AsyncMock(side_effect=RuntimeError("still running"))
            mock_proc.kill = mock.Mock()
            mock_create.return_value = mock_proc

            async def fake_request(self, op, payload, **kw):
                return {"ok": False, "error": "no host"}

            with mock.patch.object(
                AsyncHostClient, "request", new=fake_request
            ):
                result = asyncio.run(_run_demo_async_stdio(args))
        assert result == 2
        assert "probe failed" in capsys.readouterr().out
        mock_proc.kill.assert_called_once()

    def test_step_async_failure_returns_2(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo_async_stdio

        args = argparse.Namespace(
            workdir=str(tmp_path),
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
            subscribe=False,
        )
        with mock.patch(
            "asyncio.create_subprocess_exec",
            new_callable=mock.AsyncMock,
        ) as mock_create:
            mock_proc = mock.AsyncMock()
            mock_proc.stdin = mock.AsyncMock()
            mock_proc.stdout = mock.AsyncMock()
            mock_create.return_value = mock_proc

            call_count = 0

            async def fake_request(self, op, payload, **kw):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {"ok": True, "payload": {"status": "running"}}
                return {"ok": False, "error": "step failed"}

            with mock.patch.object(
                AsyncHostClient, "request", new=fake_request
            ):
                result = asyncio.run(_run_demo_async_stdio(args))
        assert result == 2
        assert "step_async failed" in capsys.readouterr().out

    def test_terminal_status_done_returns_0(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo_async_stdio

        args = argparse.Namespace(
            workdir=str(tmp_path),
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
            subscribe=False,
        )
        with mock.patch(
            "asyncio.create_subprocess_exec",
            new_callable=mock.AsyncMock,
        ) as mock_create:
            mock_proc = mock.AsyncMock()
            mock_proc.stdin = mock.AsyncMock()
            mock_proc.stdout = mock.AsyncMock()
            mock_create.return_value = mock_proc

            call_count = 0

            async def fake_request(self, op, payload, **kw):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {"ok": True, "payload": {"status": "running"}}
                elif call_count == 2:
                    return {"ok": True, "payload": {"run_id": "r1", "status": "running"}}
                return {
                    "ok": True,
                    "payload": {"status": "done", "next_offset": 1, "next_seq": 1},
                }

            with mock.patch.object(
                AsyncHostClient, "request", new=fake_request
            ):
                result = asyncio.run(_run_demo_async_stdio(args))
        assert result == 0
        assert "terminal_status=done" in capsys.readouterr().out

    def test_terminal_status_failed_returns_4(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo_async_stdio

        args = argparse.Namespace(
            workdir=str(tmp_path),
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
            subscribe=False,
        )
        with mock.patch(
            "asyncio.create_subprocess_exec",
            new_callable=mock.AsyncMock,
        ) as mock_create:
            mock_proc = mock.AsyncMock()
            mock_proc.stdin = mock.AsyncMock()
            mock_proc.stdout = mock.AsyncMock()
            mock_create.return_value = mock_proc

            call_count = 0

            async def fake_request(self, op, payload, **kw):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {"ok": True, "payload": {"status": "running"}}
                elif call_count == 2:
                    return {"ok": True, "payload": {"run_id": "r1", "status": "running"}}
                return {
                    "ok": True,
                    "payload": {"status": "failed", "error": "boom", "next_offset": 1, "next_seq": 1},
                }

            with mock.patch.object(
                AsyncHostClient, "request", new=fake_request
            ):
                result = asyncio.run(_run_demo_async_stdio(args))
        assert result == 4
        out = capsys.readouterr().out
        assert "terminal_status=failed" in out
        assert "error=boom" in out

    def test_subscribe_mode_push_complete_returns_0(self, tmp_path: Path, capsys):
        """subscribe=True uses request_stream and returns 0 on push_complete."""
        from toas.cli_demo_async_client import _run_demo_async_stdio

        args = argparse.Namespace(
            workdir=str(tmp_path),
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
            subscribe=True,
        )
        with mock.patch(
            "asyncio.create_subprocess_exec",
            new_callable=mock.AsyncMock,
        ) as mock_create:
            mock_proc = mock.AsyncMock()
            mock_proc.stdin = mock.AsyncMock()
            mock_proc.stdout = mock.AsyncMock()
            mock_create.return_value = mock_proc

            call_count = 0

            async def fake_request(self, op, payload, **kw):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {"ok": True, "payload": {"status": "running"}}
                return {"ok": True, "payload": {"run_id": "r1", "status": "running"}}

            async def fake_request_stream(self, op, payload, **kw):
                q: asyncio.Queue = asyncio.Queue()
                await q.put({"payload": {"kind": "push_complete"}})
                return q

            with (
                mock.patch.object(
                    AsyncHostClient, "request", new=fake_request
                ),
                mock.patch.object(
                    AsyncHostClient, "request_stream", new=fake_request_stream
                ),
            ):
                result = asyncio.run(_run_demo_async_stdio(args))
        assert result == 0
        assert "terminal_status=succeeded" in capsys.readouterr().out

    def test_subscribe_timeout_returns_3(self, tmp_path: Path, capsys):
        """subscribe mode times out and returns 3."""
        from toas.cli_demo_async_client import _run_demo_async_stdio

        args = argparse.Namespace(
            workdir=str(tmp_path),
            backend_mode="local",
            mode="poll",
            read_timeout_s=0.1,  # shorter timeout for test speed
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=0.001,  # very short
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
            subscribe=True,
        )
        with mock.patch(
            "asyncio.create_subprocess_exec",
            new_callable=mock.AsyncMock,
        ) as mock_create:
            mock_proc = mock.AsyncMock()
            mock_proc.stdin = mock.AsyncMock()
            mock_proc.stdout = mock.AsyncMock()
            mock_create.return_value = mock_proc

            call_count = 0

            async def fake_request(self, op, payload, **kw):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {"ok": True, "payload": {"status": "running"}}
                return {"ok": True, "payload": {"run_id": "r1", "status": "running"}}

            async def fake_request_stream(self, op, payload, **kw):
                return asyncio.Queue()  # never gets anything

            with (
                mock.patch.object(
                    AsyncHostClient, "request", new=fake_request
                ),
                mock.patch.object(
                    AsyncHostClient, "request_stream", new=fake_request_stream
                ),
            ):
                result = asyncio.run(_run_demo_async_stdio(args))
        assert result == 3
        assert "timed out" in capsys.readouterr().out

    def test_subscribe_remaining_deadline_returns_3(self, tmp_path: Path, capsys):
        """subscribe mode returns immediately when the computed wait deadline has elapsed."""
        from toas.cli_demo_async_client import _run_demo_async_stdio

        args = argparse.Namespace(
            workdir=str(tmp_path),
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=1.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
            subscribe=True,
        )
        with mock.patch(
            "asyncio.create_subprocess_exec",
            new_callable=mock.AsyncMock,
        ) as mock_create:
            mock_proc = mock.AsyncMock()
            mock_proc.stdin = mock.AsyncMock()
            mock_proc.stdout = mock.AsyncMock()
            mock_create.return_value = mock_proc

            call_count = 0

            async def fake_request(self, op, payload, **kw):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {"ok": True, "payload": {"status": "running"}}
                return {"ok": True, "payload": {"run_id": "r1", "status": "running"}}

            async def fake_request_stream(self, op, payload, **kw):
                return asyncio.Queue()

            with (
                mock.patch.object(
                    AsyncHostClient, "request", new=fake_request
                ),
                mock.patch.object(
                    AsyncHostClient, "request_stream", new=fake_request_stream
                ),
                mock.patch(
                    "toas.cli_demo_async_client.time.time",
                    side_effect=[100.0, 100.5, 101.1],
                ),
            ):
                result = asyncio.run(_run_demo_async_stdio(args))
        assert result == 3
        assert "timed out" in capsys.readouterr().out

    def test_stream_read_failure_returns_2(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo_async_stdio

        args = argparse.Namespace(
            workdir=str(tmp_path),
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
            subscribe=False,
        )
        with mock.patch(
            "asyncio.create_subprocess_exec",
            new_callable=mock.AsyncMock,
        ) as mock_create:
            mock_proc = mock.AsyncMock()
            mock_proc.stdin = mock.AsyncMock()
            mock_proc.stdout = mock.AsyncMock()
            mock_create.return_value = mock_proc

            call_count = 0

            async def fake_request(self, op, payload, **kw):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {"ok": True, "payload": {"status": "running"}}
                elif call_count == 2:
                    return {"ok": True, "payload": {"run_id": "r1", "status": "running"}}
                return {"ok": False, "error": "read error"}

            with mock.patch.object(
                AsyncHostClient, "request", new=fake_request
            ):
                result = asyncio.run(_run_demo_async_stdio(args))
        assert result == 2
        assert "stream_read failed" in capsys.readouterr().out

    def test_timeout_returns_3(self, tmp_path: Path, capsys):
        from toas.cli_demo_async_client import _run_demo_async_stdio

        args = argparse.Namespace(
            workdir=str(tmp_path),
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=0.001,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
            subscribe=False,
        )
        with mock.patch(
            "asyncio.create_subprocess_exec",
            new_callable=mock.AsyncMock,
        ) as mock_create:
            mock_proc = mock.AsyncMock()
            mock_proc.stdin = mock.AsyncMock()
            mock_proc.stdout = mock.AsyncMock()
            mock_create.return_value = mock_proc

            call_count = 0

            async def fake_request(self, op, payload, **kw):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {"ok": True, "payload": {"status": "running"}}
                elif call_count == 2:
                    return {"ok": True, "payload": {"run_id": "r1", "status": "running"}}
                return {
                    "ok": True,
                    "payload": {"status": "running", "next_offset": 1, "next_seq": 1},
                }

            with mock.patch.object(
                AsyncHostClient, "request", new=fake_request
            ):
                result = asyncio.run(_run_demo_async_stdio(args))
        assert result == 3
        assert "timed out" in capsys.readouterr().out

    def test_client_close_called_in_finally(self, tmp_path: Path):
        """client.close() is called in the finally block."""
        from toas.cli_demo_async_client import _run_demo_async_stdio

        args = argparse.Namespace(
            workdir=str(tmp_path),
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
            subscribe=False,
        )
        with mock.patch(
            "asyncio.create_subprocess_exec",
            new_callable=mock.AsyncMock,
        ) as mock_create:
            mock_proc = mock.AsyncMock()
            mock_proc.stdin = mock.AsyncMock()
            mock_proc.stdout = mock.AsyncMock()
            mock_create.return_value = mock_proc

            async def fake_request(self, op, payload, **kw):
                return {"ok": False, "error": "boom"}  # probe fails -> returns 2

            with mock.patch.object(
                AsyncHostClient, "request", new=fake_request
            ):
                with mock.patch.object(
                    AsyncHostClient, "close", new_callable=mock.AsyncMock
                ) as mock_close:
                    asyncio.run(_run_demo_async_stdio(args))
                    mock_close.assert_called_once()

    def test_proc_terminate_in_finally_if_still_alive(self, tmp_path: Path):
        """If proc is still alive, terminate + wait is called in finally."""
        from toas.cli_demo_async_client import _run_demo_async_stdio

        args = argparse.Namespace(
            workdir=str(tmp_path),
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
            subscribe=False,
        )
        with mock.patch(
            "asyncio.create_subprocess_exec",
            new_callable=mock.AsyncMock,
        ) as mock_create:
            mock_proc = mock.AsyncMock()
            mock_proc.stdin = mock.AsyncMock()
            mock_proc.stdout = mock.AsyncMock()
            mock_proc.terminate = mock.Mock()
            mock_proc.returncode = None  # still alive
            mock_create.return_value = mock_proc

            async def fake_request(self, op, payload, **kw):
                return {"ok": False, "error": "boom"}

            with mock.patch.object(
                AsyncHostClient, "request", new=fake_request
            ):
                asyncio.run(_run_demo_async_stdio(args))
                mock_proc.terminate.assert_called_once()

    def test_proc_not_terminated_if_already_dead(self, tmp_path: Path):
        """If proc.returncode is set, terminate is not called."""
        from toas.cli_demo_async_client import _run_demo_async_stdio

        args = argparse.Namespace(
            workdir=str(tmp_path),
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=False,
            subscribe=False,
        )
        with mock.patch(
            "asyncio.create_subprocess_exec",
            new_callable=mock.AsyncMock,
        ) as mock_create:
            mock_proc = mock.AsyncMock()
            mock_proc.stdin = mock.AsyncMock()
            mock_proc.stdout = mock.AsyncMock()
            mock_proc.returncode = 0  # already dead
            mock_create.return_value = mock_proc

            async def fake_request(self, op, payload, **kw):
                return {"ok": False, "error": "boom"}

            with mock.patch.object(
                AsyncHostClient, "request", new=fake_request
            ):
                asyncio.run(_run_demo_async_stdio(args))
                mock_proc.terminate.assert_not_called()

    def test_ignore_owner_check_sets_env(self, tmp_path: Path):
        """ignore_owner_check=True sets TOAS_HOST_IGNORE_OWNER_CHECK in env."""
        from toas.cli_demo_async_client import _run_demo_async_stdio

        args = argparse.Namespace(
            workdir=str(tmp_path),
            backend_mode="local",
            mode="poll",
            read_timeout_s=1.0,
            request_timeout_s=5.0,
            poll_interval_s=0.1,
            max_seconds=2.0,
            host_cmd=["toas", "host", "serve", "--stdio-json"],
            ignore_owner_check=True,
            subscribe=False,
        )
        with mock.patch(
            "asyncio.create_subprocess_exec",
            new_callable=mock.AsyncMock,
        ) as mock_create:
            mock_proc = mock.AsyncMock()
            mock_proc.stdin = mock.AsyncMock()
            mock_proc.stdout = mock.AsyncMock()
            mock_create.return_value = mock_proc

            async def fake_request(self, op, payload, **kw):
                return {"ok": False, "error": "boom"}

            with mock.patch.object(
                AsyncHostClient, "request", new=fake_request
            ):
                asyncio.run(_run_demo_async_stdio(args))

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["env"].get("TOAS_HOST_IGNORE_OWNER_CHECK") == "1"

# ---------------------------------------------------------------------------
# AsyncHostClient (existing cancel contract test)
# ---------------------------------------------------------------------------

SCRIPT = r"""
import json
import sys

state = {"cancelled": False}

def emit(frame):
    sys.stdout.write(json.dumps(frame) + "\n")
    sys.stdout.flush()

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    req = json.loads(line)
    rid = req.get("request_id", "req")
    op = req.get("op")
    payload = req.get("payload") or {}
    run_id = payload.get("run_id", "run-1")
    if op == "status":
        emit({"protocol_version": 1, "request_id": rid, "ok": True, "payload": {"status": "running"}})
    elif op == "step_async":
        state["cancelled"] = False
        emit({"protocol_version": 1, "request_id": rid, "ok": True, "payload": {"run_id": run_id, "status": "running"}})
    elif op == "cancel":
        state["cancelled"] = True
        emit(
            {
                "protocol_version": 1,
                "request_id": rid,
                "ok": True,
                "payload": {
                    "run_id": run_id,
                    "status": "cancelling",
                    "envelope": {"kind": "cancel", "payload": {"status": "cancelling", "cancel_of": run_id}},
                },
            }
        )
    elif op == "stream_subscribe":
        emit({"protocol_version": 1, "request_id": rid, "ok": True, "payload": {"kind": "push_ack", "run_id": run_id}})
        emit(
            {
                "protocol_version": 1,
                "request_id": rid,
                "ok": True,
                "payload": {
                    "kind": "push_event",
                    "run_id": run_id,
                    "event": {"type": "llm_delta", "lane": "llm_answer", "phase": "delta", "seq": 1, "payload": {"text": "partial answer"}},
                },
            }
        )
        status = "cancelled" if state["cancelled"] else "succeeded"
        emit(
            {
                "protocol_version": 1,
                "request_id": rid,
                "ok": True,
                "payload": {
                    "kind": "push_event",
                    "run_id": run_id,
                    "event": {"type": "llm_done", "lane": "llm_answer", "phase": "end", "seq": 2, "payload": {"status": status}},
                },
            }
        )
        emit(
            {
                "protocol_version": 1,
                "request_id": rid,
                "ok": True,
                "payload": {"kind": "push_complete", "run_id": run_id, "complete": True, "reason": "terminal_event"},
            }
        )
    else:
        emit({"protocol_version": 1, "request_id": rid, "ok": False, "error": {"code": "bad_op", "message": op}})
"""


async def _run_cancel_contract_scenario(tmp_path: Path) -> None:
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-u",
        "-c",
        SCRIPT,
        cwd=str(tmp_path),
        env=dict(os.environ),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    client = AsyncHostClient(proc, request_timeout_s=5.0)
    try:
        run_id = "run-cancel-1"
        start = await client.request("step_async", {"run_id": run_id}, request_id="req-step")
        assert start["ok"] is True
        assert (start.get("payload") or {}).get("status") == "running"

        cancel = await client.request("cancel", {"run_id": run_id}, request_id="req-cancel")
        cancel_payload = cancel.get("payload") or {}
        assert cancel_payload.get("status") == "cancelling"
        assert ((cancel_payload.get("envelope") or {}).get("kind")) == "cancel"

        stream = await client.request_stream(
            "stream_subscribe",
            {"run_id": run_id, "timeout_s": 2.0},
            request_id="req-subscribe",
        )

        first = await asyncio.wait_for(stream.get(), timeout=2.0)
        assert (first.get("payload") or {}).get("kind") == "push_ack"

        delta = await asyncio.wait_for(stream.get(), timeout=2.0)
        delta_event = ((delta.get("payload") or {}).get("event") or {})
        assert delta_event.get("lane") == "llm_answer"
        assert delta_event.get("phase") == "delta"
        assert (delta_event.get("payload") or {}).get("text") == "partial answer"

        end = await asyncio.wait_for(stream.get(), timeout=2.0)
        end_event = ((end.get("payload") or {}).get("event") or {})
        assert end_event.get("lane") == "llm_answer"
        assert end_event.get("phase") == "end"
        assert (end_event.get("payload") or {}).get("status") == "cancelled"

        done = await asyncio.wait_for(stream.get(), timeout=2.0)
        done_payload = done.get("payload") or {}
        assert done_payload.get("kind") == "push_complete"
        assert done_payload.get("complete") is True
        assert done_payload.get("reason") == "terminal_event"
    finally:
        await client.close()
        if proc.returncode is None:
            proc.terminate()
            await proc.wait()


def test_async_client_cancel_contract_shapes_terminal_with_truncated_answer(tmp_path: Path) -> None:
    asyncio.run(_run_cancel_contract_scenario(tmp_path))
