from toas.runtime.rpc_payload_edges import drop_none_fields, with_workdir


def test_with_workdir_adds_default_and_preserves_existing(tmp_path):
    payload = with_workdir(None, workdir=tmp_path)
    assert payload["workdir"] == str(tmp_path.resolve())

    preserved = with_workdir({"workdir": "/custom", "x": 1}, workdir=tmp_path)
    assert preserved["workdir"] == "/custom"
    assert preserved["x"] == 1


def test_drop_none_fields_removes_only_none_values():
    assert drop_none_fields({"a": 1, "b": None, "c": False, "d": 0}) == {"a": 1, "c": False, "d": 0}
