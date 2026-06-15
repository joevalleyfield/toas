from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BackendLifecycleRequest:
    workdir: Path
    mode: str
    command: tuple[str, ...]
    cwd: Path
    env: dict[str, str]
    health_url: str
    health_timeout_s: float
    fingerprint: str = ""


@dataclass(frozen=True)
class BackendLifecycleResult:
    mode: str
    status: str
    pid: int | None = None
    detail: str | None = None


@dataclass
class _BackendProcessState:
    proc: subprocess.Popen | None = None
    fingerprint: str | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


class ModelBackendLifecycle:
    """Workspace-scoped model-serving process lifecycle domain.

    One instance should be shared across adapters for a given process; it is
    not workspace-keyed internally because the caller (CLI, daemon adapter, host)
    is responsible for selecting the right instance. If multi-workspace support is
    needed later, a registry keyed by workdir belongs above this class.
    """

    def __init__(
        self,
        *,
        spawn_fn: Callable[..., subprocess.Popen] = subprocess.Popen,
        health_probe_fn: Callable[[str, float], bool] | None = None,
        event_writer_fn: Callable[..., None] | None = None,
        active_runs_fn: Callable[[], bool] | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        time_fn: Callable[[], float] = time.time,
    ) -> None:
        self._spawn = spawn_fn
        self._health_probe = health_probe_fn or _default_health_probe
        self._write_event = event_writer_fn or _noop_event_writer
        self._has_active_runs = active_runs_fn or (lambda: False)
        self._sleep = sleep_fn
        self._time = time_fn
        self._state = _BackendProcessState()

    def status(self, request: BackendLifecycleRequest) -> BackendLifecycleResult:
        if request.mode != "managed-local":
            return BackendLifecycleResult(mode=request.mode, status="external")
        with self._state.lock:
            res = self._read_process_status(request.mode)
            if (
                res.status == "running"
                and self._state.fingerprint is not None
                and request.fingerprint
                and self._state.fingerprint != request.fingerprint
            ):
                return BackendLifecycleResult(
                    mode=res.mode,
                    status="stale",
                    pid=res.pid,
                    detail="configuration mismatch (restart required)",
                )
            return res

    def start(self, request: BackendLifecycleRequest) -> BackendLifecycleResult:
        if request.mode != "managed-local":
            logger.debug("backend start skipped mode=%s workdir=%s", request.mode, request.workdir)
            self._write_event(request, action="start", status="skipped", detail="mode is external")
            return BackendLifecycleResult(mode=request.mode, status="external")

        if not request.command:
            raise RuntimeError("managed-local backend requires non-empty command")

        with self._state.lock:
            if self._state.proc is not None and self._state.proc.poll() is None:
                pid = self._state.proc.pid
                logger.debug("backend start skipped already_running pid=%d workdir=%s", pid, request.workdir)
                status = "running"
                if (
                    self._state.fingerprint is not None
                    and request.fingerprint
                    and self._state.fingerprint != request.fingerprint
                ):
                    status = "stale"
                return BackendLifecycleResult(mode=request.mode, status=status, pid=pid)

            launch_env = os.environ.copy()
            launch_env.update(request.env)
            proc = self._spawn(
                list(request.command),
                cwd=str(request.cwd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                env=launch_env,
            )
            self._state.proc = proc
            self._state.fingerprint = request.fingerprint

        logger.debug("backend start spawned pid=%d workdir=%s", proc.pid, request.workdir)

        deadline = self._time() + request.health_timeout_s
        while self._time() < deadline:
            if proc.poll() is not None:
                break
            if self._health_probe(request.health_url, min(1.0, max(0.1, request.health_timeout_s))):
                logger.debug("backend start healthy pid=%d workdir=%s", proc.pid, request.workdir)
                self._write_event(request, action="start", status="ok", pid=proc.pid)
                return BackendLifecycleResult(mode=request.mode, status="running", pid=proc.pid)
            self._sleep(0.1)

        try:
            proc.terminate()
        except Exception:
            pass
        logger.debug("backend start health_failed pid=%d workdir=%s", proc.pid, request.workdir)
        self._write_event(request, action="start", status="error", pid=proc.pid, detail="healthcheck failed")
        raise RuntimeError("managed-local backend failed health check")

    def stop(self, request: BackendLifecycleRequest) -> BackendLifecycleResult:
        if request.mode != "managed-local":
            logger.debug("backend stop skipped mode=%s workdir=%s", request.mode, request.workdir)
            self._write_event(request, action="stop", status="skipped", detail="mode is external")
            return BackendLifecycleResult(mode=request.mode, status="external")

        if self._has_active_runs():
            raise RuntimeError("backend stop blocked: active run in progress")

        with self._state.lock:
            proc = self._state.proc
            if proc is None or proc.poll() is not None:
                self._state.proc = None
                logger.debug("backend stop already_stopped workdir=%s", request.workdir)
                self._write_event(request, action="stop", status="ok", detail="already stopped")
                return BackendLifecycleResult(mode=request.mode, status="stopped")

            try:
                proc.terminate()
                proc.wait(timeout=2.0)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            self._state.proc = None

        logger.debug("backend stop ok workdir=%s", request.workdir)
        self._write_event(request, action="stop", status="ok")
        return BackendLifecycleResult(mode=request.mode, status="stopped")

    def restart(self, request: BackendLifecycleRequest) -> BackendLifecycleResult:
        if self._has_active_runs():
            raise RuntimeError("backend restart blocked: active run in progress")
        self.stop(request)
        result = self.start(request)
        logger.debug("backend restart ok pid=%s workdir=%s", result.pid, request.workdir)
        self._write_event(request, action="restart", status="ok", pid=result.pid)
        return result

    def _read_process_status(self, mode: str) -> BackendLifecycleResult:
        proc = self._state.proc
        if proc is None:
            return BackendLifecycleResult(mode=mode, status="stopped")
        code = proc.poll()
        if code is None:
            return BackendLifecycleResult(mode=mode, status="running", pid=proc.pid)
        return BackendLifecycleResult(mode=mode, status="failed", pid=proc.pid, detail=f"exit={code}")


def _default_health_probe(health_url: str, timeout_s: float) -> bool:
    if not health_url:
        return True
    try:
        with urllib.request.urlopen(health_url, timeout=timeout_s) as response:
            return int(getattr(response, "status", 200)) < 400
    except Exception:
        return False


def _noop_event_writer(request: BackendLifecycleRequest, *, action: str, status: str, pid: int | None = None, detail: str | None = None) -> None:
    pass


def make_graph_event_writer(write_record_fn: Callable) -> Callable:
    """Return an event_writer_fn that persists lifecycle facts to the durable graph."""
    def _write(request: BackendLifecycleRequest, *, action: str, status: str, pid: int | None = None, detail: str | None = None) -> None:
        events_path = str(request.workdir / ".toas" / "events.jsonl")
        try:
            write_record_fn(
                events_path,
                action=action,
                status=status,
                mode=request.mode,
                pid=pid,
                detail=detail,
            )
        except Exception:
            logger.debug("backend event write failed action=%s status=%s", action, status)
    return _write


def request_from_payload(payload: dict) -> BackendLifecycleRequest:
    """Construct a BackendLifecycleRequest from a raw daemon/CLI payload dict."""
    mode = str(payload.get("mode", "external")).strip() or "external"
    workdir = Path(str(payload.get("workdir", Path.cwd().resolve()))).resolve()
    command_raw = payload.get("command", [])
    command = tuple(str(p) for p in command_raw) if isinstance(command_raw, list) else ()
    cwd_raw = payload.get("cwd")
    cwd = Path(str(cwd_raw)).resolve() if isinstance(cwd_raw, str) and cwd_raw else workdir
    health_url = str(payload.get("health_url", "")).strip()
    health_timeout_s = float(payload.get("health_timeout_s", 15.0))
    env_raw = payload.get("env", {})
    env: dict[str, str] = {}
    if isinstance(env_raw, dict):
        for k, v in env_raw.items():
            k_s = str(k).strip()
            if k_s:
                env[k_s] = str(v)
    return BackendLifecycleRequest(
        workdir=workdir,
        mode=mode,
        command=command,
        cwd=cwd,
        env=env,
        health_url=health_url,
        health_timeout_s=health_timeout_s,
        fingerprint=str(payload.get("fingerprint", "")).strip(),
    )


def result_to_dict(result: BackendLifecycleResult) -> dict:
    """Serialize a result to the legacy response dict shape."""
    d: dict = {"mode": result.mode, "status": result.status}
    if result.mode == "managed-local":
        d["managed"] = True
    else:
        d["managed"] = False
    if isinstance(result.pid, int):
        d["pid"] = result.pid
    if isinstance(result.detail, str) and result.detail:
        d["detail"] = result.detail
    return d
