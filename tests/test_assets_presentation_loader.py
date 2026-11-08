"""Tests for presentation template loader and workspace overrides."""
from __future__ import annotations

from pathlib import Path

import pytest

from toas.assets.presentation_loader import (
    clear_presentation_template_cache,
    list_presentation_templates,
    load_presentation_template,
    render_template,
)


def test_load_packaged_presentation_template():
    clear_presentation_template_cache()
    content = load_presentation_template("models", "model_overview")
    assert "active model target:" in content
    assert "/model targets" in content

    env_content = load_presentation_template("shell", "env_help")
    assert "/env set <KEY> <VALUE>" in env_content

    ws_content = load_presentation_template("workspace", "workspace_overview")
    assert "/workspace mode strict" in ws_content

    replay_content = load_presentation_template("replay", "queue_blocked")
    assert "replay queue blocked" in replay_content


def test_workspace_roots_override(tmp_path: Path):
    clear_presentation_template_cache()
    root1 = tmp_path / "root1"
    root2 = tmp_path / "root2"

    override1 = root1 / ".toas" / "assets" / "presentation" / "models" / "model_overview.txt"
    override1.parent.mkdir(parents=True)
    override1.write_text("CUSTOM MODEL OVERVIEW ROOT 1\n")

    override2 = root2 / ".toas" / "assets" / "presentation" / "models" / "model_overview.txt"
    override2.parent.mkdir(parents=True)
    override2.write_text("CUSTOM MODEL OVERVIEW ROOT 2\n")

    # Root 1 takes precedence
    content = load_presentation_template(
        "models",
        "model_overview",
        workspace_roots=(str(root1), str(root2)),
    )
    assert content == "CUSTOM MODEL OVERVIEW ROOT 1"

    # Only Root 2 provided
    clear_presentation_template_cache()
    content2 = load_presentation_template(
        "models",
        "model_overview",
        workspace_roots=(str(root2),),
    )
    assert content2 == "CUSTOM MODEL OVERVIEW ROOT 2"


def test_command_cwd_override(tmp_path: Path):
    clear_presentation_template_cache()
    cwd_dir = tmp_path / "project"
    override = cwd_dir / ".toas" / "assets" / "presentation" / "shell" / "env_help.txt"
    override.parent.mkdir(parents=True)
    override.write_text("CUSTOM ENV HELP FROM CWD\n")

    content = load_presentation_template(
        "shell",
        "env_help",
        command_cwd=str(cwd_dir),
    )
    assert content == "CUSTOM ENV HELP FROM CWD"


def test_cwd_fallback_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    clear_presentation_template_cache()
    override = tmp_path / ".toas" / "assets" / "presentation" / "workspace" / "workspace_overview.txt"
    override.parent.mkdir(parents=True)
    override.write_text("CUSTOM WORKSPACE OVERVIEW CWD FALLBACK\n")

    monkeypatch.chdir(tmp_path)
    content = load_presentation_template("workspace", "workspace_overview")
    assert content == "CUSTOM WORKSPACE OVERVIEW CWD FALLBACK"


def test_missing_or_invalid_asset_raises():
    clear_presentation_template_cache()
    with pytest.raises(RuntimeError, match="missing presentation asset"):
        load_presentation_template("models", "non_existent_template")

    with pytest.raises(RuntimeError, match="invalid asset ref"):
        load_presentation_template("../models", "escape")


def test_list_presentation_templates(tmp_path: Path):
    clear_presentation_template_cache()
    all_templates = list_presentation_templates()
    assert "models/model_overview" in all_templates
    assert "shell/env_help" in all_templates
    assert "workspace/workspace_overview" in all_templates
    assert "replay/queue_blocked" in all_templates

    models_only = list_presentation_templates("models")
    assert all(ref.startswith("models/") for ref in models_only)
    assert "models/model_overview" in models_only
    assert "shell/env_help" not in models_only

    # Add custom template in workspace
    custom_dir = tmp_path / ".toas" / "assets" / "presentation" / "custom_fam"
    custom_dir.mkdir(parents=True)
    (custom_dir / "custom_view.txt").write_text("custom view")

    custom_listed = list_presentation_templates(workspace_roots=(str(tmp_path),))
    assert "custom_fam/custom_view" in custom_listed

    custom_fam_only = list_presentation_templates("custom_fam", workspace_roots=(str(tmp_path),))
    assert custom_fam_only == ["custom_fam/custom_view"]


