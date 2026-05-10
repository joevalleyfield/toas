from __future__ import annotations

import pytest

from toas.cli_analysis_commands import run_diff_local


def test_run_diff_local_raises_when_head_b_missing():
    with pytest.raises(SystemExit, match="no message found with id: b"):
        run_diff_local(
            ensure_file=lambda _p: None,
            resolve_events_path=lambda: "events.jsonl",
            read_log=lambda _p: [{"id": "n0"}],
            message_lineage=lambda _events, head_id: [{"id": "n0"}] if head_id == "a" else [],
            build_runtime_diff_lines=lambda **_k: [],
            provenance_marker_fn=lambda _m: "",
            format_content_fn=lambda _c: "",
            head_a="a",
            head_b="b",
            full=False,
            print_fn=lambda _line: None,
        )
