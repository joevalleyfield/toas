"""Real terminal execution for Vim drivers: POSIX PTY or Windows ConPTY."""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pexpect

EOF = pexpect.EOF


class WindowsTerminal:
    def __init__(self, command, args, *, cwd, env, timeout):
        from winpty import Backend, PtyProcess

        command = shutil.which(command, path=env.get("PATH")) or command
        self.log_path = None
        if "-S" in args:
            self.log_path = Path(args[args.index("-S") + 1]).with_suffix(".log")
            args = [*args, "-V1" + self.log_path.as_posix()]
        argv = [command, *args]
        if command.lower().endswith((".bat", ".cmd")):
            argv = [env.get("COMSPEC", "cmd.exe"), "/d", "/c", *argv]
        self.process = PtyProcess.spawn(argv, cwd=cwd, env=env, backend=Backend.ConPTY)
        self.timeout = timeout
        self.before = ""
        self.exitstatus = None
        self.signalstatus = None

    def send(self, text):
        # Match pexpect's pacing so Vim can process mode switches between sends.
        time.sleep(0.05)
        return self.process.write(text)

    def expect(self, pattern):
        if pattern is not EOF:
            raise ValueError("Vim drivers only wait for terminal EOF")
        deadline = time.monotonic() + self.timeout
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Vim terminal deadline exceeded")
                self.process.fileobj.settimeout(min(remaining, 0.1))
                try:
                    self.before += self.process.read(65536)
                except EOFError:
                    break
                except TimeoutError:
                    # ConPTY can retain its output handle after the process exits.
                    # A quiet pipe plus a real exit status is terminal completion.
                    if not self.process.isalive():
                        break
            while self.process.isalive():
                if time.monotonic() >= deadline:
                    raise TimeoutError("Vim stayed alive after terminal EOF")
                time.sleep(0.01)
            self.exitstatus = self.process.exitstatus
        except TimeoutError as exc:
            self.close()
            log = self.log_path.read_text(encoding="utf-8", errors="replace") if self.log_path and self.log_path.exists() else ""
            if self.log_path:
                for path in (self.log_path.parent / ".toas").glob("*.log"):
                    log += path.name + ": " + path.read_text(encoding="utf-8", errors="replace")[-3000:]
            raise TimeoutError(f"Vim terminal timed out; log: {log[-3000:]!r}; output tail: {self.before[-1000:]!r}") from exc
        except Exception:
            self.close()
            raise

    def close(self):
        if self.process.isalive():
            subprocess.run(
                ["taskkill", "/pid", str(self.process.pid), "/t", "/f"],
                capture_output=True, timeout=5, check=False,
            )
        self.exitstatus = self.process.exitstatus
        self.process.fileobj.close()
        self.process._server.close()


def spawn(command, args, *, encoding="utf-8", timeout=10, cwd=None, env=None):
    if command == "vim":
        command = os.environ.get("TOAS_TEST_VIM_BIN", command)
    if os.name != "nt":
        return pexpect.spawn(command, args, encoding=encoding, timeout=timeout, cwd=cwd, env=env)
    return WindowsTerminal(command, args, cwd=cwd, env=dict(env or os.environ), timeout=timeout)
