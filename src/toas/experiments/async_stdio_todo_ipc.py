from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class TodoServerState:
    todos: list[dict[str, Any]]
    next_id: int = 1


async def _run_server() -> int:
    state = TodoServerState(todos=[])
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    loop = asyncio.get_running_loop()
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    transport, _ = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, sys.stdout)
    writer = asyncio.StreamWriter(transport, protocol, reader, loop)

    while True:
        line = await reader.readline()
        if not line:
            return 0
        try:
            req = json.loads(line.decode("utf-8"))
            req_id = req.get("id")
            cmd = req.get("cmd")
            args = req.get("args") or {}
            resp: dict[str, Any]
            if cmd == "add":
                text = str(args.get("text", "")).strip()
                if not text:
                    resp = {"id": req_id, "ok": False, "error": "text required"}
                else:
                    item = {"id": state.next_id, "text": text, "done": False}
                    state.next_id += 1
                    state.todos.append(item)
                    await asyncio.sleep(0.02)
                    resp = {"id": req_id, "ok": True, "todo": item}
            elif cmd == "list":
                await asyncio.sleep(0.01)
                resp = {"id": req_id, "ok": True, "todos": list(state.todos)}
            elif cmd == "done":
                todo_id = int(args.get("id", 0))
                found = next((t for t in state.todos if int(t["id"]) == todo_id), None)
                if not found:
                    resp = {"id": req_id, "ok": False, "error": "not found"}
                else:
                    found["done"] = True
                    await asyncio.sleep(0.02)
                    resp = {"id": req_id, "ok": True, "todo": found}
            elif cmd == "shutdown":
                resp = {"id": req_id, "ok": True, "bye": True}
                writer.write((json.dumps(resp) + "\n").encode("utf-8"))
                await writer.drain()
                return 0
            else:
                resp = {"id": req_id, "ok": False, "error": f"unknown cmd: {cmd}"}
        except Exception as exc:
            resp = {"id": None, "ok": False, "error": f"decode/dispatch error: {exc}"}
        writer.write((json.dumps(resp) + "\n").encode("utf-8"))
        await writer.drain()


class TodoClientSession:
    def __init__(self, proc: asyncio.subprocess.Process):
        self._proc = proc

    async def request(self, cmd: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        req_id = str(uuid.uuid4())
        payload = {"id": req_id, "cmd": cmd, "args": args or {}}
        assert self._proc.stdin is not None
        assert self._proc.stdout is not None
        self._proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
        await self._proc.stdin.drain()
        line = await self._proc.stdout.readline()
        if not line:
            raise RuntimeError("server closed output stream")
        resp = json.loads(line.decode("utf-8"))
        if resp.get("id") != req_id:
            raise RuntimeError(f"request/response id mismatch: {resp.get('id')} != {req_id}")
        return resp

    async def close(self) -> None:
        if self._proc.returncode is None:
            try:
                await self.request("shutdown")
            except Exception:
                pass
            await self._proc.wait()


async def open_todo_client(*, python: str | None = None) -> TodoClientSession:
    py = python or sys.executable
    proc = await asyncio.create_subprocess_exec(
        py,
        "-m",
        "toas.experiments.async_stdio_todo_ipc",
        "--server",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    return TodoClientSession(proc)


async def demo_client_session() -> int:
    session = await open_todo_client()
    try:
        print(await session.request("add", {"text": "write protocol sketch"}))
        print(await session.request("add", {"text": "exercise io-bound loop"}))
        print(await session.request("list"))
        print(await session.request("done", {"id": 1}))
        print(await session.request("list"))
    finally:
        await session.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Async stdio todo IPC experiment")
    parser.add_argument("--server", action="store_true", help="Run server mode on stdin/stdout")
    parser.add_argument("--demo", action="store_true", help="Run a demo client session")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.server:
        return asyncio.run(_run_server())
    if args.demo:
        return asyncio.run(demo_client_session())
    print("usage: pass --server or --demo", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
