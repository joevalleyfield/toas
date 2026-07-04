from __future__ import annotations

from pathlib import Path

from toas import cli_session_views as views


def test_run_history_threads_source_tokens() -> None:
    seen: dict[str, object] = {}

    def _ensure_file(path: Path) -> None:
        seen["ensured"] = path

    def _resolve_events_path() -> Path:
        return Path(".toas/events.jsonl")

    class _Outcome:
        lines = ["history: ok"]

    def _history_lines(**kwargs):
        seen["history_kwargs"] = kwargs
        return _Outcome()

    out: list[str] = []
    views.run_history(
        ensure_file=_ensure_file,
        resolve_events_path=_resolve_events_path,
        operator_history_lines=_history_lines,
        limit=5,
        source_tokens=["segments", "hot"],
        print_fn=out.append,
    )

    assert seen == {
        "ensured": Path(".toas/events.jsonl"),
        "history_kwargs": {
            "events_path": Path(".toas/events.jsonl"),
            "limit": 5,
            "source_tokens": ["segments", "hot"],
            "head_id": None,
        },
    }
    assert out == ["history: ok"]


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
