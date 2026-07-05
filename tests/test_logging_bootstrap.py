import logging

import pytest

from toas.config import DiagnosticsPolicy
from toas.runtime.logging_bootstrap import configure_logging


def test_configure_logging_sets_warning_level_by_default():
    configure_logging(DiagnosticsPolicy())
    assert logging.getLogger().level == logging.WARNING


def test_configure_logging_sets_debug_level():
    configure_logging(DiagnosticsPolicy(log_level="DEBUG"))
    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_unknown_level_falls_back_to_warning():
    configure_logging(DiagnosticsPolicy(log_level="NOTAREAL"))
    assert logging.getLogger().level == logging.WARNING


def test_configure_logging_file_handler(tmp_path):
    log_file = tmp_path / "toas.log"
    configure_logging(DiagnosticsPolicy(log_level="DEBUG", log_file=str(log_file)))
    logger = logging.getLogger("toas.test_bootstrap")
    logger.debug("test message")
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "test message" in content


def test_configure_logging_no_file_uses_stream_handler():
    configure_logging(DiagnosticsPolicy(log_level="WARNING"))
    root = logging.getLogger()
    handler_types = [type(h).__name__ for h in root.handlers]
    assert "StreamHandler" in handler_types or "FileHandler" not in handler_types


def test_configure_logging_bad_file_path_raises():
    with pytest.raises(OSError):
        configure_logging(DiagnosticsPolicy(log_level="DEBUG", log_file="/no/such/dir/toas.log"))
