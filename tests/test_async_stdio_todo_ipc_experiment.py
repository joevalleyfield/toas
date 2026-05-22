from __future__ import annotations

import asyncio

from toas.experiments.async_stdio_todo_ipc import open_todo_client


def test_async_stdio_todo_ipc_session_roundtrip() -> None:
    async def _run() -> None:
        client = await open_todo_client()
        try:
            add1 = await client.request("add", {"text": "alpha"})
            assert add1["ok"] is True
            assert (add1["todo"] or {})["id"] == 1

            add2 = await client.request("add", {"text": "beta"})
            assert add2["ok"] is True
            assert (add2["todo"] or {})["id"] == 2

            listing = await client.request("list")
            assert listing["ok"] is True
            assert len(listing["todos"]) == 2

            done = await client.request("done", {"id": 2})
            assert done["ok"] is True
            assert done["todo"]["done"] is True

            final = await client.request("list")
            assert [todo["done"] for todo in final["todos"]] == [False, True]
        finally:
            await client.close()

    asyncio.run(_run())
