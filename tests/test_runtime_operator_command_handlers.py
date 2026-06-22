from __future__ import annotations

import shlex
from pathlib import Path

import pytest

from toas.config import BackendCatalogEntry, LLMPolicy, OperatorConfig, PromptPolicy
from toas.runtime.operator_command_config_help import (
    _config_secret_result,
    _resolve_config_path,
    _validate_known_config_key,
    handle_config_help_commands,
)
from toas.runtime.operator_command_context import OperatorCommandContext
from toas.runtime.operator_command_extract_replay import (
    _apply_queue_skip,
    _cancel_queue_remaining,
    _collect_replay_candidates,
    _iter_queue_payloads,
    _latest_assistant_target,
    _parse_extract_selection,
    _parse_heal_args,
    _parse_queue_args,
    _parse_replay_args,
    _queue_step_outcome,
    _render_queue_boundary_message,
    _render_replay_candidates,
    _validate_queue_plan_state,
    handle_extract_replay_commands,
)
from toas.runtime.operator_command_prompt_workspace import (
    _extract_lens_fenced_distillation,
    _frontier_user_content,
    _handle_shell_config,
    _lens_doctor_suggestions,
    _parse_compact_args,
    _parse_lens_packet_args,
    _parse_lens_set_args,
    _parse_lens_source_ids,
    _parse_scope,
    _render_lens_packet_summary,
    _resolve_cd_target,
    _resolve_workspace_arg,
    _validate_env_key,
    _validate_lens_source_ids,
    handle_prompt_workspace_commands,
)
from toas.runtime.operator_config_backend_ops import (
    _backend_add_result,
    _backend_capture_result,
    _backend_list_result,
    _backend_remove_result,
    _backend_set_result,
    _normalize_backend_set_value,
    backend_list_dicts,
    config_backend_result,
)
from toas.runtime.replay_queue_edges import (
    entry_for_call,
    is_shell_authorization_block,
    latest_queue_state,
    latest_queue_states_by_id,
    next_queue_id,
    queue_summary,
)


def _ctx(**overrides):
    base = OperatorCommandContext(
        execute=lambda _working, _plan: [],
        events=[],
        working=[],
        frontier_role="user",
        transcript="",
        command_cwd=".",
        previous_command_cwd=None,
        workspace_mode="strict",
        workspace_roots=[str(Path(".").resolve())],
        config=OperatorConfig(),
        config_sources=None,
        already_executed_indices=None,
    )
    data = base.__dict__.copy()
    data.update(overrides)
    return OperatorCommandContext(**data)


def _assert_slash_result(node: dict, content: str, **extra) -> None:
    assert node["role"] == "result"
    assert node["content"] == content
    assert node["origin_role"] == "user"
    assert node["origin_kind"] == "slash_command"
    assert node["projection_lane"] == "user"
    for key, value in extra.items():
        assert node[key] == value


