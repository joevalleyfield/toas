import os
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from toas.daemon_backend_lifecycle import (
    _health_ok,
    _managed_backend_status,
    _managed_backend_start,
    _managed_backend_stop,
    _managed_backend_restart,
)
import toas.daemon_backend_lifecycle

@pytest.fixture(autouse=True)
def reset_managed_backend():
    toas.daemon_backend_lifecycle._MANAGED_BACKEND = None
    yield
    toas.daemon_backend_lifecycle._MANAGED_BACKEND = None

def test_health_ok_true():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response
        assert _health_ok("http://localhost:8080", 1.0) is True

def test_health_ok_false():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.status = 500
        mock_urlopen.return_value.__enter__.return_value = mock_response
        assert _health_ok("http://localhost:8080", 1.0) is False

def test_health_ok_exception():
    with patch("urllib.request.urlopen", side_effect=Exception("fail")):
        assert _health_ok("http://localhost:8080", 1.0) is False

def test_managed_backend_status_external():
    assert _managed_backend_status(mode="external", workdir=".") == {
        "mode": "external", "managed": False, "status": "external"
    }

def test_managed_backend_status_stopped():
    assert _managed_backend_status(mode="managed-local", workdir=".") == {
        "mode": "managed-local", "managed": True, "status": "stopped"
    }

def test_managed_backend_status_running():
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_proc.pid = 1234
    with patch("toas.daemon_backend_lifecycle._MANAGED_BACKEND", mock_proc):
        assert _managed_backend_status(mode="managed-local", workdir=".") == {
            "mode": "managed-local", "managed": True, "status": "running", "pid": 1234
        }

def test_managed_backend_status_failed():
    mock_proc = MagicMock()
    mock_proc.poll.return_value = 1
    mock_proc.pid = 1234
    with patch("toas.daemon_backend_lifecycle._MANAGED_BACKEND", mock_proc):
        assert _managed_backend_status(mode="managed-local", workdir=".") == {
            "mode": "managed-local", "managed": True, "status": "failed", "pid": 1234, "detail": "exit=1"
        }

@patch("toas.daemon_backend_lifecycle.subprocess.Popen")
@patch("toas.daemon_backend_lifecycle._health_ok")
def test_managed_backend_start_success(mock_health, mock_popen):
    mock_health.return_value = True
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_proc.pid = 1234
    mock_popen.return_value = mock_proc

    payload = {
        "mode": "managed-local",
        "command": ["echo", "hello"],
        "workdir": str(Path.cwd()),
        "health_url": "http://localhost:8080",
        "health_timeout_s": 1.0
    }
    
    result = _managed_backend_start(payload)
    assert result["status"] == "running"
    assert result["pid"] == 1234

def test_managed_backend_start_no_command():
    payload = {
        "mode": "managed-local",
        "command": [],
        "workdir": str(Path.cwd()),
    }
    with pytest.raises(RuntimeError, match="managed-local backend requires non-empty command"):
        _managed_backend_start(payload)

@patch("toas.daemon_backend_lifecycle.subprocess.Popen")
@patch("toas.daemon_backend_lifecycle._health_ok")
def test_managed_backend_start_health_fail(mock_health, mock_popen):
    mock_health.return_value = False
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_popen.return_value = mock_proc

    payload = {
        "mode": "managed-local",
        "command": ["echo", "hello"],
        "workdir": str(Path.cwd()),
        "health_url": "http://localhost:8080",
        "health_timeout_s": 0.2
    }
    
    with pytest.raises(RuntimeError, match="managed-local backend failed health check"):
        _managed_backend_start(payload)

@patch("toas.daemon_backend_lifecycle._managed_backend_start")
@patch("toas.daemon_backend_lifecycle._managed_backend_stop")
def test_managed_backend_restart(mock_stop, mock_start):
    mock_start.return_value = {"pid": 1234}
    payload = {"mode": "managed-local"}
    has_runs_fn = lambda: False

    result = _managed_backend_restart(payload, has_active_runs_fn=has_runs_fn)
    
    mock_stop.assert_called_once_with(payload, has_runs_fn)
    mock_start.assert_called_once_with(payload)
    assert result["pid"] == 1234

def test_managed_backend_stop_blocked():
    payload = {"mode": "managed-local"}
    with pytest.raises(RuntimeError, match="active run in progress"):
        _managed_backend_stop(payload, has_active_runs_fn=lambda: True)

@patch("toas.daemon_backend_lifecycle._managed_backend_stop")
def test_managed_backend_stop_external(mock_stop):
    payload = {"mode": "external"}
    result = _managed_backend_stop(payload, has_active_runs_fn=lambda: False)
    assert result["status"] == "external"
    mock_stop.assert_not_called()

def test_managed_backend_stop_already_stopped():
    with patch("toas.daemon_backend_lifecycle._MANAGED_BACKEND", None):
        payload = {"mode": "managed-local"}
        result = _managed_backend_stop(payload, has_active_runs_fn=lambda: False)
        assert result["status"] == "stopped"

def test_managed_backend_stop_kill_fallback():
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_proc.terminate.side_effect = Exception("terminate failed")
    mock_proc.kill.return_value = None
    
    with patch("toas.daemon_backend_lifecycle._MANAGED_BACKEND", mock_proc):
        payload = {"mode": "managed-local"}
        result = _managed_backend_stop(payload, has_active_runs_fn=lambda: False)
        assert result["status"] == "stopped"
        mock_proc.kill.assert_called_once()

def test_managed_backend_restart_blocked():
    payload = {"mode": "managed-local"}
    with pytest.raises(RuntimeError, match="active run in progress"):
        _managed_backend_restart(payload, has_active_runs_fn=lambda: True)