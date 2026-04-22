import pytest

from toas.backend_policy import BackendGenerationPolicy
from toas.capability_prompts import render_capability_overview, render_capability_repo_work
from toas.prompts import (
    PromptComposer,
    list_prompt_assets,
    load_prompt,
    load_prompt_asset,
    load_prompt_ref,
    parse_prompt_ref,
    prompt_messages,
)
from toas.tools import SHELL_ALLOWED


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


def test_list_prompt_assets_can_filter_session_start_templates():
    assets = list_prompt_assets("session-start/templates")

    assert [asset.ref for asset in assets] == [
        "session-start/templates/pragmatic-default_v1",
    ]
    assert assets[0].metadata["category"] == "templates"


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


def test_protocol_entrain_prompt_avoids_json_action_object_lane():
    content = load_prompt("protocol", "entrain_v1")
    assert "JSON action object" not in content
    assert 'argv: ["pwd"]' in content


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
    assert "shell_script" in out


def test_capability_repo_work_includes_shell_argv_shape_and_help_fallback():
    out = render_capability_repo_work()
    assert "arguments.argv" in out
    assert "not `command`" in out
    assert "run `capability_help` first" in out


def test_capability_repo_work_core_profile_omits_echo_block_noise():
    out = render_capability_repo_work(profile="core")
    assert "echo_block" not in out


def test_capability_repo_work_core_profile_includes_capability_help():
    out = render_capability_repo_work(profile="core")
    assert "capability_help" in out


def test_capability_overview_profile_hides_selected_tools():
    out = render_capability_overview(profile="full", hidden_tools=("echo_block",))
    assert "`echo_block`" not in out
    assert "`read_file`" in out


def test_capability_overview_full_profile_includes_echo_block_summary_and_shape_hint():
    out = render_capability_overview(profile="full")
    assert "`echo_block`: echo multiline block payload for YAML/debug diagnostics" in out
    assert "echo_block` example:" in out
    assert "block: |" in out
    assert "line two" in out


def test_capability_overview_full_profile_includes_code_survey_summary_and_shape_hint():
    out = render_capability_overview(profile="full")
    assert "`code_survey`: report largest Python files/functions/classes for decomposition planning" in out
    assert "code_survey` example:" in out
    assert "top_n: 15" in out


def test_load_prompt_ref_dynamic_capability_honors_profile_and_hidden_tools():
    out = load_prompt_ref(
        "dynamic/capabilities/repo-work_v1",
        capability_profile="debug",
        capability_hidden_tools=("echo_block",),
    )
    assert "capability_help" in out
    assert "echo_block" not in out


def test_capability_overview_includes_alias_and_multi_op_guidance():
    out = render_capability_overview()
    assert "aliases accepted: `operation`/`tool_name`, `arguments`/`args`" in out
    assert "use an operation list only for tightly coupled work" in out
    assert "- operation: replace_block" in out
    assert "path: src/a.py" in out


def test_capability_repo_work_full_profile_includes_write_file_capability_line():
    out = render_capability_repo_work(profile="full")
    assert "`write_file` for explicit file creation or full overwrite" in out


def test_prompt_composer_direct_role_uses_legacy_compat_layer():
    out = load_prompt_ref("role/pragmatic-engineer_v1", mode="direct")
    assert "Act as a pragmatic senior engineer" in out


def test_prompt_composer_mimic_role_layers_in_deterministic_order():
    out = load_prompt_ref("role/pragmatic-engineer_v1", mode="mimic")
    social = "You are collaborating with the user in a direct, practical loop."
    mimic = "Mirror the user's working style"
    base = "Act as a pragmatic senior engineer"
    assert social in out
    assert mimic in out
    assert base in out
    assert out.index(social) < out.index(mimic) < out.index(base)


def test_prompt_composer_protocol_includes_shared_schema_layer():
    out = load_prompt_ref("protocol/action-lane_v1", mode="direct")
    assert "Use a local action protocol" in out
    assert "operation: <operation_name>" in out


def test_prompt_composer_can_inject_constraints():
    out = load_prompt_ref("role/pragmatic-engineer_v1", constraints=["no-chatty"])
    assert "Act as a pragmatic senior engineer" in out
    assert "Avoid chatty preambles" in out


def test_prompt_composer_missing_constraint_fails_loudly():
    with pytest.raises(RuntimeError, match="missing prompt: shared/constraints/missing-constraint"):
        load_prompt_ref("role/pragmatic-engineer_v1", constraints=["missing-constraint"])


def test_prompt_composer_legacy_ref_supports_mode_switch():
    out = load_prompt_ref("session-start/role-framing/pragmatic-engineer_v1", mode="mimic")
    assert "You are collaborating with the user in a direct, practical loop." in out
    assert "Act as a pragmatic senior engineer" in out


def test_prompt_composer_rejects_invalid_mode():
    with pytest.raises(RuntimeError, match="invalid prompt mode: weird"):
        load_prompt_ref("role/pragmatic-engineer_v1", mode="weird")


def test_prompt_composer_explicit_type_available():
    composer = PromptComposer(mode="direct")
    out = composer.compose_ref("session/blank-page_v1", mode="mimic")
    assert "Start from uncertainty without stalling" in out


def test_load_prompt_asset_renders_template_asset_content_from_manifest():
    asset = load_prompt_asset("session-start/templates/pragmatic-default_v1")

    assert asset.metadata["category"] == "templates"
    assert "Act as a pragmatic senior engineer" in asset.content
    assert "Start from uncertainty without stalling" in asset.content
    assert "Use a local action protocol" in asset.content
    assert "Few-shot behavior examples for local repo work" in asset.content
    assert 'argv: ["find", "tasks/open", "-maxdepth", "1", "-type", "f"]' in asset.content
    assert "Do not ask for external repository access when local tools are available." in asset.content
    assert "Avoid chatty preambles" in asset.content
