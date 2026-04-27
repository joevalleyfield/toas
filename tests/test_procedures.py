import pytest

from toas.procedures import list_procedures, load_procedure


def test_list_procedures_includes_default_assets():
    names = list_procedures()
    assert "repo_discovery_triage_v1" in names
    assert "task_pick_first_action_v1" in names


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