def test_prompt_workspace_handler_prompts(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_render_prompt_browse_commands", lambda prefix: f"rendered:{prefix}")
    out = handle_prompt_workspace_commands("prompts", ["x"], step_mod=step_mod, context=_ctx())
    _assert_slash_result(out[0], "rendered:x", transcript_inert=False)


def test_prompt_workspace_handler_graph(tmp_path):
    events_dir = tmp_path / ".toas"
    events_dir.mkdir()
    (events_dir / "events.jsonl").write_text(
        '{"id":"n1","parent":null,"role":"user","content":"hello"}\n',
        encoding="utf-8",
    )

    out = handle_prompt_workspace_commands(
        "graph",
        ["--projection", "consequence"],
        step_mod=object(),
        context=_ctx(command_cwd=str(tmp_path)),
    )

    _assert_slash_result(out[0], "○ n1 u hello")


def test_prompt_workspace_prompts_and_prompt_usage_errors(monkeypatch):
    import toas.step as step_mod

    with pytest.raises(ValueError, match="usage: /prompts"):
        handle_prompt_workspace_commands("prompts", ["a", "b"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /prompt"):
        handle_prompt_workspace_commands("prompt", ["x", "--mode"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /prompt"):
        handle_prompt_workspace_commands("prompt", ["x", "--constraint"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /prompt"):
        handle_prompt_workspace_commands("prompt", ["x", "--wat"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /graph"):
        handle_prompt_workspace_commands("graph", ["--projection"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /graph"):
        handle_prompt_workspace_commands("graph", ["--projection", "wat"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /graph"):
        handle_prompt_workspace_commands("graph", ["--unknown-flag"], step_mod=step_mod, context=_ctx())


def test_prompt_workspace_prompt_honors_config_defaults_and_inline_overrides(monkeypatch):
    import toas.step as step_mod

    seen = {}

    def _fake_load_prompt_ref(ref, **kwargs):
        seen["ref"] = ref
        seen.update(kwargs)
        return "rendered-prompt"

    monkeypatch.setattr(step_mod, "load_prompt_ref", _fake_load_prompt_ref)
    monkeypatch.setattr(step_mod, "_render_prompt_browse_commands", lambda prefix: f"browse:{prefix}")
    monkeypatch.setattr(step_mod, "generation_policy_from_config", lambda _cfg: object())
    cfg = OperatorConfig(prompt=PromptPolicy(mode="mimic", constraints=("tools-guidance-core",)))
    out = handle_prompt_workspace_commands("prompt", ["role/pragmatic-engineer_v1"], step_mod=step_mod, context=_ctx(config=cfg))
    _assert_slash_result(
        out[0],
        "rendered-prompt\n\n## TOAS:USER\n\n",
        transcript_render="raw",
        transcript_inert=False,
    )
    assert seen["mode"] == "mimic"
    assert seen["constraints"] == ["tools-guidance-core"]

    seen.clear()
    out = handle_prompt_workspace_commands(
        "prompt",
        ["role/pragmatic-engineer_v1", "--mode", "direct", "--constraint", "no-chatty"],
        step_mod=step_mod,
        context=_ctx(config=cfg),
    )
    _assert_slash_result(
        out[0],
        "rendered-prompt\n\n## TOAS:USER\n\n",
        transcript_render="raw",
        transcript_inert=False,
    )
    assert seen["mode"] == "direct"
    assert seen["constraints"] == ["tools-guidance-core", "no-chatty"]


def test_prompt_workspace_prompt_prefix_fallback_and_unknown(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "load_prompt_ref", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("missing")))
    monkeypatch.setattr(step_mod, "_render_prompt_browse_commands", lambda prefix: f"browse:{prefix}")
    out = handle_prompt_workspace_commands("prompt", ["session-start"], step_mod=step_mod, context=_ctx())
    assert out[0]["content"] == "browse:session-start"

    monkeypatch.setattr(step_mod, "_render_prompt_browse_commands", lambda _prefix: "")
    with pytest.raises(ValueError, match="unknown prompt ref or prefix"):
        handle_prompt_workspace_commands("prompt", ["missing"], step_mod=step_mod, context=_ctx())


def test_prompt_workspace_backend_and_model_usage_and_unavailable_paths(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_available_backends", lambda _cfg: ["b1"])
    with pytest.raises(ValueError, match="usage: /backend"):
        handle_prompt_workspace_commands("backend", ["a", "b"], step_mod=step_mod, context=_ctx())
    out = handle_prompt_workspace_commands("backend", ["missing"], step_mod=step_mod, context=_ctx())
    assert "chosen backend unavailable" in out[0]["content"]

    monkeypatch.setattr(step_mod, "resolve_selected_backend", lambda _w: "b1")
    monkeypatch.setattr(step_mod, "_available_models", lambda _cfg, selected_backend=None: ["m1"])
    with pytest.raises(ValueError, match="usage: /model"):
        handle_prompt_workspace_commands("model", ["a", "b"], step_mod=step_mod, context=_ctx())
    out = handle_prompt_workspace_commands("model", ["missing"], step_mod=step_mod, context=_ctx())
    assert "chosen model unavailable" in out[0]["content"]


def test_prompt_workspace_backend_and_model_empty_catalog_paths(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_available_backends", lambda _cfg: [])
    out = handle_prompt_workspace_commands("backend", [], step_mod=step_mod, context=_ctx())
    assert "no backends available" in out[0]["content"]

    monkeypatch.setattr(step_mod, "resolve_selected_backend", lambda _w: None)
    monkeypatch.setattr(step_mod, "_available_models", lambda _cfg, selected_backend=None: [])
    out = handle_prompt_workspace_commands("model", [], step_mod=step_mod, context=_ctx())
    assert "no models available" in out[0]["content"]


def test_extract_replay_handler_replay_dry_run(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _content, yaml_position="any": ([{"tool_name": "echo_block", "args": {"content": "x"}}], False))

    working = [
        {"role": "user", "content": "hello"},
        {"role": "user", "content": "/replay --index 1 --dry-run"},
    ]
    out = handle_extract_replay_commands("replay", ["--index", "1", "--dry-run"], step_mod=step_mod, context=_ctx(working=working))
    assert out is not None
    assert "replay dry-run" in out[0]["content"]


def test_heal_reexecutes_latest_replace_block_with_search_indent(monkeypatch):
    import toas.step as step_mod

    original = {
        "tool_name": "replace_block",
        "args": {
            "path": "src/toas/step.py",
            "search_block": "for name in names:\n    use(name)\n",
            "replacement_block": "for name in names:\n    use_better(name)\n",
        },
    }
    seen = []
    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _content, yaml_position="any": ([original], False))
    monkeypatch.setattr(step_mod, "resolve_effective_env_modifiers", lambda _working: {})
    monkeypatch.setattr(
        step_mod,
        "_execute_plan_user_context",
        lambda plan, **_kwargs: seen.extend(plan) or [{"role": "result", "content": "healed"}],
    )
    context = _ctx(
        working=[
            {"role": "assistant", "content": "original callable block"},
            {"role": "user", "content": "/heal search_indent=4"},
        ]
    )

    out = handle_extract_replay_commands("heal", ["search_indent=4"], step_mod=step_mod, context=context)

    assert out == [{"role": "result", "content": "healed"}]
    assert seen == [{**original, "args": {**original["args"], "search_indent": 4}}]
    assert original["args"].get("search_indent") is None


def test_heal_reexecutes_selected_replace_blocks_from_multi_call_plan(monkeypatch):
    import toas.step as step_mod

    plan = [
        {"tool_name": "read_file", "args": {"path": "x"}},
        {"tool_name": "replace_block", "args": {"path": "a", "search_block": "a", "replacement_block": "A"}},
        {"tool_name": "search", "args": {"path": ".", "query": "x"}},
        {"tool_name": "replace_block", "args": {"path": "b", "search_block": "b", "replacement_block": "B"}},
    ]
    seen = []
    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _content, yaml_position="any": (plan, False))
    monkeypatch.setattr(step_mod, "resolve_effective_env_modifiers", lambda _working: {})
    monkeypatch.setattr(step_mod, "_execute_plan_user_context", lambda healed, **_kwargs: seen.extend(healed) or [])
    context = _ctx(working=[{"role": "assistant", "content": "plan"}, {"role": "user", "content": "/heal"}])

    handle_extract_replay_commands(
        "heal",
        ["2:search_indent=4", "4:search_indent=8"],
        step_mod=step_mod,
        context=context,
    )

    assert [(call["args"]["path"], call["args"]["search_indent"]) for call in seen] == [("a", 4), ("b", 8)]


@pytest.mark.parametrize("args", [[], ["search_indent=nope"], ["search_indent=-1"]])
def test_heal_rejects_invalid_indent(args):
    with pytest.raises(ValueError, match="usage: /heal"):
        handle_extract_replay_commands("heal", args, step_mod=object(), context=_ctx())


@pytest.mark.parametrize(
    "args",
    [
        ["x:search_indent=4"],
        ["0:search_indent=4"],
        ["2:other=4"],
        ["search_indent=4", "2:search_indent=4"],
        ["2:search_indent=4", "2:search_indent=8"],
    ],
)
def test_parse_heal_args_rejects_invalid_indexed_shapes(args):
    with pytest.raises(ValueError, match="usage: /heal"):
        _parse_heal_args(args)


@pytest.mark.parametrize(
    ("plan", "message"),
    [
        (None, "no prior callable frontier"),
        ([{"tool_name": "echo", "args": {}}], "operation 1 is not replace_block"),
        ([{"tool_name": "replace_block", "args": None}], "invalid arguments"),
    ],
)
def test_heal_rejects_missing_or_incompatible_frontier(monkeypatch, plan, message):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _content, yaml_position="any": (plan, False))
    context = _ctx(working=[{"role": "assistant", "content": "prior"}, {"role": "user", "content": "/heal search_indent=4"}])

    with pytest.raises(ValueError, match=message):
        handle_extract_replay_commands("heal", ["search_indent=4"], step_mod=step_mod, context=context)


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["search_indent=4"], "multiple operations"),
        (["3:search_indent=4"], "outside the latest callable frontier"),
    ],
)
def test_heal_rejects_ambiguous_or_stale_plan_position(monkeypatch, args, message):
    import toas.step as step_mod

    plan = [
        {"tool_name": "replace_block", "args": {}},
        {"tool_name": "replace_block", "args": {}},
    ]
    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _content, yaml_position="any": (plan, False))
    context = _ctx(working=[{"role": "assistant", "content": "prior"}, {"role": "user", "content": "/heal"}])

    with pytest.raises(ValueError, match=message):
        handle_extract_replay_commands("heal", args, step_mod=step_mod, context=context)


def test_config_help_handler_help(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "render_session_help", lambda: "help text")
    monkeypatch.setattr(step_mod, "render_help_commands_inert", lambda: "commands help text")
    monkeypatch.setattr(step_mod, "render_help_tools", lambda: "tools help text")
    monkeypatch.setattr(step_mod, "render_help_cli", lambda: "cli help text")
    monkeypatch.setattr(step_mod, "render_help_config", lambda: "config help text")
    out = handle_config_help_commands("help", [], step_mod=step_mod, context=_ctx())
    _assert_slash_result(out[0], "help text")
    out_commands = handle_config_help_commands("help", ["commands"], step_mod=step_mod, context=_ctx())
    _assert_slash_result(out_commands[0], "commands help text")
    out_tools = handle_config_help_commands("help", ["tools"], step_mod=step_mod, context=_ctx())
    _assert_slash_result(out_tools[0], "tools help text")
    out_cli = handle_config_help_commands("help", ["cli"], step_mod=step_mod, context=_ctx())
    _assert_slash_result(out_cli[0], "cli help text")
    out_config = handle_config_help_commands("help", ["config"], step_mod=step_mod, context=_ctx())
    _assert_slash_result(out_config[0], "config help text")
    with pytest.raises(ValueError, match="usage: /help"):
        handle_config_help_commands("help", ["bad"], step_mod=step_mod, context=_ctx())


def test_config_help_handler_config_paths(tmp_path):
    import toas.step as step_mod

    cfg = tmp_path / ".toas" / "config.toml"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text("[llm]\nmodel='x'\n", encoding="utf-8")
    out = handle_config_help_commands("config", ["paths"], step_mod=step_mod, context=_ctx(command_cwd=str(tmp_path)))
    assert out is not None
    assert "discovered config paths" in out[0]["content"]
    assert str(cfg) in out[0]["content"]


def test_config_help_handler_config_show_sources(monkeypatch):
    import toas.step as step_mod
    from toas.config import OperatorConfig, apply_overrides
    from toas.runtime.policy_edges import build_config_sources as _build_config_sources

    # Test the source builder first
    file_nested = {"llm": {"model": "file-model"}}
    session_overrides = {"llm": {"base_url": "override-url"}}
    cfg = OperatorConfig()
    cfg = apply_overrides(cfg, file_nested)
    cfg = apply_overrides(cfg, session_overrides)
    
    file_key_sources = {"llm.model": "file.toml"}
    sources = _build_config_sources(
        file_nested=file_nested,
        session_overrides=session_overrides,
        operator_config=cfg,
        file_key_sources=file_key_sources
    )
    assert sources["llm.base_url"] == "session_override"
    assert sources["llm.model"] == "file.toml"
    assert sources["generation.thinking_mode"] == "default"

    # Now verify the command view includes sources and precedence legend
    context = _ctx(config=cfg, config_sources=sources)
    out = handle_config_help_commands("config", ["show", "--sources"], step_mod=step_mod, context=context)
    assert out is not None
    content = out[0]["content"]
    assert "llm.base_url = override-url    [source=session_override]" in content
    assert "llm.model = file-model    [source=file.toml]" in content
    assert "precedence stack (highest to lowest):" in content
    assert "1. ephemeral_secrets" in content
    assert "timing semantics:" in content


def test_handlers_return_none_for_non_matching_command():
    import toas.step as step_mod

    context = _ctx()
    assert handle_prompt_workspace_commands("nope", [], step_mod=step_mod, context=context) is None
    assert handle_extract_replay_commands("nope", [], step_mod=step_mod, context=context) is None
    assert handle_config_help_commands("nope", [], step_mod=step_mod, context=context) is None


def test_prompt_workspace_cd_strict_workspace_guard(tmp_path):
    import toas.step as step_mod

    outside = tmp_path / "outside"
    outside.mkdir()
    context = _ctx(command_cwd=str(tmp_path), workspace_roots=[str(tmp_path / "inside")], workspace_mode="strict")
    with pytest.raises(ValueError, match="cwd outside allowed workspace roots"):
        handle_prompt_workspace_commands("cd", [str(outside)], step_mod=step_mod, context=context)


def test_prompt_workspace_env_set_unset_and_usage(monkeypatch):
    import toas.step as step_mod

    out = handle_prompt_workspace_commands("env", ["set", "ABC", "123"], step_mod=step_mod, context=_ctx())
    _assert_slash_result(out[0], "env set: ABC")
    out = handle_prompt_workspace_commands("env", ["unset", "ABC"], step_mod=step_mod, context=_ctx())
    _assert_slash_result(out[0], "env unset: ABC")
    out = handle_prompt_workspace_commands("env", [], step_mod=step_mod, context=_ctx())
    assert "/env set <KEY> <VALUE>" in out[0]["content"]
    with pytest.raises(ValueError, match="usage: /env"):
        handle_prompt_workspace_commands("env", ["bad"], step_mod=step_mod, context=_ctx())


def test_prompt_workspace_shell_config_add_remove_reset_and_errors(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "normalize_shell_grants", lambda grants: tuple(grants))
    monkeypatch.setattr(step_mod, "parse_shell_grant", lambda s: type("P", (), {"raw": s})())
    cfg = OperatorConfig()
    out = handle_prompt_workspace_commands("shell", ["config", "add", "jj"], step_mod=step_mod, context=_ctx(config=cfg))
    assert out[0]["config_update"]["shell"]["allowed_commands"]
    out = handle_prompt_workspace_commands("shell", ["config", "remove", "jj"], step_mod=step_mod, context=_ctx(config=cfg))
    assert "config baseline" in out[0]["content"]
    out = handle_prompt_workspace_commands("shell", ["config", "reset"], step_mod=step_mod, context=_ctx(config=cfg))
    assert "reset to defaults" in out[0]["content"]
    with pytest.raises(ValueError, match="usage:"):
        handle_prompt_workspace_commands("shell", ["config", "add"], step_mod=step_mod, context=_ctx(config=cfg))
    with pytest.raises(ValueError, match="bad grant"):
        monkeypatch.setattr(step_mod, "parse_shell_grant", lambda _s: (_ for _ in ()).throw(ValueError("bad grant")))
        handle_prompt_workspace_commands("shell", ["config", "add", "bad"], step_mod=step_mod, context=_ctx(config=cfg))
    with pytest.raises(ValueError, match="usage:"):
        handle_prompt_workspace_commands("shell", ["config", "wat", "x"], step_mod=step_mod, context=_ctx(config=cfg))


def test_prompt_workspace_shell_list_and_reset(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_resolve_shell_grants_with_sources", lambda _w, _c, _e=None: (("echo",), ("echo",), {"config": "default"}, (), ()))
    monkeypatch.setattr(step_mod, "render_shell_policy_view", lambda *args: "policy-view")
    monkeypatch.setattr(step_mod, "resolve_effective_shell_allowed", lambda _w, _c, _e=None: ("echo",))
    monkeypatch.setattr(step_mod, "parse_shell_grant", lambda s: type("P", (), {"raw": s})())
    out = handle_prompt_workspace_commands("shell", ["list"], step_mod=step_mod, context=_ctx())
    _assert_slash_result(out[0], "policy-view")
    out = handle_prompt_workspace_commands("shell", ["reset"], step_mod=step_mod, context=_ctx())
    assert "shell grants reset (scope=session)" in out[0]["content"]


def test_parse_scope_supports_explicit_scope_and_rejects_bad_shapes():
    assert _parse_scope(["add", "echo"]) == "session"
    assert _parse_scope(["add", "echo", "--scope", "workspace"]) == "workspace"
    with pytest.raises(ValueError, match="usage: /shell"):
        _parse_scope(["add", "echo", "--wat", "workspace"])
    with pytest.raises(ValueError, match="invalid scope"):
        _parse_scope(["add", "echo", "--scope", "banana"])


def test_shell_reset_rejects_invalid_scope_shape(monkeypatch):
    import toas.step as step_mod

    with pytest.raises(ValueError, match="usage: /shell reset"):
        handle_prompt_workspace_commands("shell", ["reset", "--wat", "session"], step_mod=step_mod, context=_ctx())
    monkeypatch.setattr(step_mod, "parse_shell_grant", lambda _s: (_ for _ in ()).throw(ValueError("bad grant")))
    with pytest.raises(ValueError, match="bad grant"):
        handle_prompt_workspace_commands("shell", ["allow", "??"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage:"):
        handle_prompt_workspace_commands("shell", ["wat"], step_mod=step_mod, context=_ctx())


def test_shell_reset_accepts_explicit_scope():
    import toas.step as step_mod

    out = handle_prompt_workspace_commands("shell", ["reset", "--scope", "head"], step_mod=step_mod, context=_ctx())
    assert "shell grants reset (scope=head)" in out[0]["content"]
    assert out[0]["shell_scope_update"] == {"scope": "head", "action": "reset"}


def test_prompt_workspace_pwd_and_cd_usage_and_previous_dir_errors(tmp_path):
    import toas.step as step_mod

    with pytest.raises(ValueError, match="usage: /pwd"):
        handle_prompt_workspace_commands("pwd", ["extra"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /cd <path>\\|\\-"):
        handle_prompt_workspace_commands("cd", [], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="no previous command cwd"):
        handle_prompt_workspace_commands("cd", ["-"], step_mod=step_mod, context=_ctx(previous_command_cwd=None))
    missing = tmp_path / "missing"
    with pytest.raises(ValueError, match="not a directory"):
        handle_prompt_workspace_commands("cd", [str(missing)], step_mod=step_mod, context=_ctx(command_cwd=str(tmp_path)))


def test_prompt_workspace_workspace_modes_and_compact(monkeypatch, tmp_path):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_render_workspace_commands", lambda mode, roots: f"{mode}:{len(roots)}")
    monkeypatch.setattr(step_mod, "_compact_result_blocks", lambda transcript, threshold: ("x", [{"index": 1, "chars": 900}]))
    cwd = tmp_path
    add_dir = tmp_path / "add"
    add_dir.mkdir()
    out = handle_prompt_workspace_commands("workspace", [], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    _assert_slash_result(out[0], "strict:1")
    out = handle_prompt_workspace_commands("workspace", ["add", str(add_dir)], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    assert "workspace_update" in out[0]
    out = handle_prompt_workspace_commands("workspace", ["mode", "unbounded"], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    assert out[0]["workspace_update"]["mode"] == "unbounded"
    out = handle_prompt_workspace_commands("compact", ["--dry-run", "--threshold", "10"], step_mod=step_mod, context=_ctx(transcript="t"))
    assert "compact dry-run" in out[0]["content"]


def test_prompt_workspace_compact_noop_and_apply_branches(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_compact_result_blocks", lambda transcript, threshold: (transcript, []))
    out = handle_prompt_workspace_commands("compact", ["--dry-run"], step_mod=step_mod, context=_ctx(transcript="t"))
    assert "no RESULT blocks" in out[0]["content"]
    out = handle_prompt_workspace_commands("compact", [], step_mod=step_mod, context=_ctx(transcript="t"))
    assert "no RESULT blocks" in out[0]["content"]


def test_prompt_workspace_workspace_error_paths(tmp_path):
    import toas.step as step_mod

    cwd = tmp_path
    with pytest.raises(ValueError, match="usage: /workspace add <path>"):
        handle_prompt_workspace_commands("workspace", ["add"], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    with pytest.raises(ValueError, match="not a directory"):
        handle_prompt_workspace_commands("workspace", ["add", "missing"], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    with pytest.raises(ValueError, match="usage: /workspace remove <path>"):
        handle_prompt_workspace_commands("workspace", ["remove"], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    with pytest.raises(ValueError, match="usage: /workspace reset"):
        handle_prompt_workspace_commands("workspace", ["reset", "extra"], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    with pytest.raises(ValueError, match="usage: /workspace mode strict\\|unbounded"):
        handle_prompt_workspace_commands("workspace", ["mode", "weird"], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    with pytest.raises(ValueError, match="usage: /workspace \\[add\\|remove\\|reset\\|mode\\]"):
        handle_prompt_workspace_commands("workspace", ["wat"], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))


def test_prompt_workspace_workspace_remove_empty_and_reset_paths(tmp_path):
    import toas.step as step_mod

    cwd = tmp_path
    other = tmp_path / "other"
    other.mkdir()
    out = handle_prompt_workspace_commands(
        "workspace",
        ["remove", str(other)],
        step_mod=step_mod,
        context=_ctx(command_cwd=str(cwd), workspace_roots=[str(other.resolve())]),
    )
    assert out[0]["workspace_update"]["roots"]
    out = handle_prompt_workspace_commands("workspace", ["reset"], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    assert out[0]["workspace_update"]["mode"] == "strict"


def test_prompt_workspace_session_show_slot_name_path():
    import toas.step as step_mod

    out = handle_prompt_workspace_commands("session", ["show"], step_mod=step_mod, context=_ctx())
    assert "session transcript path: .toas/session.md" in out[0]["content"]
    out = handle_prompt_workspace_commands("session", ["slot", "2"], step_mod=step_mod, context=_ctx())
    assert out[0]["config_update"]["session"]["transcript_path"] == ".toas/session2.md"
    out = handle_prompt_workspace_commands("session", ["name", "triage-1"], step_mod=step_mod, context=_ctx())
    assert out[0]["config_update"]["session"]["transcript_path"] == ".toas/session-triage-1.md"
    out = handle_prompt_workspace_commands("session", ["path", ".toas/custom.md"], step_mod=step_mod, context=_ctx())
    assert out[0]["config_update"]["session"]["transcript_path"] == ".toas/custom.md"
    with pytest.raises(ValueError, match="usage: /session"):
        handle_prompt_workspace_commands("session", ["slot"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="integer >= 1"):
        handle_prompt_workspace_commands("session", ["slot", "0"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="name must match"):
        handle_prompt_workspace_commands("session", ["name", "bad/name"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="path must be non-empty"):
        handle_prompt_workspace_commands("session", ["path", "   "], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /session"):
        handle_prompt_workspace_commands("session", ["wat"], step_mod=step_mod, context=_ctx())


def test_prompt_workspace_session_additional_error_paths():
    import toas.step as step_mod

    with pytest.raises(ValueError, match="usage: /session"):
        handle_prompt_workspace_commands("session", ["show", "extra"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="slot must be integer >= 1"):
        handle_prompt_workspace_commands("session", ["slot", "nope"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /session"):
        handle_prompt_workspace_commands("session", ["name"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /session"):
        handle_prompt_workspace_commands("session", ["path"], step_mod=step_mod, context=_ctx())


def test_prompt_workspace_intent_set_list_current_status_note():
    import toas.step as step_mod

    out = handle_prompt_workspace_commands(
        "intent",
        ["set", "stabilize-462", "--scope", "task", "--tag", "intent", "--source", "task:462"],
        step_mod=step_mod,
        context=_ctx(),
    )
    assert out is not None
    update = out[0]["intent_update"]
    assert update["intent_id"] == "i1"
    assert update["status"] == "active"
    assert update["scope"] == "task"
    assert update["tags"] == ["intent"]
    assert update["source"] == "task:462"

    events = [{"kind": "intent", "payload": update}]
    listed = handle_prompt_workspace_commands("intent", ["list"], step_mod=step_mod, context=_ctx(events=events))
    assert "- i1 [active] stabilize-462" in listed[0]["content"]
    current = handle_prompt_workspace_commands("intent", ["current"], step_mod=step_mod, context=_ctx(events=events))
    assert "current intent: i1 [active] stabilize-462" in current[0]["content"]
    status = handle_prompt_workspace_commands("intent", ["status", "i1", "paused"], step_mod=step_mod, context=_ctx(events=events))
    assert status[0]["intent_update"]["status"] == "paused"
    note = handle_prompt_workspace_commands("intent", ["note", "i1", "next-pass"], step_mod=step_mod, context=_ctx(events=events))
    assert note[0]["intent_update"]["notes"] == "next-pass"
    none_list = handle_prompt_workspace_commands("intent", ["list"], step_mod=step_mod, context=_ctx(events=[]))
    assert "(none)" in none_list[0]["content"]
    none_current = handle_prompt_workspace_commands("intent", ["current"], step_mod=step_mod, context=_ctx(events=[]))
    assert "(none)" in none_current[0]["content"]


def test_prompt_workspace_intent_current_includes_notes_when_present():
    import toas.step as step_mod

    out = handle_prompt_workspace_commands(
        "intent",
        ["set", "stabilize-462", "--notes", "track followup"],
        step_mod=step_mod,
        context=_ctx(),
    )
    events = [{"kind": "intent", "payload": out[0]["intent_update"]}]
    current = handle_prompt_workspace_commands("intent", ["current"], step_mod=step_mod, context=_ctx(events=events))
    assert "notes: track followup" in current[0]["content"]


def test_prompt_workspace_intent_errors():
    import toas.step as step_mod

    with pytest.raises(ValueError, match="usage: /intent"):
        handle_prompt_workspace_commands("intent", ["set"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /intent"):
        handle_prompt_workspace_commands("intent", ["set", "x", "--status", "bad"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="no active intent"):
        handle_prompt_workspace_commands("intent", ["status", "current", "paused"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="unknown intent id: i99"):
        handle_prompt_workspace_commands(
            "intent",
            ["status", "i99", "paused"],
            step_mod=step_mod,
            context=_ctx(events=[{"kind": "intent", "payload": {"intent_id": "i1", "title": "x", "status": "active"}}]),
        )
    with pytest.raises(ValueError, match="usage: /intent"):
        handle_prompt_workspace_commands("intent", ["current", "extra"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /intent"):
        handle_prompt_workspace_commands("intent", ["set", "   "], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /intent"):
        handle_prompt_workspace_commands("intent", ["set", "x", "--wat"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /intent"):
        handle_prompt_workspace_commands("intent", ["wat"], step_mod=step_mod, context=_ctx())


def test_prompt_workspace_intent_status_and_note_additional_errors():
    import toas.step as step_mod

    intents = [{"kind": "intent", "payload": {"intent_id": "i1", "title": "x", "status": "active"}}]
    with pytest.raises(ValueError, match="usage: /intent"):
        handle_prompt_workspace_commands("intent", ["status", "i1"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /intent"):
        handle_prompt_workspace_commands("intent", ["note", "i1"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="unknown intent id"):
        handle_prompt_workspace_commands("intent", ["note", "i1", "   "], step_mod=step_mod, context=_ctx(events=[]))
    with pytest.raises(ValueError, match="usage: /intent"):
        handle_prompt_workspace_commands("intent", ["status", "current", "bad"], step_mod=step_mod, context=_ctx(events=intents))
    with pytest.raises(ValueError, match="usage: /intent"):
        handle_prompt_workspace_commands("intent", ["note", "i1", ""], step_mod=step_mod, context=_ctx(events=intents))


def test_prompt_workspace_intent_set_next_id_skips_invalid_existing_ids():
    import toas.step as step_mod

    events = [
        {"kind": "intent", "payload": {"intent_id": "i3", "title": "x", "status": "active"}},
        {"kind": "intent", "payload": {"intent_id": "ix", "title": "bad", "status": "active"}},
    ]
    out = handle_prompt_workspace_commands("intent", ["set", "next"], step_mod=step_mod, context=_ctx(events=events))
    assert out[0]["intent_update"]["intent_id"] == "i4"


def test_prompt_workspace_lens_list_set_remove_reset():
    import toas.step as step_mod

    context = _ctx(
        events=[
            {
                "kind": "lens_artifact",
                "payload": {
                    "action": "set",
                    "title": "repo-state",
                    "distillation": "tests green",
                    "source_pointers": ["n1", "n2"],
                    "use_when": "planning",
                },
            }
        ]
    )
    out = handle_prompt_workspace_commands("lens", ["list"], step_mod=step_mod, context=context)
    assert "lens artifacts:" in out[0]["content"]
    assert "repo-state" in out[0]["content"]

    out = handle_prompt_workspace_commands(
        "lens",
        ["set", "goal", "ship-next-slice", "n3,n4", "handoff"],
        step_mod=step_mod,
        context=_ctx(events=[{"id": "n3", "role": "user", "content": "a", "metadata": {}}, {"id": "n4", "role": "assistant", "content": "b", "metadata": {}}]),
    )
    assert out[0]["lens_update"]["action"] == "set"
    assert out[0]["lens_update"]["source_pointers"] == ["n3", "n4"]

    out = handle_prompt_workspace_commands("lens", ["remove", "goal"], step_mod=step_mod, context=_ctx())
    assert out[0]["lens_update"] == {"action": "remove", "title": "goal"}

    out = handle_prompt_workspace_commands("lens", ["reset"], step_mod=step_mod, context=_ctx())
    assert out[0]["lens_update"] == {"action": "reset"}

    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["set", "only-title"], step_mod=step_mod, context=_ctx())


def test_prompt_workspace_lens_set_supports_flag_form_and_multiline_fence():
    import toas.step as step_mod

    out = handle_prompt_workspace_commands(
        "lens",
        ["set", "--title", "goal", "--source", "n3,n4", "--distillation", "ship-next"],
        step_mod=step_mod,
        context=_ctx(events=[{"id": "n3", "role": "user", "content": "a", "metadata": {}}, {"id": "n4", "role": "assistant", "content": "b", "metadata": {}}]),
    )
    assert out[0]["lens_update"]["title"] == "goal"
    assert out[0]["lens_update"]["distillation"] == "ship-next"
    assert out[0]["lens_update"]["source_pointers"] == ["n3", "n4"]

    frontier = {
        "role": "user",
        "content": "```lens\nline one\nline two\n```\n/lens set --title summary --source n9 --use-when planning",
    }
    out = handle_prompt_workspace_commands(
        "lens",
        ["set", "--title", "summary", "--source", "n9", "--use-when", "planning"],
        step_mod=step_mod,
        context=_ctx(
            events=[{"id": "n9", "role": "assistant", "content": "c", "metadata": {}}],
            working=[frontier],
        ),
    )
    assert out[0]["lens_update"]["title"] == "summary"
    assert out[0]["lens_update"]["distillation"] == "line one\nline two"
    assert out[0]["lens_update"]["source_pointers"] == ["n9"]
    assert out[0]["lens_update"]["use_when"] == "planning"
    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["set", "--title", "x", "--bad"], step_mod=step_mod, context=_ctx())


def test_prompt_workspace_lens_set_validates_source_ids_and_duplicate_title_note():
    import toas.step as step_mod

    context = _ctx(
        events=[
            {"id": "n1", "role": "user", "content": "u", "metadata": {}},
            {
                "kind": "lens_artifact",
                "payload": {
                    "action": "set",
                    "title": "goal",
                    "distillation": "old",
                    "source_pointers": ["n1"],
                    "use_when": "planning",
                },
            },
        ]
    )
    out = handle_prompt_workspace_commands(
        "lens",
        ["set", "--title", "goal", "--source", "n1", "--distillation", "new"],
        step_mod=step_mod,
        context=context,
    )
    assert "replacing existing title" in out[0]["content"]

    with pytest.raises(ValueError, match="unknown source pointer ids: n404"):
        handle_prompt_workspace_commands(
            "lens",
            ["set", "--title", "goal2", "--source", "n404", "--distillation", "x"],
            step_mod=step_mod,
            context=context,
        )


def test_prompt_workspace_lens_set_flag_value_usage_errors():
    import toas.step as step_mod

    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["set", "--title"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["set", "--distillation"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["set", "--source"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["set", "--use-when"], step_mod=step_mod, context=_ctx())


def test_prompt_workspace_lens_set_requires_title_distillation_and_sources():
    import toas.step as step_mod

    # empty source list
    with pytest.raises(ValueError, match="source_ids_csv must include at least one message id"):
        handle_prompt_workspace_commands(
            "lens",
            ["set", "--title", "goal", "--distillation", "d", "--source", " , "],
            step_mod=step_mod,
            context=_ctx(events=[{"id": "n1", "role": "user", "content": "u", "metadata": {}}]),
        )
    # title/distillation required in positional path
    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["set", "goal", "", "n1"], step_mod=step_mod, context=_ctx())


def test_prompt_workspace_lens_doctor_usage_and_unknown_subcommand():
    import toas.step as step_mod

    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["doctor", "extra"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["wat"], step_mod=step_mod, context=_ctx())


def test_prompt_workspace_lens_remove_and_reset_usage_errors():
    import toas.step as step_mod

    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["remove"], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["remove", "   "], step_mod=step_mod, context=_ctx())
    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["reset", "extra"], step_mod=step_mod, context=_ctx())


def test_prompt_workspace_lens_list_empty_and_distillation_fallback_to_blank():
    import toas.step as step_mod

    out = handle_prompt_workspace_commands("lens", ["list"], step_mod=step_mod, context=_ctx(events=[]))
    assert "lens artifacts: (none)" in out[0]["content"]
    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands(
            "lens",
            ["set", "--title", "goal", "--source", "n1"],
            step_mod=step_mod,
            context=_ctx(events=[{"id": "n1", "role": "user", "content": "u", "metadata": {}}], working=[{"role": "assistant", "content": "no fence"}]),
        )


def test_parse_compact_args_invalid_threshold_value():
    with pytest.raises(ValueError, match="usage: /compact"):
        _parse_compact_args(["--threshold", "abc"])
    with pytest.raises(ValueError, match="usage: /compact"):
        _parse_compact_args(["--wat"])


def test_prompt_workspace_lens_packet_shows_summary_and_quality():
    import toas.step as step_mod

    context = _ctx(
        events=[
            {"id": "n1", "role": "user", "content": "goal line", "metadata": {}},
            {
                "kind": "lens_artifact",
                "payload": {
                    "action": "set",
                    "title": "repo-state",
                    "distillation": "tests green",
                    "source_pointers": ["n1"],
                    "use_when": "planning",
                },
            },
        ],
        working=[{"id": "n1", "role": "user", "content": "goal line"}],
    )
    out = handle_prompt_workspace_commands("lens", ["packet"], step_mod=step_mod, context=context)
    content = out[0]["content"]
    assert content.startswith("lens packet summary:")
    assert "- goal_cue: goal line" in content
    assert "- artifact_count: 1" in content
    assert "repo-state" in content
    assert "- quality: pass" in content

    bad_context = _ctx(
        events=[
            {
                "kind": "lens_artifact",
                "payload": {
                    "action": "set",
                    "title": "repo-state",
                    "distillation": "tests green",
                    "source_pointers": ["n-missing"],
                    "use_when": "planning",
                },
            }
        ],
        working=[{"role": "user", "content": "goal line"}],
    )
    out = handle_prompt_workspace_commands("lens", ["packet"], step_mod=step_mod, context=bad_context)
    assert "- quality: fail (staleness)" in out[0]["content"]
    assert "n-missing" in out[0]["content"]


def test_prompt_workspace_lens_packet_folded_and_expand_modes():
    import toas.step as step_mod

    context = _ctx(
        events=[
            {"id": "n1", "role": "user", "content": "goal line", "metadata": {}},
            {
                "kind": "lens_artifact",
                "payload": {
                    "action": "set",
                    "title": "repo-state",
                    "distillation": "tests green",
                    "source_pointers": ["n1", "n2", "n3"],
                    "use_when": "planning",
                },
            },
        ],
        working=[{"id": "n1", "role": "user", "content": "goal line"}],
    )
    folded = handle_prompt_workspace_commands("lens", ["packet", "--folded"], step_mod=step_mod, context=context)
    folded_content = folded[0]["content"]
    assert folded_content.startswith("lens folded outline:")
    assert "[hidden_refs=2]" in folded_content

    expanded = handle_prompt_workspace_commands(
        "lens",
        ["packet", "--expand", "n2,n3"],
        step_mod=step_mod,
        context=context,
    )
    expanded_content = expanded[0]["content"]
    assert "- expanded_refs: n2,n3" in expanded_content
    assert "[expand=explicit_ref]" in expanded_content

    auto = handle_prompt_workspace_commands(
        "lens",
        ["packet", "--mode", "auto_frontier"],
        step_mod=step_mod,
        context=context,
    )
    auto_content = auto[0]["content"]
    assert auto_content.startswith("lens folded outline:")
    assert "expansion_reasons: frontier_ref:1" in auto_content


def test_prompt_workspace_lens_packet_folded_usage_errors():
    import toas.step as step_mod

    context = _ctx(
        events=[{"id": "n1", "role": "user", "content": "goal line", "metadata": {}}],
        working=[{"id": "n1", "role": "user", "content": "goal line"}],
    )
    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["packet", "--expand"], step_mod=step_mod, context=context)

    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["packet", "--nope"], step_mod=step_mod, context=context)

    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["packet", "--mode", "bad"], step_mod=step_mod, context=context)


def test_prompt_workspace_lens_packet_more_usage_errors():
    import toas.step as step_mod

    context = _ctx()
    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["packet", "--mode"], step_mod=step_mod, context=context)
    with pytest.raises(ValueError, match="usage: /lens"):
        handle_prompt_workspace_commands("lens", ["packet", "--expand"], step_mod=step_mod, context=context)


def test_parse_lens_packet_args_modes_and_auto_fold():
    usage = "usage: /lens ..."
    folded, expanded_refs, mode = _parse_lens_packet_args(["--mode", "auto_frontier"], usage=usage)
    assert (folded, expanded_refs, mode) == (True, set(), "auto_frontier")

    folded, expanded_refs, mode = _parse_lens_packet_args(["--expand", "n1,n2"], usage=usage)
    assert folded is True
    assert expanded_refs == {"n1", "n2"}
    assert mode == "manual"

    with pytest.raises(ValueError, match="usage: /lens"):
        _parse_lens_packet_args(["--mode"], usage=usage)


def test_lens_packet_summary_and_doctor_suggestion_helpers():
    packet = type(
        "Packet",
        (),
        {
            "goal_cue": "g",
            "messages": [{"role": "user", "content": "x"}],
            "artifacts": (),
        },
    )()
    summary = _render_lens_packet_summary(packet, None)
    assert summary.startswith("lens packet summary:")
    assert "- quality: pass" in summary
    assert _lens_doctor_suggestions("unknown") == ["/lens packet", "/lens list"]


def test_lens_set_helper_frontier_and_source_validation():
    assert _frontier_user_content([]) == ""
    assert _frontier_user_content([{"role": "assistant", "content": "x"}]) == ""
    assert _frontier_user_content([{"role": "user", "content": "x"}]) == "x"
    with pytest.raises(ValueError, match="unknown source pointer ids: n9"):
        _validate_lens_source_ids(["n1", "n9"], known_message_ids={"n1", "n2"})


def test_lens_set_parser_helpers():
    usage = "usage: /lens ..."
    assert _extract_lens_fenced_distillation("x\n```text\nline one\nline two\n```\ny") == "line one\nline two"
    assert _extract_lens_fenced_distillation("no fence") is None
    assert _parse_lens_source_ids("n1, n2,,n3") == ["n1", "n2", "n3"]

    title, distillation, source_ids, use_when = _parse_lens_set_args(
        ["goal", "ship", "n1,n2", "handoff"],
        frontier_content="",
        usage=usage,
    )
    assert (title, distillation, source_ids, use_when) == ("goal", "ship", ["n1", "n2"], "handoff")

    title, distillation, source_ids, use_when = _parse_lens_set_args(
        ["--title", "summary", "--source", "n9", "--use-when", "planning"],
        frontier_content="```lens\nfrom fence\n```",
        usage=usage,
    )
    assert (title, distillation, source_ids, use_when) == ("summary", "from fence", ["n9"], "planning")

    with pytest.raises(ValueError, match="usage: /lens"):
        _parse_lens_set_args(["--title"], frontier_content="", usage=usage)


def test_prompt_workspace_lens_doctor_reports_recovery_commands():
    import toas.step as step_mod

    good = _ctx(events=[{"id": "n1", "role": "user", "content": "x", "metadata": {}}], working=[{"role": "user", "content": "goal"}])
    out = handle_prompt_workspace_commands("lens", ["doctor"], step_mod=step_mod, context=good)
    _assert_slash_result(out[0], "lens doctor: no quality-gate issues detected")

    bad = _ctx(
        events=[
            {
                "kind": "lens_artifact",
                "payload": {
                    "action": "set",
                    "title": "repo-state",
                    "distillation": "tests green",
                    "source_pointers": ["n-stale"],
                    "use_when": "planning",
                },
            }
        ],
        working=[{"role": "user", "content": "goal"}],
    )
    out = handle_prompt_workspace_commands("lens", ["doctor"], step_mod=step_mod, context=bad)
    content = out[0]["content"]
    assert "lens doctor: quality failure (staleness)" in content
    assert "n-stale" in content
    assert "/lens remove <title>" in content


def test_prompt_workspace_helper_compact_parse_and_cd_target(tmp_path):
    dry_run, threshold = _parse_compact_args(["--dry-run", "--threshold", "12"])
    assert (dry_run, threshold) == (True, 12)
    with pytest.raises(ValueError, match="usage: /compact"):
        _parse_compact_args(["--threshold"])
    with pytest.raises(ValueError, match="threshold must be >= 0"):
        _parse_compact_args(["--threshold", "-1"])

    prev = tmp_path / "prev"
    prev.mkdir()
    context = _ctx(command_cwd=str(tmp_path), previous_command_cwd=str(prev))
    assert _resolve_cd_target("-", context=context) == prev.resolve()
    rel = _resolve_cd_target("x", context=context)
    assert rel == (tmp_path / "x").resolve()


def test_extract_handler_errors_and_adopt(monkeypatch):
    import toas.step as step_mod

    with pytest.raises(ValueError, match="no prior assistant message"):
        handle_extract_replay_commands("extract", [], step_mod=step_mod, context=_ctx(working=[{"role": "user", "content": "x"}]))

    monkeypatch.setattr(step_mod, "_extract_frontier_assistant_candidates", lambda _c, **_kwargs: ([], ["1. bad"]))
    with pytest.raises(ValueError, match="skipped callable-looking blocks"):
        handle_extract_replay_commands(
            "extract",
            [],
            step_mod=step_mod,
            context=_ctx(working=[{"role": "assistant", "content": "a"}, {"role": "user", "content": "/extract"}]),
        )

    monkeypatch.setattr(
        step_mod,
        "_extract_frontier_assistant_candidates",
        lambda _c, **_kwargs: ([{"kind": "tool_plan", "preview": "p", "adopt": "a"}], []),
    )
    out = handle_extract_replay_commands(
        "extract",
        ["1"],
        step_mod=step_mod,
        context=_ctx(working=[{"role": "assistant", "content": "a"}, {"role": "user", "content": "/extract 1"}]),
    )
    assert out[0]["role"] == "user"
    with pytest.raises(ValueError, match="index out of range"):
        handle_extract_replay_commands(
            "extract",
            ["9"],
            step_mod=step_mod,
            context=_ctx(working=[{"role": "assistant", "content": "a"}, {"role": "user", "content": "/extract 9"}]),
        )


def test_replay_errors_and_force_path(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _c, yaml_position="any": (None, False))
    monkeypatch.setattr(step_mod, "_extract_loose_command", lambda _c: ("echo hi", False))
    monkeypatch.setattr(step_mod, "shlex", shlex)
    monkeypatch.setattr(step_mod, "_as_nodes", lambda nodes: nodes)

    working = [{"role": "assistant", "content": "$ echo hi"}, {"role": "user", "content": "/replay"}]
    out = handle_extract_replay_commands(
        "replay",
        ["--index", "1", "--force"],
        step_mod=step_mod,
        context=_ctx(working=working, already_executed_indices={1}, execute=lambda _w, _p: [{"role": "result", "content": "ok"}]),
    )
    assert out[0]["replay_execution"]["target_message_index"] == 1

    with pytest.raises(ValueError, match="usage: /replay"):
        handle_extract_replay_commands("replay", ["--index"], step_mod=step_mod, context=_ctx(working=working))
    with pytest.raises(ValueError, match="index out of range"):
        handle_extract_replay_commands("replay", ["--index", "9"], step_mod=step_mod, context=_ctx(working=working))


def test_extract_replay_helper_parsers():
    assert _parse_extract_selection([]) == (None, False, None)
    assert _parse_extract_selection(["2"]) == (2, False, None)
    assert _parse_extract_selection(["d2"]) == (2, False, None)
    assert _parse_extract_selection(["#d2"]) == (2, False, None)
    assert _parse_extract_selection(["--verbose"]) == (None, True, None)
    assert _parse_extract_selection(["--verbose", "2"]) == (2, True, None)
    assert _parse_extract_selection(["--shape", "yaml"]) == (None, False, "yaml")
    assert _parse_extract_selection(["--shape", "shell", "2"]) == (2, False, "shell")
    with pytest.raises(ValueError, match="usage: /extract"):
        _parse_extract_selection(["a"])
    with pytest.raises(ValueError, match="usage: /extract"):
        _parse_extract_selection(["1", "2"])
    with pytest.raises(ValueError, match="usage: /extract"):
        _parse_extract_selection(["--shape"])
    with pytest.raises(ValueError, match="usage: /extract"):
        _parse_extract_selection(["--shape", "bad"])

    assert _parse_replay_args(["--dry-run", "--index", "3", "--force"]) == (True, True, 3, None)
    assert _parse_replay_args(["--index", "r3"]) == (False, False, 3, None)
    assert _parse_replay_args(["--index", "#r3"]) == (False, False, 3, None)
    with pytest.raises(ValueError, match="usage: /replay"):
        _parse_replay_args(["--index"])
    with pytest.raises(ValueError, match="usage: /replay"):
        _parse_replay_args(["--index", "r"])
    assert _parse_replay_args(["--resume", "q2"]) == (False, False, None, ("resume", "q2"))
    with pytest.raises(ValueError, match="usage: /replay"):
        _parse_replay_args(["--index", "1", "--resume", "q2"])


def test_queue_parser_defaults_and_variants():
    context = _ctx(events=[{"kind": "execution_queue", "payload": {"id": "q7", "status": "blocked"}}])
    assert _parse_queue_args([], context=context) == ("approve", "q7")
    assert _parse_queue_args(["resume"], context=context) == ("resume", "q7")
    assert _parse_queue_args(["q7"], context=context) == ("approve", "q7")
    assert _parse_queue_args(["q7", "skip"], context=context) == ("skip", "q7")
    assert _parse_queue_args(["cancel", "q7"], context=context) == ("cancel", "q7")


def test_queue_parser_errors_for_ambiguous_or_invalid_inputs():
    context = _ctx(events=[{"kind": "execution_queue", "payload": {"id": "q7", "status": "blocked"}}])
    with pytest.raises(ValueError, match="no active replay queue"):
        _parse_queue_args([], context=_ctx(events=[]))
    with pytest.raises(ValueError, match="multiple active replay queues"):
        _parse_queue_args(
            [],
            context=_ctx(
                events=[
                    {"kind": "execution_queue", "payload": {"id": "q1", "status": "blocked"}},
                    {"kind": "execution_queue", "payload": {"id": "q2", "status": "running"}},
                ]
            ),
        )
    with pytest.raises(ValueError, match="usage: /queue"):
        _parse_queue_args(["bogus"], context=_ctx(events=[]))


def test_queue_payload_iterator_filters_non_queue_records():
    context = _ctx(
        events=[
            {"kind": "message", "payload": {"id": "n1"}},
            {"kind": "execution_queue", "payload": {"id": "q1", "status": "blocked"}},
            {"kind": "execution_queue", "payload": "bad"},
            {"kind": "execution_queue", "payload": {"id": "q2", "status": "running"}},
        ]
    )
    payloads = list(_iter_queue_payloads(context=context))
    assert payloads == [{"id": "q1", "status": "blocked"}, {"id": "q2", "status": "running"}]


def test_config_show_sources_and_secret_usage(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "flatten_config", lambda _c: {"llm.model": "x"})
    out = handle_config_help_commands("config", ["show", "--sources"], step_mod=step_mod, context=_ctx(config_sources={"llm.model": "env"}))
    assert "[source=env]" in out[0]["content"]
    with pytest.raises(ValueError, match="usage: /config secret"):
        handle_config_help_commands("config", ["secret", "set", "llm_api_key"], step_mod=step_mod, context=_ctx())


def test_config_set_unset_restore_load_save_backend(monkeypatch, tmp_path):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "valid_config_keys", lambda: ["llm.model", "generation.thinking_mode", "generation.transport_mode"])
    monkeypatch.setattr(step_mod, "apply_dotted_override", lambda _c, _k, _v: OperatorConfig())
    monkeypatch.setattr(step_mod, "config_value_choices", lambda _k: ("enabled", "disabled"))
    monkeypatch.setattr(step_mod, "flatten_config", lambda _c: {"llm.model": "m", "generation.thinking_mode": "disabled"})
    monkeypatch.setattr(step_mod, "load_file_config", lambda _p: {"llm": {"model": "m"}})
    monkeypatch.setattr(step_mod.Settings, "from_env", classmethod(lambda cls: type("S", (), {"llm_base_url": "u", "llm_model": "m"})()))
    cfg = OperatorConfig()

    out = handle_config_help_commands("config", ["set", "llm.model", "q"], step_mod=step_mod, context=_ctx(config=cfg))
    assert out[0]["config_update"] == {"llm": {"model": "m"}}
    out = handle_config_help_commands("config", ["values", "generation.thinking_mode"], step_mod=step_mod, context=_ctx(config=cfg))
    assert "allowed values" in out[0]["content"]
    out = handle_config_help_commands("config", ["unset", "llm.model"], step_mod=step_mod, context=_ctx(config=cfg))
    assert out[0]["config_update"]["__op__"] == "unset"
    out = handle_config_help_commands("config", ["restore"], step_mod=step_mod, context=_ctx(config=cfg))
    assert out[0]["config_update"]["__op__"] == "restore"

    cfg_path = tmp_path / "toas.toml"
    cfg_path.write_text("x=1", encoding="utf-8")
    out = handle_config_help_commands("config", ["load", str(cfg_path)], step_mod=step_mod, context=_ctx(config=cfg, command_cwd=str(tmp_path)))
    assert out[0]["config_update"]
    out = handle_config_help_commands("config", ["save", "out.toml"], step_mod=step_mod, context=_ctx(config=cfg))
    assert out[0]["config_save"]["path"] == "out.toml"

    out = handle_config_help_commands("config", ["backend", "add", "b1", "http://x"], step_mod=step_mod, context=_ctx(config=cfg))
    assert out[0]["config_update"]["llm"]["backends"][0]["id"] == "b1"
    cfg_with_backend = OperatorConfig(llm=LLMPolicy(backends=(BackendCatalogEntry(id="b1", base_url="http://x"),)))
    out = handle_config_help_commands("config", ["backend", "set", "b1.model", "m2"], step_mod=step_mod, context=_ctx(config=cfg_with_backend))
    assert "updated backend" in out[0]["content"]
    out = handle_config_help_commands("config", ["backend", "capture", "b2"], step_mod=step_mod, context=_ctx(config=cfg_with_backend))
    assert "captured backend b2" in out[0]["content"]


def test_config_values_non_categorical_branch(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "valid_config_keys", lambda: ["generation.max_retries"])
    monkeypatch.setattr(step_mod, "config_value_choices", lambda _k: None)
    monkeypatch.setattr(step_mod, "flatten_config", lambda _c: {"generation.max_retries": 2})
    out = handle_config_help_commands("config", ["values", "generation.max_retries"], step_mod=step_mod, context=_ctx())
    assert "no categorical value set" in out[0]["content"]


def test_config_helper_secret_and_path_and_usage(monkeypatch, tmp_path):
    import toas.step as step_mod

    out = _config_secret_result(["secret", "show"])
    assert "secret keys" in out[0]["content"]
    with pytest.raises(ValueError, match="usage: /config secret"):
        _config_secret_result(["secret", "set", "llm_api_key"])

    ctx = _ctx(command_cwd=str(tmp_path))
    resolved = _resolve_config_path("toas.toml", context=ctx)
    assert resolved == (tmp_path / "toas.toml").resolve()

    with pytest.raises(ValueError, match="usage: /config"):
        handle_config_help_commands("config", ["wat"], step_mod=step_mod, context=ctx)


def test_config_backend_validation_error_branches():
    import toas.step as step_mod

    cfg_with_backend = OperatorConfig(llm=LLMPolicy(backends=(BackendCatalogEntry(id="b1", base_url="http://x"),)))
    with pytest.raises(ValueError, match="backend field must be one of"):
        handle_config_help_commands("config", ["backend", "set", "b1.nope", "x"], step_mod=step_mod, context=_ctx(config=cfg_with_backend))
    with pytest.raises(ValueError, match="unknown backend id: missing"):
        handle_config_help_commands("config", ["backend", "set", "missing.model", "x"], step_mod=step_mod, context=_ctx(config=cfg_with_backend))
    with pytest.raises(ValueError, match="backend api_key_source must be env\\|keyring"):
        handle_config_help_commands("config", ["backend", "set", "b1.api_key_source", "bad"], step_mod=step_mod, context=_ctx(config=cfg_with_backend))


def test_operator_config_backend_ops_helper_branches(monkeypatch):
    import toas.step as step_mod

    empty_ctx = _ctx(config=OperatorConfig())
    assert backend_list_dicts(context=empty_ctx) == []
    assert _backend_list_result(["backend", "list"], context=empty_ctx)[0]["content"] == "no configured backends"
    with pytest.raises(ValueError, match="usage: /config backend list"):
        _backend_list_result(["backend", "list", "extra"], context=empty_ctx)

    cfg = OperatorConfig(llm=LLMPolicy(backends=(BackendCatalogEntry(id="b1", base_url="http://x"),)))
    ctx = _ctx(config=cfg)
    with pytest.raises(ValueError, match="backend id/base_url must be non-empty"):
        _backend_add_result(["backend", "add", "  ", "http://x"], context=ctx)
    with pytest.raises(ValueError, match="usage: /config backend add"):
        _backend_add_result(["backend", "add", "b2"], context=ctx)
    with pytest.raises(ValueError, match="usage: /config backend remove"):
        _backend_remove_result(["backend", "remove"], context=ctx)
    with pytest.raises(ValueError, match="usage: /config backend set"):
        _backend_set_result(["backend", "set", "b1model", "x"], context=ctx)
    with pytest.raises(ValueError, match="usage: /config backend capture"):
        _backend_capture_result(["backend", "capture"], step_mod=step_mod, context=ctx)

    assert _normalize_backend_set_value("models", "a, b , ,c") == ["a", "b", "c"]
    assert _normalize_backend_set_value("api_key_source", "ENV") == "env"
    assert _normalize_backend_set_value("notes", "x") == "x"

    monkeypatch.setattr(step_mod, "Settings", type("S", (), {"from_env": staticmethod(lambda: type("SS", (), {"llm_base_url": "u", "llm_model": "m"})())}))
    out = _backend_capture_result(["backend", "capture", "capt"], step_mod=step_mod, context=ctx)
    assert "captured backend capt" in out[0]["content"]
    listed = _backend_list_result(["backend", "list"], context=ctx)
    assert "configured backends:" in listed[0]["content"]
    assert "- b1: http://x (model=-)" in listed[0]["content"]

    with pytest.raises(ValueError, match="usage: /config backend set"):
        _backend_set_result(["backend", "set", "only3"], context=ctx)

    with pytest.raises(ValueError, match="usage: /config backend"):
        config_backend_result(["backend", "nope"], step_mod=step_mod, context=ctx)


def test_config_key_validator_branch():
    class _M:
        @staticmethod
        def valid_config_keys():
            return ["a.b"]

    _validate_known_config_key("a.b", step_mod=_M)
    with pytest.raises(ValueError, match="unknown config key"):
        _validate_known_config_key("x.y", step_mod=_M)


def test_prompt_workspace_helper_env_shell_and_workspace(tmp_path, monkeypatch):
    import toas.step as step_mod

    with pytest.raises(ValueError, match="invalid env key"):
        _validate_env_key("1BAD", step_mod=step_mod)

    monkeypatch.setattr(step_mod, "normalize_shell_grants", lambda grants: tuple(grants))
    cfg = OperatorConfig()
    out = _handle_shell_config(["config", "list"], step_mod=step_mod, context=_ctx(config=cfg))
    assert "config shell grants" in out[0]["content"]
    with pytest.raises(ValueError, match="usage:"):
        _handle_shell_config(["config", "reset", "extra"], step_mod=step_mod, context=_ctx(config=cfg))

    context = _ctx(command_cwd=str(tmp_path))
    assert _resolve_workspace_arg("x", context=context) == (tmp_path / "x").resolve()


def test_extract_replay_helper_branches(monkeypatch):
    import toas.step as step_mod

    with pytest.raises(ValueError, match="no prior assistant message"):
        _latest_assistant_target([{"role": "user", "content": "u"}])

    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _c, yaml_position="any": (None, True))
    monkeypatch.setattr(step_mod, "_extract_loose_command", lambda _c: (None, False))
    candidates = _collect_replay_candidates(step_mod=step_mod, context=_ctx(working=[{"role": "assistant", "content": "x"}, {"role": "user", "content": "/replay"}]))
    assert candidates == []

    rendered = _render_replay_candidates(
        [{"index": 1, "preview": "message #1 user: tool plan", "plan": []}],
        dry_run=False,
        context=_ctx(already_executed_indices={1}),
    )
    assert "already executed" in rendered[0]["content"]


def test_replay_queue_helpers_cover_state_transitions():
    plan = [{"tool_name": "echo"}, {"tool_name": "shell"}]
    queue = {"id": "q9", "plan": plan, "next_index": 1, "entries": []}
    resolved_plan, next_index = _validate_queue_plan_state(queue)
    assert resolved_plan is plan
    assert next_index == 1

    with pytest.raises(ValueError, match="missing plan payload"):
        _validate_queue_plan_state({"id": "q9", "next_index": 0})
    with pytest.raises(ValueError, match="invalid next_index"):
        _validate_queue_plan_state({"id": "q9", "plan": [], "next_index": -1})

    cancelled = _cancel_queue_remaining(dict(queue), plan=plan, entries=[], next_index=1)
    assert cancelled["status"] == "cancelled"
    assert cancelled["next_index"] == 2
    assert cancelled["entries"][-1]["status"] == "cancelled"

    with pytest.raises(ValueError, match="no pending operation to skip"):
        _apply_queue_skip({"id": "q7"}, plan=[{"tool_name": "echo"}], entries=[], next_index=1)


def test_replay_queue_helpers_cover_boundary_render_and_outcomes():
    queue = {"id": "q1"}
    plan = [{"tool_name": "shell"}]
    msg = _render_queue_boundary_message(queue=queue, plan=plan, call=plan[0], next_index=0)
    assert "queue id: q1" in msg
    assert "/queue [resume|approve*|skip|cancel]" in msg

    blocked_nodes = [
        {
            "payload": {"tool_name": "shell", "ok": False, "error": "tool shell disallows command: nope"},
        }
    ]
    assert _queue_step_outcome(blocked_nodes) == "blocked"

    failed_nodes = [{"payload": {"tool_name": "echo", "ok": False, "error": "boom"}}]
    assert _queue_step_outcome(failed_nodes) == "failed"

    ran_nodes = [{"payload": {"tool_name": "echo", "ok": True}}]
    assert _queue_step_outcome(ran_nodes) == "ran"


def test_replay_queue_edges_helpers_cover_branches():
    assert is_shell_authorization_block(
        {"payload": {"tool_name": "shell", "ok": False, "error": "tool shell disallows command: x"}}
    )
    assert is_shell_authorization_block(
        {"payload": {"tool_name": "shell_script", "ok": False, "error": "tool shell_script disallows cwd: x"}}
    )
    assert is_shell_authorization_block({"content": "tool shell disallows command: x"})
    assert is_shell_authorization_block({"content": "tool shell_script disallows cwd: x"})
    assert not is_shell_authorization_block({"payload": {"tool_name": "echo", "ok": False, "error": "boom"}})

    context = _ctx(
        events=[
            {"kind": "execution_queue", "payload": {"id": "q1", "status": "blocked", "entries": "bad"}},
            {"kind": "execution_queue", "payload": {"id": "qx", "status": "running"}},
            {"kind": "execution_queue", "payload": {"id": "q2", "status": "running", "next_index": 3}},
        ]
    )
    assert next_queue_id(context=context) == "q3"
    assert latest_queue_state("q2", context=context)["next_index"] == 3
    assert latest_queue_state("missing", context=context) is None
    by_id = latest_queue_states_by_id(context=context)
    assert set(by_id) == {"q1", "qx", "q2"}
    assert "unknown=1" in queue_summary({"id": "q1", "status": "blocked", "next_index": 0, "entries": [{"status": "unknown"}, "bad"]})
    assert entry_for_call(1, {"tool_name": "echo"}, status="ran", note="ok")["note"] == "ok"
    assert "note" not in entry_for_call(1, {"tool_name": "echo"}, status="ran")


def test_replay_queue_edges_additional_guard_branches():
    context = _ctx(
        events=[
            {"kind": "other", "payload": {"id": "q99"}},
            {"kind": "execution_queue", "payload": None},
            {"kind": "execution_queue", "payload": {"id": 1, "status": "x"}},
            {"kind": "execution_queue", "payload": {"id": "", "status": "x"}},
        ]
    )
    assert next_queue_id(context=context) == "q1"
    assert latest_queue_states_by_id(context=context) == {}
    assert "status=None next_index=0" in queue_summary({"id": "q0", "entries": "bad"})


def test_replay_queue_resume_action_unknown_id(monkeypatch):
    import toas.step as step_mod

    with pytest.raises(ValueError, match="unknown replay queue id"):
        handle_extract_replay_commands(
            "replay",
            ["--resume", "q9"],
            step_mod=step_mod,
            context=_ctx(events=[]),
        )


def test_replay_queue_block_and_approve_flow(monkeypatch):
    import toas.step as step_mod

    plan = [
        {"tool_name": "echo", "args": {"text": "ok"}},
        {"tool_name": "shell", "args": {"argv": ["blocked"]}},
        {"tool_name": "echo", "args": {"text": "tail"}},
    ]
    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _c, yaml_position="any": (plan, False))
    monkeypatch.setattr(step_mod, "_extract_loose_command", lambda _c: (None, False))
    monkeypatch.setattr(step_mod, "_as_nodes", lambda nodes: nodes)
    monkeypatch.setattr(step_mod, "resolve_effective_env_modifiers", lambda _w: {})
    monkeypatch.setattr(step_mod, "resolve_effective_shell_allowed", lambda _w, _c, _e=None: ("echo",))

    def _execute_plan(single_plan, **_kwargs):
        call = single_plan[0]
        if call["tool_name"] == "shell":
            return [
                {
                    "role": "result",
                    "content": "[ERROR] shell: tool shell disallows command: blocked",
                    "payload": {
                        "tool_name": "shell",
                        "ok": False,
                        "error": "tool shell disallows command: blocked",
                        "summary": "tool shell disallows command: blocked",
                    },
                }
            ]
        return [{"role": "result", "content": "ok", "payload": {"tool_name": call["tool_name"], "ok": True}}]

    def _execute_plan_user_context(single_plan, **_kwargs):
        call = single_plan[0]
        return [{"role": "result", "content": "approved", "payload": {"tool_name": call["tool_name"], "ok": True}}]

    monkeypatch.setattr(step_mod, "_execute_plan", _execute_plan)
    monkeypatch.setattr(step_mod, "_execute_plan_user_context", _execute_plan_user_context)

    working = [{"role": "assistant", "content": "```yaml\n- tool_name: echo\n```"}, {"role": "user", "content": "/replay --index 1"}]
    out = handle_extract_replay_commands(
        "replay",
        ["--index", "1"],
        step_mod=step_mod,
        context=_ctx(working=working, execute=lambda _w, _p: []),
    )
    blocked_updates = [node["queue_update"] for node in out if isinstance(node, dict) and isinstance(node.get("queue_update"), dict)]
    assert blocked_updates
    blocked = blocked_updates[-1]
    assert blocked["id"] == "q1"
    assert blocked["status"] == "blocked"
    assert blocked["next_index"] == 1
    blocked_messages = [node["content"] for node in out if isinstance(node, dict) and isinstance(node.get("content"), str)]
    assert any("queue controls:\n  /queue [resume|approve*|skip|cancel]" in message for message in blocked_messages)

    out2 = handle_extract_replay_commands(
        "replay",
        ["--approve", "q1"],
        step_mod=step_mod,
        context=_ctx(
            working=[{"role": "user", "content": "/replay --approve q1"}],
            events=[{"kind": "execution_queue", "payload": blocked}],
        ),
    )
    approved_updates = [node["queue_update"] for node in out2 if isinstance(node, dict) and isinstance(node.get("queue_update"), dict)]
    assert approved_updates
    assert approved_updates[-1]["status"] == "completed"


def test_replay_queue_skip_and_resume_flow(monkeypatch):
    import toas.step as step_mod

    plan = [
        {"tool_name": "echo", "args": {"text": "head"}},
        {"tool_name": "shell", "args": {"argv": ["blocked"]}},
        {"tool_name": "echo", "args": {"text": "tail"}},
    ]
    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _c, yaml_position="any": (plan, False))
    monkeypatch.setattr(step_mod, "_extract_loose_command", lambda _c: (None, False))
    monkeypatch.setattr(step_mod, "_as_nodes", lambda nodes: nodes)
    monkeypatch.setattr(step_mod, "resolve_effective_env_modifiers", lambda _w: {})
    monkeypatch.setattr(step_mod, "resolve_effective_shell_allowed", lambda _w, _c, _e=None: ("echo",))

    def _execute_plan(single_plan, **_kwargs):
        call = single_plan[0]
        if call["tool_name"] == "shell":
            return [
                {
                    "role": "result",
                    "content": "[ERROR] shell: tool shell disallows command: blocked",
                    "payload": {
                        "tool_name": "shell",
                        "ok": False,
                        "error": "tool shell disallows command: blocked",
                        "summary": "tool shell disallows command: blocked",
                    },
                }
            ]
        return [{"role": "result", "content": "ok", "payload": {"tool_name": call["tool_name"], "ok": True}}]

    monkeypatch.setattr(step_mod, "_execute_plan", _execute_plan)
    monkeypatch.setattr(step_mod, "_execute_plan_user_context", lambda single_plan, **_kwargs: single_plan)

    out = handle_extract_replay_commands(
        "replay",
        ["--index", "1"],
        step_mod=step_mod,
        context=_ctx(
            working=[{"role": "assistant", "content": "```yaml\n- tool_name: echo\n```"}, {"role": "user", "content": "/replay --index 1"}],
            execute=lambda _w, _p: [],
        ),
    )
    blocked = [node["queue_update"] for node in out if isinstance(node, dict) and isinstance(node.get("queue_update"), dict)][-1]
    assert blocked["status"] == "blocked"
    assert blocked["next_index"] == 1

    out2 = handle_extract_replay_commands(
        "replay",
        ["--skip", "q1"],
        step_mod=step_mod,
        context=_ctx(
            working=[{"role": "user", "content": "/replay --skip q1"}],
            events=[{"kind": "execution_queue", "payload": blocked}],
        ),
    )
    updates = [node["queue_update"] for node in out2 if isinstance(node, dict) and isinstance(node.get("queue_update"), dict)]
    assert updates
    assert updates[-1]["status"] == "completed"
    assert any(entry["status"] == "skipped" and entry["index"] == 1 for entry in updates[-1]["entries"])
    assert any(entry["status"] == "ran" and entry["index"] == 2 for entry in updates[-1]["entries"])


def test_replay_queue_cancel_marks_remaining_and_is_terminal(monkeypatch):
    import toas.step as step_mod

    queue = {
        "id": "q3",
        "status": "blocked",
        "next_index": 1,
        "target_message_index": 2,
        "plan": [
            {"tool_name": "echo", "args": {"text": "head"}},
            {"tool_name": "shell", "args": {"argv": ["blocked"]}},
            {"tool_name": "echo", "args": {"text": "tail"}},
        ],
        "entries": [{"index": 0, "tool_name": "echo", "status": "ran"}],
    }
    monkeypatch.setattr(step_mod, "_as_nodes", lambda nodes: nodes)

    out = handle_extract_replay_commands(
        "replay",
        ["--cancel", "q3"],
        step_mod=step_mod,
        context=_ctx(
            working=[{"role": "user", "content": "/replay --cancel q3"}],
            events=[{"kind": "execution_queue", "payload": queue}],
        ),
    )
    updates = [node["queue_update"] for node in out if isinstance(node, dict) and isinstance(node.get("queue_update"), dict)]
    assert updates
    cancelled = updates[-1]
    assert cancelled["status"] == "cancelled"
    assert cancelled["next_index"] == 3
    assert sum(1 for entry in cancelled["entries"] if entry["status"] == "cancelled") == 2

    out2 = handle_extract_replay_commands(
        "replay",
        ["--resume", "q3"],
        step_mod=step_mod,
        context=_ctx(
            working=[{"role": "user", "content": "/replay --resume q3"}],
            events=[{"kind": "execution_queue", "payload": cancelled}],
        ),
    )
    assert "already terminal" in out2[0]["content"]


def test_queue_command_alias_routes_to_replay_queue_action(monkeypatch):
    import toas.step as step_mod

    queue = {
        "id": "q1",
        "status": "blocked",
        "next_index": 0,
        "target_message_index": 1,
        "plan": [{"tool_name": "echo", "args": {"text": "x"}}],
        "entries": [],
    }
    monkeypatch.setattr(step_mod, "_as_nodes", lambda nodes: nodes)
    monkeypatch.setattr(step_mod, "resolve_effective_env_modifiers", lambda _w: {})
    monkeypatch.setattr(step_mod, "resolve_effective_shell_allowed", lambda _w, _c, _e=None: ("echo",))
    monkeypatch.setattr(
        step_mod,
        "_execute_plan_user_context",
        lambda single_plan, **_kwargs: [{"role": "result", "content": "approved", "payload": {"tool_name": single_plan[0]["tool_name"], "ok": True}}],
    )
    monkeypatch.setattr(
        step_mod,
        "_execute_plan",
        lambda single_plan, **_kwargs: [{"role": "result", "content": "ran", "payload": {"tool_name": single_plan[0]["tool_name"], "ok": True}}],
    )

    out = handle_extract_replay_commands(
        "queue",
        [],
        step_mod=step_mod,
        context=_ctx(
            working=[{"role": "user", "content": "/queue"}],
            events=[{"kind": "execution_queue", "payload": queue}],
        ),
    )
    updates = [node["queue_update"] for node in out if isinstance(node, dict) and isinstance(node.get("queue_update"), dict)]
    assert updates
    assert updates[-1]["status"] == "completed"


def test_config_values_and_yaml_position_compat(monkeypatch, tmp_path):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "flatten_config", lambda c: {"extraction.yaml_position": "top"})
    monkeypatch.setattr(step_mod, "valid_config_keys", lambda: ["extraction.yaml_position"])

    ctx = _ctx()

    # /config values extraction.yaml_position (covers --sources and yaml_position compat)
    out = handle_config_help_commands("config", ["values", "extraction.yaml_position"], step_mod=step_mod, context=ctx)
    assert out is not None
    assert "yaml_position" in out[0]["content"]

    # /config values wrong arg count
    with pytest.raises(ValueError, match="usage: /config values"):
        handle_config_help_commands("config", ["values"], step_mod=step_mod, context=ctx)

    # /config values unknown key
    monkeypatch.setattr(step_mod, "valid_config_keys", lambda: [])
    with pytest.raises(ValueError, match="unknown config key"):
        handle_config_help_commands("config", ["values", "bad.key"], step_mod=step_mod, context=ctx)


def test_config_secret_show(monkeypatch):
    import toas.step as step_mod

    out = handle_config_help_commands("config", ["secret", "show"], step_mod=step_mod, context=_ctx())
    assert out is not None
    assert "secret keys" in out[0]["content"]

    # /config secret wrong usage
    with pytest.raises(ValueError, match="usage: /config secret"):
        handle_config_help_commands("config", ["secret", "bad"], step_mod=step_mod, context=_ctx())


def test_config_unset_and_restore_errors(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "valid_config_keys", lambda: ["llm.model"])

    # /config unset wrong arg count
    with pytest.raises(ValueError, match="usage: /config unset"):
        handle_config_help_commands("config", ["unset"], step_mod=step_mod, context=_ctx())

    # /config unset unknown key
    with pytest.raises(ValueError, match="unknown config key"):
        handle_config_help_commands("config", ["unset", "bad.key"], step_mod=step_mod, context=_ctx())

    # /config restore wrong arg count
    with pytest.raises(ValueError, match="usage: /config restore"):
        handle_config_help_commands("config", ["restore", "extra"], step_mod=step_mod, context=_ctx())


def test_config_load_and_save_errors(monkeypatch, tmp_path):
    import toas.step as step_mod

    ctx = _ctx(command_cwd=str(tmp_path))

    # /config load too many args
    with pytest.raises(ValueError, match="usage: /config load"):
        handle_config_help_commands("config", ["load", "a", "b"], step_mod=step_mod, context=ctx)

    # /config load file not found
    with pytest.raises(ValueError, match="config file not found"):
        handle_config_help_commands("config", ["load", "missing.toml"], step_mod=step_mod, context=ctx)

    # /config load failed to parse
    bad = tmp_path / "bad.toml"
    bad.write_text("not valid toml [[[", encoding="utf-8")
    monkeypatch.setattr(step_mod, "load_file_config", lambda p: None)
    with pytest.raises(ValueError, match="failed to load config"):
        handle_config_help_commands("config", ["load", str(bad)], step_mod=step_mod, context=ctx)

    # /config save too many args
    with pytest.raises(ValueError, match="usage: /config save"):
        handle_config_help_commands("config", ["save", "a", "b"], step_mod=step_mod, context=ctx)


def test_config_show_sources(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "flatten_config", lambda c: {"llm.model": "x"})

    # /config --sources
    out = handle_config_help_commands("config", ["--sources"], step_mod=step_mod, context=_ctx())
    assert out is not None
    assert "source" in out[0]["content"].lower()

    # /config show --sources
    out = handle_config_help_commands("config", ["show", "--sources"], step_mod=step_mod, context=_ctx())
    assert out is not None
    assert "source" in out[0]["content"].lower()

    # /config show extra args
    with pytest.raises(ValueError, match="usage: /config show"):
        handle_config_help_commands("config", ["show", "extra"], step_mod=step_mod, context=_ctx())

    # /config extra args
    with pytest.raises(ValueError, match="usage: /config"):
        handle_config_help_commands("config", ["extra"], step_mod=step_mod, context=_ctx())


def test_config_values_yaml_position_with_choices(monkeypatch):
    """Test /config values extraction.yaml_position with categorical choices,
    covering the compat note in the 'choices' branch (not the 'no choices' branch)."""
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "flatten_config", lambda c: {"extraction.yaml_position": "top"})
    monkeypatch.setattr(step_mod, "valid_config_keys", lambda: ["extraction.yaml_position"])
    monkeypatch.setattr(step_mod, "config_value_choices", lambda k: ("top", "bottom", "auto") if k == "extraction.yaml_position" else None)

    ctx = _ctx()
    out = handle_config_help_commands("config", ["values", "extraction.yaml_position"], step_mod=step_mod, context=ctx)
    assert out is not None
    assert "allowed values" in out[0]["content"]
    assert "yaml_position" in out[0]["content"].lower()
    # The compat note should appear in the choices branch
    assert "compatibility-only" in out[0]["content"] or "intent_arbitration" in out[0]["content"]


def test_extract_replay_additional_coverage(monkeypatch):
    import toas.step as step_mod
    from toas.runtime.operator_command_extract_replay import (
        _parse_extract_index_token,
        _parse_replay_index_token,
        _render_extract_candidates,
        _normalized_queue_entries,
        _run_queue_until_boundary,
        _handle_replay_queue_action,
    )

    # 1. _parse_extract_index_token raw is empty
    with pytest.raises(ValueError, match="usage: /extract"):
        _parse_extract_index_token("d")

    # 2. _parse_replay_index_token raw is not int
    with pytest.raises(ValueError, match="usage: /replay"):
        _parse_replay_index_token("abc")

    # 3. _render_extract_candidates with skipped
    step_mod_dummy = object()
    out = _render_extract_candidates(
        candidates=[{"kind": "tool_plan", "preview": "p1"}],
        skipped=["skip1"],
        verbose=False,
        step_mod=step_mod_dummy,
        context=_ctx(),
    )
    assert "skipped callable-looking blocks" in out[0]["content"]

    # 4. _parse_replay_args errors
    with pytest.raises(ValueError, match="usage: /replay"):
        _parse_replay_args(["--resume"])
    with pytest.raises(ValueError, match="usage: /replay"):
        _parse_replay_args(["--resume", "q1", "--approve", "q2"])
    with pytest.raises(ValueError, match="usage: /replay"):
        _parse_replay_args(["--resume", "  "])
    with pytest.raises(ValueError, match="usage: /replay"):
        _parse_replay_args(["--unknown"])
    with pytest.raises(ValueError, match="usage: /replay"):
        _parse_replay_args(["--resume", "q1", "--dry-run"])

    # 5. _normalized_queue_entries non-list or list containing non-dict
    assert _normalized_queue_entries({"entries": None}) == []
    assert _normalized_queue_entries({"entries": [123, {"a": 1}]}) == [{"a": 1}]

    # 6. _run_queue_until_boundary failed outcome
    class DummyStepMod:
        @staticmethod
        def _as_nodes(nodes):
            return nodes
        @staticmethod
        def resolve_effective_env_modifiers(working):
            return {}
        @staticmethod
        def resolve_effective_shell_allowed(working, config):
            return []
        @staticmethod
        def _execute_plan(plan, **kwargs):
            return [{"role": "result", "payload": {"ok": False}}]

    queue = {
        "id": "q_fail",
        "status": "running",
        "next_index": 0,
        "plan": [{"tool_name": "echo", "args": {}}],
        "entries": [],
    }
    out_nodes, updated_queue = _run_queue_until_boundary(
        queue,
        step_mod=DummyStepMod,
        context=_ctx(),
        action="resume",
    )
    assert updated_queue["status"] == "failed"

    # 8. _render_replay_candidates with multiple candidates
    replay_candidates = [
        {"index": 1, "preview": "p1", "plan": []},
        {"index": 2, "preview": "p2", "plan": []},
    ]
    out_rendered = _render_replay_candidates(replay_candidates, dry_run=False, context=_ctx())
    assert "replay candidates:" in out_rendered[0]["content"]

    # 9. _handle_replay_queue_action invalid action
    context = _ctx(events=[{"kind": "execution_queue", "payload": {"id": "q1", "status": "blocked"}}])
    with pytest.raises(ValueError, match="usage: /replay"):
        _handle_replay_queue_action(("bad_action", "q1"), step_mod=step_mod, context=context)

    # 10. _parse_queue_args errors
    with pytest.raises(ValueError, match="usage: /queue"):
        _parse_queue_args(["q1", "resume", "extra"], context=context)
    with pytest.raises(ValueError, match="usage: /queue"):
        _parse_queue_args(["resume", "skip"], context=context)

    # 11. _handle_replay no candidates found
    with pytest.raises(ValueError, match="no replayable callable messages found in history"):
        handle_extract_replay_commands("replay", [], step_mod=step_mod, context=_ctx(working=[]))

    # 12. /extract no candidates and empty skipped
    monkeypatch.setattr(step_mod, "_extract_frontier_assistant_candidates", lambda _c, **_kwargs: ([], []))
    with pytest.raises(ValueError, match="latest assistant message has no extractable callable intent"):
        handle_extract_replay_commands(
            "extract",
            [],
            step_mod=step_mod,
            context=_ctx(working=[{"role": "assistant", "content": "a"}, {"role": "user", "content": "/extract"}]),
        )

    # 13. /extract with no selection index
    monkeypatch.setattr(step_mod, "_extract_frontier_assistant_candidates", lambda _c, **_kwargs: ([{"kind": "tool_plan", "preview": "p", "adopt": "a"}], []))
    out_extract_no_idx = handle_extract_replay_commands(
        "extract",
        [],
        step_mod=step_mod,
        context=_ctx(working=[{"role": "assistant", "content": "a"}, {"role": "user", "content": "/extract"}]),
    )
    assert "extract candidates" in out_extract_no_idx[0]["content"]

    # 14. /extract --verbose index
    monkeypatch.setattr(step_mod, "_extract_frontier_assistant_candidates", lambda _c, **_kwargs: ([{"kind": "tool_plan", "preview": "p", "adopt": "a", "adopt_verbose": "av"}], []))
    out_extract_verbose = handle_extract_replay_commands(
        "extract",
        ["--verbose", "1"],
        step_mod=step_mod,
        context=_ctx(working=[{"role": "assistant", "content": "a"}, {"role": "user", "content": "/extract"}]),
    )
    assert out_extract_verbose[0]["content"] == "av"

    # 15. /replay with no index specified
    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _c, yaml_position="any": ([{"tool_name": "echo", "args": {}}], False))
    out_replay_no_idx = handle_extract_replay_commands(
        "replay",
        [],
        step_mod=step_mod,
        context=_ctx(working=[{"role": "assistant", "content": "plan"}, {"role": "user", "content": "/replay"}]),
    )
    assert "replay candidate" in out_replay_no_idx[0]["content"]

    # 16. /replay already executed index and no force
    with pytest.raises(ValueError, match="target already has tool_request records; rerun with --force"):
        handle_extract_replay_commands(
            "replay",
            ["--index", "1"],
            step_mod=step_mod,
            context=_ctx(
                working=[{"role": "assistant", "content": "plan"}, {"role": "user", "content": "/replay"}],
                already_executed_indices={1},
            ),
        )

    # 17. shlex ValueError
    monkeypatch.setattr(step_mod, "extract_plan_with_status", lambda _c, yaml_position="any": (None, False))
    orig_split = step_mod.shlex.split
    def fail_split(s):
        if s == "fail-me":
            raise ValueError("fail")
        return orig_split(s)
    monkeypatch.setattr(step_mod.shlex, "split", fail_split)
    working_shlex = [{"role": "assistant", "content": "```yaml\ncmd: fail-me\n```"}, {"role": "user", "content": "/replay"}]
    candidates_shlex = _collect_replay_candidates(step_mod=step_mod, context=_ctx(working=working_shlex))
    assert candidates_shlex == []
