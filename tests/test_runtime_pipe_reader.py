import io
from threading import Event

import pytest

from toas.runtime.pipe_reader import PipeReader


def test_pipe_reader_drains_all_bytes_before_persistent_eof():
    reader = PipeReader(io.BytesIO(b"abc"))
    assert [reader.read(timeout_s=1) for _ in range(3)] == [b"a", b"b", b"c"]
    assert reader.read(timeout_s=1) == b""
    assert reader.read(timeout_s=0) == b""


def test_pipe_reader_deadline_does_not_wait_for_child_eof():
    release = Event()

    class Blocked:
        def read(self, _size):
            release.wait(2)
            return b""

    reader = PipeReader(Blocked())
    try:
        assert reader.read(timeout_s=0.01) is None
    finally:
        release.set()
    assert reader.read(timeout_s=1) == b""


def test_pipe_reader_reports_read_error():
    class Broken:
        def read(self, _size):
            raise OSError("broken pipe")

    reader = PipeReader(Broken())
    with pytest.raises(OSError, match="broken pipe"):
        reader.read(timeout_s=1)
    assert reader.read(timeout_s=0) == b""
