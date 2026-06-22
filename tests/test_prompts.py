import pytest

from toas.backend_policy import BackendGenerationPolicy
from toas.capability_prompts import render_capability_overview, render_capability_repo_work
from toas.prompts import (
    _resolve_constraint_ref,
    _split_frontmatter,
    _validate_mode,
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


def test_pragmatic_default_template_includes_procedure_bootstrap_example():
    asset = load_prompt_asset("session-start/templates/pragmatic-default_v1")
    assert "operation: procedure" in asset.content
    assert "repo_discovery_triage_v1" in asset.content


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


def test_split_frontmatter_rejects_invalid_metadata_yaml():
    with pytest.raises(RuntimeError, match="invalid prompt metadata"):
        _split_frontmatter("---\n:bad\n---\nhello")


def test_split_frontmatter_rejects_non_mapping_metadata():
    with pytest.raises(RuntimeError, match="invalid prompt metadata"):
        _split_frontmatter("---\n- a\n- b\n---\nhello")


def test_validate_mode_and_constraint_ref_aliases():
    assert _validate_mode("DIRECT") == "direct"
    with pytest.raises(RuntimeError, match="invalid prompt mode"):
        _validate_mode("weird")
    assert _resolve_constraint_ref("tools-guidance-core") == "shared/constraints/tools-guidance-core"


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
    assert "prefer `$ rg ...`" in out
    assert "run `capability_help` first" in out


def test_capability_prompts_surface_read_file_line_window():
    out = render_capability_overview()
    assert "start_line" in out
    assert "end_line" in out
    repo_work = render_capability_repo_work()
    assert "start_line" in repo_work
    assert "end_line" in repo_work
    assert "number_lines" in repo_work


def test_capability_repo_work_core_profile_omits_echo_block_noise():
    out = render_capability_repo_work(profile="core")
    assert "echo_block" not in out


def test_capability_repo_work_core_profile_includes_capability_help():
    out = render_capability_repo_work(profile="core")
    assert "capability_help" in out


def test_capability_prompt_loader_strips_yaml_frontmatter(monkeypatch):
    import toas.capability_prompts as mod

    class _FakePath:
        def read_text(self, encoding: str) -> str:  # noqa: ARG002
            return "---\nname: test\n---\nbody line\n"

    class _FakeNode:
        def joinpath(self, *parts: str):  # noqa: ANN001
            if parts and parts[-1] == "overview_v1.txt":
                return _FakePath()
            return self

    class _FakeResources:
        @staticmethod
        def files(_pkg: str) -> _FakeNode:
            return _FakeNode()

    monkeypatch.setattr(mod, "resources", _FakeResources)
    assert mod._load_template("overview_v1") == "body line"


def test_capability_prompt_loader_keeps_body_when_frontmatter_is_unclosed(monkeypatch):
    import toas.capability_prompts as mod

    class _FakePath:
        def read_text(self, encoding: str) -> str:  # noqa: ARG002
            return "---\nname: test\nbody line\n"

    class _FakeNode:
        def joinpath(self, *parts: str):  # noqa: ANN001
            if parts and parts[-1] == "overview_v1.txt":
                return _FakePath()
            return self

    class _FakeResources:
        @staticmethod
        def files(_pkg: str) -> _FakeNode:
            return _FakeNode()

    monkeypatch.setattr(mod, "resources", _FakeResources)
    assert mod._load_template("overview_v1") == "---\nname: test\nbody line"


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
    assert "aliases accepted: `operation`/`tool_name`, `arguments`/`args`/`params`, `intent`/`intention`" in out
    assert "use an operation list only for tightly coupled work" in out
    assert "- operation: replace_block" in out
    assert "path: src/a.py" in out


def test_capability_repo_work_full_profile_includes_write_file_capability_line():
    out = render_capability_repo_work(profile="full")
    assert "`write_file` for explicit file creation or full overwrite" in out


def test_capability_start_here_template_without_frontmatter_still_loads(monkeypatch):
    import toas.capability_prompts as mod

    monkeypatch.setattr(mod, "_load_template", lambda _name: "plain template body")
    assert mod.render_capability_start_here() == "plain template body"


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


def test_prompt_composer_can_inject_tools_guidance_core_constraint():
    out = load_prompt_ref("role/pragmatic-engineer_v1", constraints=["tools-guidance-core"])
    assert "Act as a pragmatic senior engineer" in out
    assert "operation: capability_help" in out
    assert "topic: core" in out


def test_prompt_composer_can_inject_tools_guidance_repo_work_constraint():
    out = load_prompt_ref("role/pragmatic-engineer_v1", constraints=["tools-guidance-repo-work"])
    assert "begin with bounded discovery" in out
    assert "topic: repo-work" in out


def test_prompt_composer_can_inject_tools_guidance_first_edit_pass_constraint():
    out = load_prompt_ref("role/pragmatic-engineer_v1", constraints=["tools-guidance-first-edit-pass"])
    assert "First-edit-pass scaffold for repo work" in out
    assert "discover -> edit -> test" in out
    assert "topic: repo-work" in out


def test_prompt_composer_can_inject_tools_guidance_full_constraint():
    out = load_prompt_ref("role/pragmatic-engineer_v1", constraints=["tools-guidance-full"])
    assert "Shape contract" in out
    assert "optional `intent`/`intention`" in out
    assert "use a literal indent indicator (for example `|2`, `|4`)" in out
    assert "set `search_indent` explicitly" in out
    assert "topic: all" in out


def test_tools_guidance_full_asset_contains_edit_mode_indent_contract():
    asset = load_prompt_asset("shared/constraints/tools-guidance-full")
    assert "Edit-mode replacement rules" in asset.content
    assert "literal indent indicator (for example `|2`, `|4`)" in asset.content
    assert "`|N` means content indentation is interpreted relative to the block's baseline" in asset.content
    assert "set `search_indent` explicitly" in asset.content


def test_tools_guidance_first_edit_pass_asset_contains_discover_edit_test_scaffold():
    asset = load_prompt_asset("shared/constraints/tools-guidance-first-edit-pass")
    assert "First-edit-pass scaffold for repo work" in asset.content
    assert "one concrete edit target" in asset.content
    assert "smallest relevant test/validation command" in asset.content


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


def test_capability_overview_includes_capture_task_thread_policy_when_visible():
    out = render_capability_overview(profile="core")
    assert "Task Capture Policy" in out
    assert "Fork Rule" in out
    assert "Resume" in out
    assert "continue" in out


def test_capability_overview_omits_capture_task_thread_policy_when_hidden():
    out = render_capability_overview(profile="core", hidden_tools=("capture_task_thread",))
    assert "Task Capture Policy" not in out
    assert "Fork Rule" not in out


def test_capability_repo_work_includes_capture_task_thread_when_visible():
    out = render_capability_repo_work(profile="core")
    assert "capture_task_thread" in out
    assert "synchronously deferring side threads" in out


def test_capability_repo_work_omits_capture_task_thread_when_hidden():
    out = render_capability_repo_work(profile="core", hidden_tools=("capture_task_thread",))
    assert "capture_task_thread" not in out


def test_prompts_additional_coverage(monkeypatch):
    from toas.prompts import (
        _load_asset_or_none,
        _load_static_prompt_content,
        _resolve_compose_target,
        _load_required_layer,
        _render_template_asset,
        list_prompt_assets,
    )
    import toas.prompts as prompts

    # 1. parse_prompt_ref empty
    with pytest.raises(RuntimeError, match="invalid prompt ref:"):
        parse_prompt_ref("   ")

    # 2. _split_frontmatter YAMLError
    with pytest.raises(RuntimeError, match="invalid prompt metadata"):
        _split_frontmatter("---\nmetadata: [invalid\n---\nbody")

    # 3. _load_asset_or_none other RuntimeError
    monkeypatch.setattr(prompts, "load_prompt_asset", lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("other error")))
    with pytest.raises(RuntimeError, match="other error"):
        _load_asset_or_none("ref")
    monkeypatch.undo() # wait, we can just use monkeypatch manually to restore if we want, or not since monkeypatch handles it

    # 4. _load_static_prompt_content missing file
    with pytest.raises(RuntimeError, match="missing prompt:"):
        _load_static_prompt_content("nonexistent")

    # 5. _resolve_compose_target direct/mimic and protocol legacy prefix
    t1 = _resolve_compose_target("direct/role/pragmatic-engineer_v1")
    assert t1 is not None
    assert t1.category == "role"
    
    t2 = _resolve_compose_target("session-start/protocol-entrainment/action-lane_v1")
    assert t2 is not None
    assert t2.category == "protocol"
    assert "protocol/action-lane_v1" in t2.base_candidates

    t3 = _resolve_compose_target("direct/protocol/action-lane_v1")
    assert t3 is not None
    assert t3.category == "protocol"
    assert "protocol/action-lane_v1" in t3.base_candidates

    # 6. _resolve_constraint_ref starting with shared/constraints/
    assert _resolve_constraint_ref("shared/constraints/no-chatty") == "shared/constraints/no-chatty"

    # 7. _load_required_layer failure
    with pytest.raises(RuntimeError, match="missing required prompt layer"):
        _load_required_layer(("nonexistent1", "nonexistent2"))

    # 8. compose_template errors
    composer = PromptComposer()
    with pytest.raises(RuntimeError, match="refs must be a non-empty list"):
        composer.compose_template([])
    with pytest.raises(RuntimeError, match="refs must be non-empty strings"):
        composer.compose_template([123])
    with pytest.raises(RuntimeError, match="invalid template ref:"):
        composer.compose_template(["invalid_ref"])

    # 9. _render_template_asset errors and none constraints
    with pytest.raises(RuntimeError, match="refs must be a list"):
        _render_template_asset({"template": {"refs": 123}})
    with pytest.raises(RuntimeError, match="mode must be a string"):
        _render_template_asset({"template": {"refs": ["role/pragmatic-engineer_v1"], "mode": 123}})
    with pytest.raises(RuntimeError, match="constraints must be a list of strings"):
        _render_template_asset({"template": {"refs": ["role/pragmatic-engineer_v1"], "constraints": 123}})
    
    # None constraints should pass and not raise
    rendered = _render_template_asset({"template": {"refs": ["role/pragmatic-engineer_v1"], "constraints": None}})
    assert rendered is not None

    # 10. list_prompt_assets non-existent path
    assert list_prompt_assets("dynamic/capabilities/overview_v1")
    with pytest.raises(RuntimeError, match="missing prompt prefix: nonexistent"):
        list_prompt_assets("nonexistent")
