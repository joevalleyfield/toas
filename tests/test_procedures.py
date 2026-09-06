from types import SimpleNamespace

import pytest

from toas.procedures import list_procedures, load_procedure


def _write_procedure(tmp_path, name: str, content: str):
    procedures_dir = tmp_path / "procedures"
    procedures_dir.mkdir(exist_ok=True)
    (procedures_dir / f"{name}.yaml").write_text(content, encoding="utf-8")


def _patch_procedure_root(monkeypatch, root):
    def load_packaged_asset(kind, ref, *, suffix):
        path = root / kind / f"{ref}{suffix}"
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise RuntimeError(f"missing {kind} asset: {ref}") from exc
        return SimpleNamespace(kind=kind, ref=ref, suffix=suffix, content=content)

    monkeypatch.setattr("toas.procedures.load_packaged_asset", load_packaged_asset)


def test_list_procedures_includes_default_assets():
    names = list_procedures()
    assert "repo_discovery_triage_v1" in names
    assert "search_scope_v1" in names
    assert "task_pick_first_action_v1" in names


def test_migrated_procedure_uses_common_asset_path_and_preserves_interpolation():
    asset = load_procedure("search_scope_v1", params={"query": "TODO", "path": "src"})
    assert asset.plan == [{"tool_name": "search", "args": {"query": "TODO", "path": "src", "limit": 10}}]
    assert list_procedures().count("search_scope_v1") == 1


def test_migrated_repo_discovery_procedure_preserves_plan_and_listing():
    asset = load_procedure("repo_discovery_triage_v1")
    assert asset.description == "Repo-local discovery and quick triage for a new working session."
    assert asset.plan == [
        {"tool_name": "shell", "args": {"argv": ["pwd"]}},
        {"tool_name": "shell", "args": {"argv": ["ls", "-la"]}},
        {"tool_name": "shell", "args": {"argv": ["ls", "-1", "tasks/open"]}},
        {
            "tool_name": "search",
            "args": {"query": "TODO|FIXME", "path": "src", "regex": True, "limit": 30},
        },
    ]
    assert list_procedures().count("repo_discovery_triage_v1") == 1


def test_list_procedures_filters_non_yaml_and_sorts(monkeypatch, tmp_path):
    procedures_dir = tmp_path / "procedures"
    procedures_dir.mkdir()
    (procedures_dir / "zeta.yaml").write_text("description: x\nsteps:\n- operation: echo\n", encoding="utf-8")
    (procedures_dir / "alpha.yaml").write_text("description: x\nsteps:\n- operation: echo\n", encoding="utf-8")
    (procedures_dir / "notes.txt").write_text("ignore", encoding="utf-8")
    monkeypatch.setattr(
        "toas.procedures.list_packaged_assets",
        lambda _kind, suffix: sorted(
            path.name.removesuffix(suffix)
            for path in procedures_dir.iterdir()
            if path.is_file() and path.name.endswith(suffix)
        ),
    )

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


def test_load_procedure_preserves_unrelated_loader_errors(monkeypatch):
    def fail(*_args, **_kwargs):
        raise RuntimeError("asset loader unavailable")

    monkeypatch.setattr("toas.procedures.load_packaged_asset", fail)

    with pytest.raises(RuntimeError, match="asset loader unavailable"):
        load_procedure("search_scope_v1")


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
