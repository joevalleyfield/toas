import pytest

from toas.backend_policy import BackendGenerationPolicy
from toas.capability_prompts import render_capability_overview, render_capability_repo_work
from toas.tools import SHELL_ALLOWED
from toas.prompts import list_prompt_assets, load_prompt, load_prompt_asset, load_prompt_ref, parse_prompt_ref, prompt_messages


def test_load_prompt_reads_named_asset():
    content = load_prompt("generation", "v1")

    assert "TOAS" in content
    assert "next assistant message content" in content


def test_load_prompt_ref_reads_path_like_identifier():
    content = load_prompt_ref("protocol/terse_v1")

    assert "TOAS" in content
    assert "action" in content


def test_load_prompt_asset_reads_minimal_command_lane_prompt():
    asset = load_prompt_asset("protocol/minimal-command-lane_v1")

    assert asset.metadata == {
        "name": "Minimal Command Lane (Live-Like)",
        "description": "Known-good command-suggestion lane with explicit user-run semantics.",
        "category": "protocol",
    }
    assert 'command: "somecommand argv1 argv2"' in asset.content


def test_load_prompt_asset_reads_minimal_command_lane_strict_prompt():
    asset = load_prompt_asset("protocol/minimal-command-lane-strict_v1")
    assert asset.metadata["category"] == "protocol"
    assert "exactly one YAML block" in asset.content


def test_load_prompt_asset_reads_minimal_command_lane_advisor_clear_prompt():
    asset = load_prompt_asset("protocol/minimal-command-lane-advisor-clear_v1")
    assert asset.metadata["category"] == "protocol"
    assert "you are the advisor" in asset.content


def test_load_prompt_asset_reads_metadata_backed_session_prompt():
    asset = load_prompt_asset("session-start/start-here/blank-page_v1")

    assert asset.ref == "session-start/start-here/blank-page_v1"
    assert asset.metadata == {
        "name": "Blank Page Starter",
        "description": "A simple opening prompt for when you do not know how to begin.",
        "category": "start-here",
    }
    assert "Help me get started" in asset.content


def test_load_prompt_asset_renders_dynamic_capability_prompt():
    asset = load_prompt_asset("dynamic/capabilities/overview_v1")

    assert asset.metadata == {
        "name": "Capability Overview",
        "description": "Advertise the current TOAS runtime capabilities and limits.",
        "category": "capability-advertisement",
    }
    assert "`read_file`" in asset.content
    assert "`search`" in asset.content
    assert "`shell`" in asset.content
    assert "workspace-bounded" in asset.content


def test_load_prompt_asset_dynamic_overview_accepts_injected_policy():
    asset = load_prompt_asset(
        "dynamic/capabilities/overview_v1",
        policy=BackendGenerationPolicy(
            name="test",
            extra_body=None,
            avoid_terms=("function-call",),
        ),
    )
    assert "safer than `function-call`." in asset.content


def test_list_prompt_assets_can_filter_by_prefix():
    assets = list_prompt_assets("session-start/role-framing")

    assert [asset.ref for asset in assets] == [
        "session-start/role-framing/editorial-partner_v1",
        "session-start/role-framing/pragmatic-engineer_v1",
        "session-start/role-framing/requirements-interrogator_v1",
    ]
    assert all(asset.metadata["category"] == "role-framing" for asset in assets)


def test_list_prompt_assets_can_browse_dynamic_capability_prompts():
    assets = list_prompt_assets("dynamic/capabilities")

    assert [asset.ref for asset in assets] == [
        "dynamic/capabilities/overview_v1",
        "dynamic/capabilities/repo-work_v1",
        "dynamic/capabilities/start-here_v1",
    ]
    assert all(asset.metadata["category"] == "capability-advertisement" for asset in assets)


def test_prompt_messages_support_protocol_assets():
    messages = prompt_messages("protocol", [{"role": "user", "content": "hello"}], version="terse_v1")

    assert messages[0]["role"] == "system"
    assert "TOAS" in messages[0]["content"]
    assert "action" in messages[0]["content"]
    assert messages[1:] == [{"role": "user", "content": "hello"}]


def test_parse_prompt_ref_rejects_invalid_refs():
    with pytest.raises(RuntimeError, match="invalid prompt ref: ../generation"):
        parse_prompt_ref("../generation")


def test_load_prompt_rejects_missing_asset():
    with pytest.raises(RuntimeError, match="missing prompt: generation/missing"):
        load_prompt("generation", "missing")


def test_capability_overview_lists_all_shell_allowed_commands():
    out = render_capability_overview()
    for cmd in SHELL_ALLOWED:
        assert cmd in out, f"expected shell command {cmd!r} in capability overview"


def test_capability_overview_shell_limits_includes_timeout():
    out = render_capability_overview()
    assert "timeout_s" in out
    assert "30" in out


def test_capability_overview_includes_replace_block():
    out = render_capability_overview()
    assert "replace_block" in out


def test_capability_repo_work_includes_replace_block():
    out = render_capability_repo_work()
    assert "replace_block" in out
