import pytest

from toas.procedures import list_procedures, load_procedure


def _write_procedure(tmp_path, name: str, content: str):
    procedures_dir = tmp_path / "procedures"
    procedures_dir.mkdir(exist_ok=True)
    (procedures_dir / f"{name}.yaml").write_text(content, encoding="utf-8")


def _patch_procedure_root(monkeypatch, root):
    monkeypatch.setattr("toas.procedures.resources.files", lambda _package: root)


def test_list_procedures_includes_default_assets():
    names = list_procedures()
    assert "repo_discovery_triage_v1" in names
    assert "search_scope_v1" in names
    assert "task_pick_first_action_v1" in names


def test_list_procedures_filters_non_yaml_and_sorts(monkeypatch, tmp_path):
    procedures_dir = tmp_path / "procedures"
    procedures_dir.mkdir()
    (procedures_dir / "zeta.yaml").write_text("description: x\nsteps:\n- operation: echo\n", encoding="utf-8")
    (procedures_dir / "alpha.yaml").write_text("description: x\nsteps:\n- operation: echo\n", encoding="utf-8")
    (procedures_dir / "notes.txt").write_text("ignore", encoding="utf-8")
    _patch_procedure_root(monkeypatch, tmp_path)

    assert list_procedures() == ["alpha", "zeta"]


def test_load_procedure_returns_normalized_callable_plan():
    asset = load_procedure("repo_discovery_triage_v1")
    assert asset.name == "repo_discovery_triage_v1"
    assert asset.description
    assert asset.plan
    assert all("tool_name" in step for step in asset.plan)
    assert all("args" in step for step in asset.plan)


def test_load_procedure_rejects_missing_asset():
    with pytest.raises(RuntimeError, match="missing procedure"):
        load_procedure("missing_procedure")


def test_load_procedure_interpolates_defaults_and_parameters():
    asset = load_procedure("search_scope_v1", params={"query": "TODO", "path": "src"})
    assert asset.plan == [{"tool_name": "search", "args": {"query": "TODO", "path": "src", "limit": 10}}]


def test_load_procedure_uses_default_parameter_values():
    asset = load_procedure("search_scope_v1", params={"query": "FIXME"})
    assert asset.plan[0]["args"]["path"] == "."


def test_load_procedure_fails_when_required_parameter_missing():
    with pytest.raises(RuntimeError, match="missing required parameters: query"):
        load_procedure("search_scope_v1")


def test_load_procedure_rejects_invalid_names():
    with pytest.raises(RuntimeError, match="invalid procedure name"):
        load_procedure("   ")
    with pytest.raises(RuntimeError, match="invalid procedure name"):
        load_procedure("../escape")


def test_load_procedure_rejects_invalid_yaml_parse(monkeypatch, tmp_path):
    _write_procedure(tmp_path, "broken", "description: [\nsteps:\n  - operation: echo")
    _patch_procedure_root(monkeypatch, tmp_path)

    with pytest.raises(RuntimeError, match="invalid procedure asset: broken"):
        load_procedure("broken")


@pytest.mark.parametrize(
    ("content", "params"),
    [
        ("- just\n- a\n- list\n", None),
        ("description: ''\nsteps:\n  - operation: echo\n    params: {}\n", None),
        ("description: ok\nsteps: {}\n", None),
        ("description: ok\nsteps:\n  - nope\n", None),
        ("description: ok\nsteps:\n  - operation: ''\n", None),
        ("description: ok\nsteps:\n  - operation: procedure\n", None),
        ("description: ok\nsteps:\n  - operation: echo\n    params: []\n", None),
        (
            "description: ok\nsteps:\n  - operation: echo\n    params:\n      text: '{{ value }}'\n",
            {},
        ),
    ],
)
def test_load_procedure_rejects_invalid_assets(monkeypatch, tmp_path, content, params):
    _write_procedure(tmp_path, "invalid_case", content)
    _patch_procedure_root(monkeypatch, tmp_path)

    with pytest.raises(RuntimeError):
        if params is None:
            load_procedure("invalid_case")
        else:
            load_procedure("invalid_case", params=params)


def test_load_procedure_accepts_compact_placeholder_form(monkeypatch, tmp_path):
    _write_procedure(
        tmp_path,
        "compact",
        "description: ok\nsteps:\n  - operation: search\n    params:\n      query: '{{query}}'\n      path: '.'\n",
    )
    _patch_procedure_root(monkeypatch, tmp_path)

    asset = load_procedure("compact", params={"query": "needle"})
    assert asset.plan[0]["args"]["query"] == "needle"


def test_load_procedure_ignores_non_mapping_defaults(monkeypatch, tmp_path):
    _write_procedure(
        tmp_path,
        "defaults_ignored",
        "description: ok\ndefaults: []\nsteps:\n  - operation: echo\n    params:\n      text: hi\n",
    )
    _patch_procedure_root(monkeypatch, tmp_path)

    asset = load_procedure("defaults_ignored")
    assert asset.plan[0]["args"]["text"] == "hi"
