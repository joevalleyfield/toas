import os
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from ..graph import write_backend_lifecycle_record

_MANAGED_BACKEND: subprocess.Popen | None = None
_MANAGED_BACKEND_LOCK = threading.Lock()

def _events_path_for_workdir(workdir: str) -> str:
    return str(Path(workdir) / "events.jsonl")

def _write_backend_event(
    workdir: str,
    *,
    action: str,
    status: str,
    mode: str,
    pid: int | None = None,
    detail: str | None = None,
) -> None:
    try:
        write_backend_lifecycle_record(
            _events_path_for_workdir(workdir),
            action=action,
            status=status,
            mode=mode,
            pid=pid,
            detail=detail,
        )
    except Exception:
        return

def _health_ok(health_url: str, timeout_s: float) -> bool:
    if not health_url:
        return True
    try:
        with urllib.request.urlopen(health_url, timeout=timeout_s) as response:
            status = getattr(response, "status", 200)
            return int(status) < 400
    except Exception:
        return False

def _managed_backend_status(*, mode: str, workdir: str) -> dict:
    global _MANAGED_BACKEND
    if mode != "managed-local":
        return {"mode": mode, "managed": False, "status": "external"}
    with _MANAGED_BACKEND_LOCK:
        proc = _MANAGED_BACKEND
        if proc is None:
            return {"mode": mode, "managed": True, "status": "stopped"}
        code = proc.poll()
        if code is None:
            return {"mode": mode, "managed": True, "status": "running", "pid": proc.pid}
        return {"mode": mode, "managed": True, "status": "failed", "pid": proc.pid, "detail": f"exit={code}"}

def _managed_backend_start(payload: dict) -> dict:
    global _MANAGED_BACKEND
    mode = str(payload.get("mode", "external")).strip() or "external"
    workdir = str(payload.get("workdir", Path.cwd().resolve()))
    if mode != "managed-local":
        result = {"mode": mode, "managed": False, "status": "external"}
        _write_backend_event(workdir, action="start", status="skipped", mode=mode, detail="mode is external")
        return result
    command_raw = payload.get("command", [])
    command = [str(part) for part in command_raw] if isinstance(command_raw, list) else []
    if not command:
        raise RuntimeError("managed-local backend requires non-empty command")
    cwd_raw = payload.get("cwd")
    launch_cwd = str(Path(cwd_raw).resolve()) if isinstance(cwd_raw, str) and cwd_raw else workdir
    health_url = str(payload.get("health_url", "")).strip()
    health_timeout_s = float(payload.get("health_timeout_s", 15.0))
    env_overlay_raw = payload.get("env", {})
    env_overlay: dict[str, str] = {}
    if isinstance(env_overlay_raw, dict):
        for key, value in env_overlay_raw.items():
            key_s = str(key).strip()
            if key_s:
                env_overlay[key_s] = str(value)

    with _MANAGED_BACKEND_LOCK:
        if _MANAGED_BACKEND is not None and _MANAGED_BACKEND.poll() is None:
            return {"mode": mode, "managed": True, "status": "running", "pid": _MANAGED_BACKEND.pid}
        launch_env = os.environ.copy()
        launch_env.update(env_overlay)
        proc = subprocess.Popen(
            command,
            cwd=launch_cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=launch_env,
        )
        _MANAGED_BACKEND = proc
    deadline = time.time() + max(1.0, health_timeout_s)
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        if _health_ok(health_url, min(1.0, max(0.1, health_timeout_s))):
            _write_backend_event(workdir, action="start", status="ok", mode=mode, pid=proc.pid)
            return {"mode": mode, "managed": True, "status": "running", "pid": proc.pid}
        time.sleep(0.1)
    try:
        proc.terminate()
    except Exception:
        pass
    _write_backend_event(workdir, action="start", status="error", mode=mode, pid=proc.pid, detail="healthcheck failed")
    raise RuntimeError("managed-local backend failed health check")

def _managed_backend_stop(payload: dict, has_active_runs_fn) -> dict:
    global _MANAGED_BACKEND
    mode = str(payload.get("mode", "external")).strip() or "external"
    workdir = str(payload.get("workdir", Path.cwd().resolve()))
    if mode != "managed-local":
        result = {"mode": mode, "managed": False, "status": "external"}
        _write_backend_event(workdir, action="stop", status="skipped", mode=mode, detail="mode is external")
        return result
    if has_active_runs_fn():
        raise RuntimeError("backend stop blocked: active run in progress")
    with _MANAGED_BACKEND_LOCK:
        proc = _MANAGED_BACKEND
        if proc is None or proc.poll() is not None:
            _MANAGED_BACKEND = None
            _write_backend_event(workdir, action="stop", status="ok", mode=mode, detail="already stopped")
            return {"mode": mode, "managed": True, "status": "stopped"}
        try:
            proc.terminate()
            proc.wait(timeout=2.0)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        _MANAGED_BACKEND = None
    _write_backend_event(workdir, action="stop", status="ok", mode=mode, detail="stopped")
    return {"mode": mode, "managed": True, "status": "stopped"}

def _managed_backend_restart(payload: dict, has_active_runs_fn) -> dict:
    mode = str(payload.get("mode", "external")).strip() or "external"
    workdir = str(payload.get("workdir", Path.cwd().resolve()))
    if has_active_runs_fn():
        raise RuntimeError("backend restart blocked: active run in progress")
    _managed_backend_stop(payload, has_active_runs_fn)
    result = _managed_backend_start(payload)
    _write_backend_event(workdir, action="restart", status="ok", mode=mode, pid=result.get("pid"))
    return result
