import importlib.util
import sys
from pathlib import Path

_PATH = Path(__file__).parents[1] / "scripts" / "cancel_race_sweep.py"
_SPEC = importlib.util.spec_from_file_location("cancel_race_sweep", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
_field = _MODULE._field
_float_range = _MODULE._float_range
_timings = _MODULE._timings


def test_float_range_is_bounded_and_inclusive():
    assert _float_range(0.0, 0.3, 0.1) == [0.0, 0.1, 0.2, 0.3]


def test_field_extracts_cancel_and_terminal_statuses():
    output = "ui t=1s cancel=2 status=cancelled\nterminal_status=cancelled\n"
    assert _field(output, "cancel=2", "status") == "cancelled"
    assert _field(output, "terminal_status=", "terminal_status") == "cancelled"
    assert _field(output, "cancel=1", "status") == "missing"


def test_timings_measure_second_cancel_rtt_and_flag_long_gap():
    output = "\n".join(
        (
            "ui t=1.000s run=r frame=push_event",
            "ui t=2.400s run=r cancel=2 phase=dispatch",
            "ui t=17.410s run=r cancel=2 status=cancelled",
            "ui t=17.411s run=r frame=push_complete",
        )
    )
    rtt_s, max_gap_s, stalled = _timings(output, stall_threshold_s=12.0)
    assert rtt_s == 15.01
    assert max_gap_s == 15.01
    assert stalled is True
