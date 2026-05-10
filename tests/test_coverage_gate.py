from __future__ import annotations

import sys
from pathlib import Path

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
