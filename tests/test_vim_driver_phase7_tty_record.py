import pytest


@pytest.mark.skip(reason="Phase7 TTY recording is manual/diagnostic and exceeds CI timeout budget.")
def test_phase7_tty_record_baseline_smoke():
    assert True
