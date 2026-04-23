from __future__ import annotations

import shlex
from pathlib import Path

import pytest

from toas.config import BackendCatalogEntry, LLMPolicy, OperatorConfig
from toas.runtime.operator_command_config_help import (
    _config_secret_result,
    _resolve_config_path,
    handle_config_help_commands,
)
from toas.runtime.operator_command_context import OperatorCommandContext
from toas.runtime.operator_command_extract_replay import handle_extract_replay_commands
from toas.runtime.operator_command_prompt_workspace import (
    _parse_compact_args,
    _resolve_cd_target,
    handle_prompt_workspace_commands,
)


def _ctx(**overrides):
    base = OperatorCommandContext(
        execute=lambda _working, _plan: [],
        working=[],
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


def test_prompt_workspace_handler_prompts(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_render_prompt_browse_commands", lambda prefix: f"rendered:{prefix}")
    out = handle_prompt_workspace_commands("prompts", ["x"], step_mod=step_mod, context=_ctx())
    assert out == [{"role": "result", "content": "rendered:x"}]


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


def test_config_help_handler_help(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "render_session_help", lambda: "help text")
    out = handle_config_help_commands("help", [], step_mod=step_mod, context=_ctx())
    assert out == [{"role": "result", "content": "help text"}]


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
    assert out == [{"role": "result", "content": "env set: ABC"}]
    out = handle_prompt_workspace_commands("env", ["unset", "ABC"], step_mod=step_mod, context=_ctx())
    assert out == [{"role": "result", "content": "env unset: ABC"}]
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


def test_prompt_workspace_shell_list_and_reset(monkeypatch):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_resolve_shell_grants_with_sources", lambda _w, _c: (("echo",), ("echo",), {"config": "default"}, (), ()))
    monkeypatch.setattr(step_mod, "render_shell_policy_view", lambda *args: "policy-view")
    monkeypatch.setattr(step_mod, "resolve_effective_shell_allowed", lambda _w, _c: ("echo",))
    monkeypatch.setattr(step_mod, "parse_shell_grant", lambda s: type("P", (), {"raw": s})())
    out = handle_prompt_workspace_commands("shell", ["list"], step_mod=step_mod, context=_ctx())
    assert out == [{"role": "result", "content": "policy-view"}]
    out = handle_prompt_workspace_commands("shell", ["reset"], step_mod=step_mod, context=_ctx())
    assert "reset to config baseline" in out[0]["content"]


def test_prompt_workspace_workspace_modes_and_compact(monkeypatch, tmp_path):
    import toas.step as step_mod

    monkeypatch.setattr(step_mod, "_render_workspace_commands", lambda mode, roots: f"{mode}:{len(roots)}")
    monkeypatch.setattr(step_mod, "_compact_result_blocks", lambda transcript, threshold: ("x", [{"index": 1, "chars": 900}]))
    cwd = tmp_path
    add_dir = tmp_path / "add"
    add_dir.mkdir()
    out = handle_prompt_workspace_commands("workspace", [], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    assert out == [{"role": "result", "content": "strict:1"}]
    out = handle_prompt_workspace_commands("workspace", ["add", str(add_dir)], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    assert "workspace_update" in out[0]
    out = handle_prompt_workspace_commands("workspace", ["mode", "unbounded"], step_mod=step_mod, context=_ctx(command_cwd=str(cwd)))
    assert out[0]["workspace_update"]["mode"] == "unbounded"
    out = handle_prompt_workspace_commands("compact", ["--dry-run", "--threshold", "10"], step_mod=step_mod, context=_ctx(transcript="t"))
    assert "compact dry-run" in out[0]["content"]


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

    monkeypatch.setattr(step_mod, "_extract_frontier_assistant_candidates", lambda _c: ([], ["1. bad"]))
    with pytest.raises(ValueError, match="skipped callable-looking blocks"):
        handle_extract_replay_commands(
            "extract",
            [],
            step_mod=step_mod,
            context=_ctx(working=[{"role": "assistant", "content": "a"}, {"role": "user", "content": "/extract"}]),
        )

    monkeypatch.setattr(step_mod, "_extract_frontier_assistant_candidates", lambda _c: ([{"kind": "tool_plan", "preview": "p", "adopt": "a"}], []))
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
    monkeypatch.setattr(step_mod, "flatten_config", lambda _c: {"llm.model": "m", "generation.thinking_mode": "disabled"})
    monkeypatch.setattr(step_mod, "load_file_config", lambda _p: {"llm": {"model": "m"}})
    monkeypatch.setattr(step_mod.Settings, "from_env", classmethod(lambda cls: type("S", (), {"llm_base_url": "u", "llm_model": "m"})()))
    cfg = OperatorConfig()

    out = handle_config_help_commands("config", ["set", "llm.model", "q"], step_mod=step_mod, context=_ctx(config=cfg))
    assert out[0]["config_update"] == {"llm": {"model": "m"}}
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
