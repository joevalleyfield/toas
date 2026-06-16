from __future__ import annotations

from pathlib import Path

from toas import cli_session_views as views


def test_run_session_path_prints_resolved_path() -> None:
    calls: list[object] = []

    def _ensure_file(_path: Path) -> None:
        calls.append("ensure")

    def _resolve_events_path() -> Path:
        return Path(".toas/events.jsonl")

    def _read_log(_path: str) -> list[dict]:
        calls.append("read")
        return [{"id": "n1"}]

    def _resolve_session_path(_events: list[dict]) -> Path:
        return Path(".toas/session-a.md")

    out: list[str] = []
    views.run_session_path(
        ensure_file=_ensure_file,
        resolve_events_path=_resolve_events_path,
        read_log=_read_log,
        resolve_session_path=_resolve_session_path,
        print_fn=out.append,
    )
    assert out == [".toas/session-a.md"]
    assert calls == ["ensure", "read"]


def test_run_prompts_formats_with_and_without_category() -> None:
    class _Asset:
        def __init__(self, ref: str, metadata: dict):
            self.ref = ref
            self.metadata = metadata

    def _list_prompt_assets(_prefix):
        return [
            _Asset("dynamic/foo", {"name": "Foo", "description": "first", "category": "dynamic"}),
            _Asset("protocol/bar", {"name": "Bar", "description": "second"}),
        ]

    lines: list[str] = []
    views.run_prompts(list_prompt_assets=_list_prompt_assets, prefix=None, print_fn=lines.append)
    assert lines == [
        "dynamic/foo\t[dynamic] Foo\tfirst",
        "protocol/bar\tBar\tsecond",
    ]
