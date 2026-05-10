from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import coverage


@dataclass(frozen=True)
class CoverageFileStats:
    measured_files: int
    files_below_full: int


def coverage_file_stats(data_file: str | Path = ".coverage") -> CoverageFileStats:
    cov = coverage.Coverage(data_file=str(data_file))
    cov.load()
    measured = list(cov.get_data().measured_files())
    files_below_full = 0
    for filename in measured:
        _, statements, excluded, missing, _ = cov.analysis2(filename)
        relevant = len(statements) - len(excluded)
        if relevant <= 0:
            continue
        if len(missing) > 0:
            files_below_full += 1
    return CoverageFileStats(measured_files=len(measured), files_below_full=files_below_full)