def test_active_presentation_context(tmp_path: Path):
    clear_presentation_template_cache()
    from toas.assets.presentation_loader import (
        reset_active_presentation_context,
        set_active_presentation_context,
    )

    override = tmp_path / ".toas" / "assets" / "presentation" / "shell" / "env_help.txt"
    override.parent.mkdir(parents=True)
    override.write_text("CUSTOM SHELL HELP FROM ACTIVE CONTEXT\n")

    token = set_active_presentation_context(
        workspace_roots=(str(tmp_path),),
        command_cwd=str(tmp_path),
    )
    try:
        content = load_presentation_template("shell", "env_help")
        assert content == "CUSTOM SHELL HELP FROM ACTIVE CONTEXT"

        listed = list_presentation_templates("shell")
        assert "shell/env_help" in listed
    finally:
        reset_active_presentation_context(token)


def test_command_dispatch_respects_workspace_override(tmp_path: Path):
    clear_presentation_template_cache()
    from toas.config import OperatorConfig
    from toas.runtime.operator_commands import execute_operator_command

    override = tmp_path / ".toas" / "assets" / "presentation" / "shell" / "env_help.txt"
    override.parent.mkdir(parents=True)
    override.write_text("DISPATCH OVERRIDE SUCCESS\n")

    ctx_args = {
        "execute": lambda *a, **k: None,
        "events": [],
        "working": [],
        "transcript": "",
        "command_cwd": str(tmp_path),
        "previous_command_cwd": None,
        "workspace_mode": "off",
        "workspace_roots": [str(tmp_path)],
        "config": OperatorConfig(),
    }

    nodes = execute_operator_command("env", [], **ctx_args)
    assert nodes[0]["content"] == "DISPATCH OVERRIDE SUCCESS"


def test_render_template():
    clear_presentation_template_cache()
    # With kwargs
    out = render_template("models", "endpoint_intent", selected="ep-1", unavailable_block="")
    assert "selected endpoint intent: ep-1" in out

    # Without kwargs
    out_no_kwargs = render_template("shell", "env_help")
    assert "/env set <KEY> <VALUE>" in out_no_kwargs


def test_yaml_workspace_overrides(tmp_path: Path):
    clear_presentation_template_cache()
    # 1. Unified .toas/presentation.yaml
    toas_dir = tmp_path / ".toas"
    toas_dir.mkdir(parents=True)
    unified = toas_dir / "presentation.yaml"
    unified.write_text("shell:\n  env_help: UNIFIED SHELL HELP\n")

    val = load_presentation_template("shell", "env_help", workspace_roots=(str(tmp_path),))
    assert val == "UNIFIED SHELL HELP"

    # 2. Family file .toas/assets/presentation/shell.yaml
    fam_dir = toas_dir / "assets" / "presentation"
    fam_dir.mkdir(parents=True)
    fam_file = fam_dir / "shell.yaml"
    fam_file.write_text("env_help: FAMILY FILE SHELL HELP\n")

    clear_presentation_template_cache()
    val2 = load_presentation_template("shell", "env_help", workspace_roots=(str(tmp_path),))
    assert val2 == "FAMILY FILE SHELL HELP"

    # Malformed YAML handling
    fam_file.write_text("not: [valid: yaml\n")
    unified.write_text("not: [valid: yaml\n")
    clear_presentation_template_cache()
    # Should fall back to packaged catalog gracefully
    val_fallback = load_presentation_template("shell", "env_help", workspace_roots=(str(tmp_path),))
    assert "/env set" in val_fallback

