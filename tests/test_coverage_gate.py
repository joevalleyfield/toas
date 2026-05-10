from __future__ import annotations

import sys
from pathlib import Path

import pytest

from toas.coverage_gate import coverage_file_stats


def test_coverage_file_stats_counts_partial_file(tmp_path: Path) -> None:
    mod = tmp_path / "mod.py"
    mod.write_text(
        "def f(x):\n"
        "    if x:\n"
        "        return 1\n"
        "    return 0\n",
        encoding="utf-8",
    )
    script = tmp_path / "run_mod.py"
    script.write_text(
        "from mod import f\n"
        "f(True)\n",
        encoding="utf-8",
    )

    import coverage

    cov_file = tmp_path / ".coverage"
    cov = coverage.Coverage(data_file=str(cov_file))
    sys.path.insert(0, str(tmp_path))
    cov.start()
    namespace: dict[str, object] = {}
    exec(compile(script.read_text(encoding="utf-8"), str(script), "exec"), namespace, namespace)
    cov.stop()
    cov.save()
    sys.path.remove(str(tmp_path))

    stats = coverage_file_stats(cov_file)
    assert stats.measured_files >= 1
    assert stats.files_below_full >= 1


def test_coverage_file_stats_skips_files_with_no_relevant_statements(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeData:
        def measured_files(self) -> list[str]:
            return ["only_excluded.py"]

    class _FakeCoverage:
        def __init__(self, *, data_file: str) -> None:
            self.data_file = data_file

        def load(self) -> None:
            return None

        def get_data(self) -> _FakeData:
            return _FakeData()

        def analysis2(self, filename: str):
            assert filename == "only_excluded.py"
            statements = [1]
            excluded = [1]
            missing: list[int] = []
            return filename, statements, excluded, missing, ""

    import toas.coverage_gate as coverage_gate

    monkeypatch.setattr(coverage_gate.coverage, "Coverage", _FakeCoverage)
    stats = coverage_file_stats(".coverage")
    assert stats.measured_files == 1
    assert stats.files_below_full == 0
